#!/usr/bin/env python3
"""
发票业务服务层

该模块将原本耦合在 UI 层的发票业务逻辑（批量重命名、导出 Excel、批量字段提取）
抽象为独立的 Python 服务，不依赖 Qt，可供 GUI 和 MCP Server 共用。
"""

import logging
import os
import re
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable

from openpyxl import Workbook
from openpyxl.styles import PatternFill

from core.pdf_handler import is_image_file, is_ofd_file
from core.invoice_field_registry import (
    ALL_FIELD_KEYS,
    INVOICE_TYPE_KEYS,
    get_fields,
    get_type_label,
)


# 模块级日志器
logger = logging.getLogger(__name__)


def migrate_rename_rules(config: Dict[str, Any]) -> bool:
    """
    把旧版单一重命名规则迁移为按票种的规则集合

    功能描述:
        当配置中不存在有效的 rename_rules 字典、且存在非空的旧版
        rename_rule 字符串时，把该字符串复制到全部 7 类票种，
        使升级前后的重命名行为保持一致。

        若 rename_rules 已存在（是字典），一律不覆盖。

    参数:
        config: 配置字典（原地修改）

    返回值:
        bool: 是否发生了迁移（True 表示已写入 rename_rules）
    """
    if not isinstance(config, dict):
        return False

    existing = config.get('rename_rules')
    if isinstance(existing, dict):
        # 已有按票种规则集合，不覆盖
        return False

    legacy = config.get('rename_rule')
    if not isinstance(legacy, str) or not legacy.strip():
        # 无旧版规则，不生成空规则
        return False

    config['rename_rules'] = {key: legacy for key in INVOICE_TYPE_KEYS}
    return True


def normalize_rename_rules(raw: Any) -> Dict[str, str]:
    """
    把任意来源的规则集合规整为「7 个票种键齐全」的字典

    功能描述:
        仅保留 7 个合法票种键，值为字符串；缺失的票种补空串，
        使「未配置」与「配置了空串」语义唯一。

    参数:
        raw: 原始规则集合，可为 None / dict / 其他类型

    返回值:
        Dict[str, str]: 7 个票种键齐全的规则字典
    """
    result = {key: '' for key in INVOICE_TYPE_KEYS}
    if isinstance(raw, dict):
        for key in INVOICE_TYPE_KEYS:
            value = raw.get(key)
            if isinstance(value, str):
                result[key] = value.strip()
    return result


class InvoiceService:
    """
    发票业务服务类

    提供与界面无关的发票处理功能，包括批量字段提取、批量重命名、导出 Excel 等。

    Attributes:
        pdf_handler: PDFHandler 实例，用于执行 PDF 合并和字段提取
        INVALID_CHARS: 文件名非法字符正则
    """

    INVALID_CHARS = r'[<>:"/\\|?*]'

    def __init__(self, pdf_handler):
        """
        初始化发票业务服务

        参数:
            pdf_handler: PDFHandler 实例，提供 merge_pdfs 和 extract 系列方法
        """
        self.pdf_handler = pdf_handler

    def batch_extract(self, pdf_paths: List[str],
                      on_progress: Optional[Callable[[int, int], None]] = None) -> List[Dict[str, Any]]:
        """
        批量提取发票字段信息

        功能描述:
            依次调用 PDFHandler.extract_all_invoice_info 提取每张发票的字段。

        参数:
            pdf_paths: PDF 文件路径列表
            on_progress: 进度回调函数，签名为 on_progress(current, total)

        返回值:
            List[Dict[str, Any]]: 每个元素包含 'path' 和 'info' 的字典列表
        """
        results = []
        total = len(pdf_paths)

        for idx, pdf_path in enumerate(pdf_paths, start=1):
            try:
                info = self.pdf_handler.extract_all_invoice_info(pdf_path)
                results.append({
                    'path': pdf_path,
                    'info': info,
                })
            except Exception as e:
                logger.exception("批量提取失败: %s", pdf_path)
                results.append({
                    'path': pdf_path,
                    'info': None,
                })

            if on_progress:
                on_progress(idx, total)

        return results

    def batch_rename(self, pdf_paths: List[str], rules: Dict[str, str],
                     on_progress: Optional[Callable[[int, int], None]] = None,
                     dry_run: bool = False) -> Dict[str, Any]:
        """
        根据按票种的规则批量重命名发票 PDF 文件

        功能描述:
            逐个文件识别其票种，套用该票种自己的规则生成新文件名，
            处理文件名冲突后执行或预览重命名。
            图片与 OFD 类型文件不参与重命名，分别计入 skipped_image_count、skipped_ofd_count。
            票种规则为空（未配置）的文件保持原文件名，计入 skipped_unconfigured_count。

        参数:
            pdf_paths: 需要重命名的 PDF 文件路径列表
            rules: 票种标识 -> 重命名规则字符串。（空串表示该票种未配置）
            on_progress: 进度回调函数，签名为 on_progress(current, total)
            dry_run: 是否为预览模式；为 True 时不实际重命名文件，仅返回预计映射

        返回值:
            Dict[str, Any]: 重命名结果，包含以下字段
                - renamed_count: 成功重命名（或预览中将会重命名）的文件数
                - failed_count: 失败的文件数
                - unrecognized_files: 无法识别（info 为 None）的文件名列表
                - skipped_image_count: 被跳过的图片文件数量
                - skipped_ofd_count: 被跳过的 OFD 文件数量
                - skipped_unconfigured_count: 因票种未配置规则而跳过的文件数量
                - renamed_map: 旧路径 -> 新路径 的映射字典
        """
        renamed_count = 0
        failed_count = 0
        unrecognized_files = []
        skipped_image_count = 0
        skipped_ofd_count = 0
        skipped_unconfigured_count = 0
        renamed_map = {}
        total = len(pdf_paths)

        # 规整规则集合：只保留合法票种键，值为字符串
        normalized_rules = normalize_rename_rules(rules)

        # 预览模式下用于模拟文件名冲突的已占用名称集合
        used_names = set(os.path.basename(p) for p in pdf_paths) if dry_run else None

        for idx, file_path in enumerate(pdf_paths, start=1):
            try:
                # 图片文件不提取字段，直接跳过重命名
                if is_image_file(file_path):
                    skipped_image_count += 1
                    continue

                # OFD 文件不解析字段，直接跳过重命名
                if is_ofd_file(file_path):
                    skipped_ofd_count += 1
                    continue

                file_info = self.pdf_handler.extract_all_invoice_info(file_path)

                if file_info is None:
                    unrecognized_files.append(os.path.basename(file_path))
                    continue

                # 按识别出的票种选择对应规则
                type_key = file_info.get('invoice_type_key')
                rule = normalized_rules.get(type_key, '') if type_key else ''

                if not rule:
                    # 该票种未配置规则：保持原文件名
                    skipped_unconfigured_count += 1
                    continue

                new_name = self.apply_rule(rule, file_info, type_key=type_key)
                if not new_name:
                    failed_count += 1
                    continue

                _, ext = os.path.splitext(file_path)
                new_name_with_ext = new_name + ext

                # 处理文件名冲突
                dir_path = os.path.dirname(file_path)
                final_name = new_name_with_ext
                counter = 1

                if dry_run:
                    while final_name in used_names:
                        if final_name == os.path.basename(file_path):
                            break
                        base_name = f"{new_name}({counter})"
                        final_name = base_name + ext
                        counter += 1
                else:
                    while os.path.exists(os.path.join(dir_path, final_name)):
                        if final_name == os.path.basename(file_path):
                            break
                        base_name = f"{new_name}({counter})"
                        final_name = base_name + ext
                        counter += 1

                if final_name != os.path.basename(file_path):
                    new_path = os.path.join(dir_path, final_name)
                    if dry_run:
                        used_names.add(final_name)
                        used_names.discard(os.path.basename(file_path))
                    else:
                        os.rename(file_path, new_path)
                    renamed_count += 1
                    renamed_map[file_path] = new_path

            except Exception as e:
                logger.exception("重命名文件失败: %s", file_path)
                failed_count += 1

            if on_progress:
                on_progress(idx, total)

        return {
            'renamed_count': renamed_count,
            'failed_count': failed_count,
            'unrecognized_files': unrecognized_files,
            'skipped_image_count': skipped_image_count,
            'skipped_ofd_count': skipped_ofd_count,
            'skipped_unconfigured_count': skipped_unconfigured_count,
            'renamed_map': renamed_map,
        }

    def export_to_excel(self, pdf_infos: List[Dict[str, Any]], output_path: str,
                        duplicate_codes: Optional[set] = None) -> bool:
        """
        将发票信息列表导出为 Excel 文件

        功能描述:
            使用 openpyxl 创建 Excel 工作簿，写入发票列表、标记重复发票、添加总计行。

        参数:
            pdf_infos: 发票信息字典列表，每个字典需包含 name、amount、tax_amount、
                       invoice_date、invoice_code、path、mod_time、size 等字段
            output_path: 输出 Excel 文件路径
            duplicate_codes: 重复发票号码集合，用于高亮标记，可选

        返回值:
            bool: 导出是否成功
        """
        if duplicate_codes is None:
            duplicate_codes = set()

        try:
            wb = Workbook()
            ws = wb.active
            ws.title = "发票列表"

            headers = ["发票代码", "文件名", "金额", "税额", "发票日期", "文件路径", "修改时间", "大小"]
            for col, header in enumerate(headers, 1):
                cell = ws.cell(row=1, column=col, value=header)
                cell.font = cell.font.copy(bold=True)

            yellow_fill = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid")

            total_amount = 0.0
            total_tax = 0.0

            for row_idx, file_info in enumerate(pdf_infos, 2):
                invoice_code = file_info.get('invoice_code', '')
                amount = file_info.get('amount', 0.0)
                tax_amount = file_info.get('tax_amount', 0.0)

                if isinstance(amount, (int, float)):
                    total_amount += amount
                if isinstance(tax_amount, (int, float)):
                    total_tax += tax_amount

                is_duplicate = invoice_code in duplicate_codes and invoice_code != ""

                ws.cell(row=row_idx, column=1, value=invoice_code)
                ws.cell(row=row_idx, column=2, value=file_info.get('name', ''))
                ws.cell(row=row_idx, column=3, value=amount)
                ws.cell(row=row_idx, column=4, value=tax_amount)
                ws.cell(row=row_idx, column=5, value=file_info.get('invoice_date', ''))
                ws.cell(row=row_idx, column=6, value=file_info.get('path', ''))
                ws.cell(row=row_idx, column=7, value=file_info.get('mod_time', ''))
                ws.cell(row=row_idx, column=8, value=file_info.get('size', ''))

                if is_duplicate:
                    for col in range(1, 9):
                        ws.cell(row=row_idx, column=col).fill = yellow_fill

            # 总计行
            total_row = len(pdf_infos) + 2
            ws.cell(row=total_row, column=1, value="")
            ws.cell(row=total_row, column=2, value="总计")
            ws.cell(row=total_row, column=3, value=total_amount)
            ws.cell(row=total_row, column=4, value=total_tax)
            ws.cell(row=total_row, column=5, value="")
            ws.cell(row=total_row, column=6, value="")
            ws.cell(row=total_row, column=7, value="")
            ws.cell(row=total_row, column=8, value="")

            for col in range(1, 9):
                ws.cell(row=total_row, column=col).font = ws.cell(row=total_row, column=col).font.copy(bold=True)

            ws.column_dimensions['A'].width = 20
            ws.column_dimensions['B'].width = 30
            ws.column_dimensions['C'].width = 12
            ws.column_dimensions['D'].width = 12
            ws.column_dimensions['E'].width = 15
            ws.column_dimensions['F'].width = 50
            ws.column_dimensions['G'].width = 20
            ws.column_dimensions['H'].width = 12

            wb.save(output_path)
            return True

        except Exception as e:
            logger.exception("导出 Excel 失败: %s", output_path)
            return False

    @staticmethod
    def apply_rule(rule: str, file_info: Dict[str, Any],
                   type_key: Optional[str] = None) -> Optional[str]:
        """
        应用重命名规则生成新文件名

        功能描述:
            将规则字符串中的中文占位符替换为 file_info 中对应的字段值，并清理非法字符。

            字段集按票种取：传入 type_key 时使用该票种的字段集，
            未传或未知票种时退回全部字段（兼容旧调用）。

            未识别字段的处理：值为 None、缺失、或空白字符串时，
            保留 {占位符} 原文而不替换为空，便于用户从文件名看出未识别。
            数值字段（如金额）即使为 0 也按数值格式替换，因为 0 是有效值。

        参数:
            rule: 重命名规则字符串，如 "{买方名字}-{开票日期}-{商品类型}"
            file_info: 发票信息字典，包含 invoice_type、invoice_date 等字段
            type_key: 票种标识，用于确定可用字段集；None 表示使用全部字段

        返回值:
            Optional[str]: 清理后的文件名（不含扩展名），规则为空时返回 None
        """
        if not rule:
            return None

        result = rule
        fields = get_fields(type_key) if type_key else get_fields(None)

        # 按票种字段集替换；若规则里出现该票种字段集之外的占位符，
        # 再尝试用全部字段兜底（保持旧规则可用）
        field_pairs = list(fields)
        _known = {name for name, _ in field_pairs}
        for name, key in get_fields(None):
            if name not in _known:
                field_pairs.append((name, key))

        for field_name, field_key in field_pairs:
            placeholder = f"{{{field_name}}}"
            if placeholder not in result:
                continue

            value = file_info.get(field_key)

            # 数值字段：0 也是有效值，按两位小数替换
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                result = result.replace(placeholder, f"{value:.2f}")
                continue

            # 缺失/空白：保留占位符原文
            if value is None:
                continue
            text = str(value)
            if not text.strip():
                continue

            result = result.replace(placeholder, text)

        result = InvoiceService.sanitize_filename(result)
        return result

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        清理文件名中的非法字符

        功能描述:
            将 Windows 文件名非法字符替换为下划线，并移除首尾的空格和点。

        参数:
            filename: 原始文件名

        返回值:
            str: 清理后的文件名，若为空则返回 "未命名"
        """
        sanitized = re.sub(InvoiceService.INVALID_CHARS, '_', filename)
        sanitized = sanitized.strip('. ')
        if not sanitized:
            sanitized = "未命名"
        return sanitized

    @staticmethod
    def get_available_fields() -> Dict[str, Any]:
        """
        获取重命名规则中可用的字段列表（按票种分组）

        返回值:
            Dict[str, Any]:
                - types: 7 个票种分组，每项含 key / label / fields
                         （fields 为 [{display, key}, ...]）
                - fields: 全部字段的扁平并集，保留以兼容既有调用方
        """
        types = []
        for type_key in INVOICE_TYPE_KEYS:
            types.append({
                'key': type_key,
                'label': get_type_label(type_key),
                'fields': [
                    {'display': display, 'key': field_key}
                    for display, field_key in get_fields(type_key)
                ],
            })

        # 扁平并集：按 ALL_FIELD_KEYS 顺序，显示名取首次出现
        display_by_key: Dict[str, str] = {}
        for item in types:
            for field in item['fields']:
                display_by_key.setdefault(field['key'], field['display'])

        flat = [
            {'display': display_by_key[key], 'key': key}
            for key in ALL_FIELD_KEYS
        ]

        return {'types': types, 'fields': flat}
