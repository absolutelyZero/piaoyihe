#!/usr/bin/env python3
"""
MCP Server Tools 实现模块

提供每个 MCP Tool 的具体业务逻辑实现，所有函数均为纯 Python 函数，
不依赖 Qt，可直接被 server.py 注册为 MCP Tools。
"""

import logging
import os
from typing import List, Dict, Any, Optional

from core.pdf_handler import PDFHandler
from core.invoice_service import InvoiceService
from .config import SERVER_NAME, SERVER_VERSION


# 模块级日志器
logger = logging.getLogger(__name__)


def _new_pdf_handler() -> PDFHandler:
    """
    创建新的 PDFHandler 实例

    功能描述:
        为 MCP Server 创建独立的 PDFHandler，避免与 GUI 实例共享状态。

    返回值:
        PDFHandler: 新的 PDFHandler 实例
    """
    return PDFHandler()


def _validate_pdf_paths(pdf_paths: Any) -> tuple[bool, str]:
    """
    校验 PDF 路径列表

    功能描述:
        确保传入的是列表/元组，且每个元素为存在并以 .pdf/.PDF 结尾的字符串路径。

    参数:
        pdf_paths: 待校验的路径集合

    返回值:
        tuple[bool, str]: (是否通过, 错误信息)
    """
    if not isinstance(pdf_paths, (list, tuple)):
        return False, "pdf_paths 必须是列表或元组"

    if len(pdf_paths) == 0:
        return False, "待处理文件列表为空"

    for path in pdf_paths:
        if not isinstance(path, str):
            return False, f"路径必须是字符串: {path!r}"
        if not path.lower().endswith(".pdf"):
            return False, f"仅支持 PDF 文件: {path}"
        if not os.path.exists(path):
            return False, f"文件不存在: {path}"

    return True, ""


def _normalize_paths(pdf_paths: List[str]) -> List[str]:
    """
    将路径规范化为绝对路径

    功能描述:
        将相对路径基于当前工作目录解析为绝对路径，便于客户端和日志统一处理。

    参数:
        pdf_paths: PDF 文件路径列表

    返回值:
        List[str]: 规范化后的绝对路径列表
    """
    return [os.path.abspath(p) for p in pdf_paths]


def _ensure_output_dir(output_path: str) -> tuple[bool, str]:
    """
    确保输出目录存在且可写

    功能描述:
        如果输出路径的父目录不存在则尝试创建，并返回是否成功。

    参数:
        output_path: 输出文件路径

    返回值:
        tuple[bool, str]: (是否通过, 错误信息)
    """
    if not output_path or not isinstance(output_path, str):
        return False, "输出路径不能为空"

    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir, exist_ok=True)
        except Exception as e:
            logger.exception("创建输出目录失败: %s", output_dir)
            return False, f"无法创建输出目录: {e}"

    return True, ""


def handle_merge_invoices(pdf_paths: List[str], output_path: str,
                          layout: Dict[str, Any], mode: str = "普通",
                          margins: Optional[Dict[str, int]] = None,
                          crop_marks: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    合并多个 PDF 发票为指定布局

    功能描述:
        调用 PDFHandler.merge_pdfs 将多个 PDF 文件按指定布局合并输出。
        支持自定义页边距和裁切线设置。

    参数:
        pdf_paths: 待合并的 PDF 文件路径列表
        output_path: 合并后的输出文件路径
        layout: 布局配置字典，包含 orientation、rows、cols、rotate
        mode: 合并模式，可选 "普通" 或 "图像"，默认 "普通"
        margins: 页边距配置（mm），可选，格式 {"top": 10, "bottom": 10, "left": 10, "right": 10}
        crop_marks: 裁切线配置，可选，格式 {"show": true, "left_mm": 5, "right_mm": 5}

    返回值:
        Dict[str, Any]: 包含 success（是否成功）和 message（提示信息）的字典
    """
    valid, msg = _validate_pdf_paths(pdf_paths)
    if not valid:
        return {"success": False, "message": msg}

    valid, msg = _ensure_output_dir(output_path)
    if not valid:
        return {"success": False, "message": msg}

    pdf_paths = _normalize_paths(pdf_paths)

    # 合并可选参数到 layout 配置中
    merged_layout = layout.copy()
    if margins is not None and isinstance(margins, dict):
        merged_layout['margins'] = {
            'top': margins.get('top', 10),
            'bottom': margins.get('bottom', 10),
            'left': margins.get('left', 10),
            'right': margins.get('right', 10),
        }
    if crop_marks is not None and isinstance(crop_marks, dict):
        merged_layout['show_crop_marks'] = crop_marks.get('show', False)
        merged_layout['crop_mark_left'] = crop_marks.get('left_mm', 0)
        merged_layout['crop_mark_right'] = crop_marks.get('right_mm', 0)

    pdf_handler = _new_pdf_handler()
    try:
        result = pdf_handler.merge_pdfs(
            pdf_paths,
            output_path,
            merged_layout,
            mode=mode,
            batch_size=50
        )
        if result:
            return {"success": True, "message": f"合并完成，保存至: {output_path}", "output_path": output_path}
        else:
            return {"success": False, "message": "合并失败，请检查文件或日志"}
    except Exception as e:
        logger.exception("合并发票异常")
        return {"success": False, "message": f"合并异常: {str(e)}"}


def handle_extract_invoice_info(pdf_path: str) -> Dict[str, Any]:
    """
    提取单张发票的全部字段信息

    功能描述:
        调用 PDFHandler.extract_all_invoice_info 提取指定 PDF 的发票字段。

    参数:
        pdf_path: PDF 文件路径

    返回值:
        Dict[str, Any]: 包含 success、info（字段信息字典或 None）和 message 的字典
    """
    valid, msg = _validate_pdf_paths([pdf_path])
    if not valid:
        return {"success": False, "info": None, "message": msg}

    pdf_path = os.path.abspath(pdf_path)
    pdf_handler = _new_pdf_handler()
    try:
        info = pdf_handler.extract_all_invoice_info(pdf_path)
        if info is None:
            return {"success": False, "info": None, "message": "无法识别该发票类型（可能是图片格式）"}
        return {"success": True, "info": info, "message": "提取成功"}
    except Exception as e:
        logger.exception("提取发票信息异常: %s", pdf_path)
        return {"success": False, "info": None, "message": f"提取异常: {str(e)}"}


def handle_batch_extract_invoice_info(pdf_paths: List[str]) -> Dict[str, Any]:
    """
    批量提取多张发票的字段信息

    功能描述:
        调用 InvoiceService.batch_extract 批量提取多张 PDF 发票的字段。

    参数:
        pdf_paths: PDF 文件路径列表

    返回值:
        Dict[str, Any]: 包含 success、results（提取结果列表）和 message 的字典
    """
    valid, msg = _validate_pdf_paths(pdf_paths)
    if not valid:
        return {"success": False, "results": [], "message": msg}

    pdf_paths = _normalize_paths(pdf_paths)
    pdf_handler = _new_pdf_handler()
    service = InvoiceService(pdf_handler)
    try:
        results = service.batch_extract(pdf_paths)
        return {"success": True, "results": results, "message": f"共提取 {len(results)} 个文件"}
    except Exception as e:
        logger.exception("批量提取发票信息异常")
        return {"success": False, "results": [], "message": f"批量提取异常: {str(e)}"}


def handle_batch_rename_invoices(pdf_paths: List[str], rule: str, dry_run: bool = False) -> Dict[str, Any]:
    """
    按规则批量重命名发票 PDF 文件

    功能描述:
        调用 InvoiceService.batch_rename 根据规则批量重命名文件。
        支持 dry_run 预览模式，预览模式下不会真正修改文件系统。

    参数:
        pdf_paths: 需要重命名的 PDF 文件路径列表
        rule: 重命名规则字符串，支持 {发票类型}、{开票日期} 等占位符
        dry_run: 是否为预览模式，默认 False

    返回值:
        Dict[str, Any]: 包含 success、renamed_count、failed_count、unrecognized_files、
                       renamed_map、dry_run 和 message 的字典
    """
    valid, msg = _validate_pdf_paths(pdf_paths)
    if not valid:
        return {"success": False, "renamed_count": 0, "failed_count": 0,
                "unrecognized_files": [], "renamed_map": {}, "dry_run": dry_run,
                "message": msg}

    if not rule:
        return {"success": False, "renamed_count": 0, "failed_count": 0,
                "unrecognized_files": [], "renamed_map": {}, "dry_run": dry_run,
                "message": "重命名规则为空"}

    pdf_paths = _normalize_paths(pdf_paths)
    pdf_handler = _new_pdf_handler()
    service = InvoiceService(pdf_handler)
    try:
        result = service.batch_rename(pdf_paths, rule, dry_run=dry_run)
        action = "将会重命名" if dry_run else "成功重命名"
        message = f"{action} {result['renamed_count']} 个文件"
        if result['failed_count'] > 0:
            message += f"，失败 {result['failed_count']} 个"
        if result['unrecognized_files']:
            message += f"，未能识别 {len(result['unrecognized_files'])} 个文件"

        return {
            "success": True,
            "renamed_count": result['renamed_count'],
            "failed_count": result['failed_count'],
            "unrecognized_files": result['unrecognized_files'],
            "renamed_map": result['renamed_map'],
            "dry_run": dry_run,
            "message": message
        }
    except Exception as e:
        logger.exception("批量重命名异常")
        return {"success": False, "renamed_count": 0, "failed_count": 0,
                "unrecognized_files": [], "renamed_map": {}, "dry_run": dry_run,
                "message": f"批量重命名异常: {str(e)}"}


def handle_export_invoice_list(pdf_infos: List[Dict[str, Any]], output_path: str,
                               duplicate_codes: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    将发票信息列表导出为 Excel 文件

    功能描述:
        调用 InvoiceService.export_to_excel 将发票信息导出为 Excel。

    参数:
        pdf_infos: 发票信息字典列表，每个字典需包含 name、amount、tax_amount、
                   invoice_date、invoice_code、path、mod_time、size 等字段
        output_path: 输出 Excel 文件路径
        duplicate_codes: 重复发票号码列表，可选

    返回值:
        Dict[str, Any]: 包含 success、output_path 和 message 的字典
    """
    if not pdf_infos:
        return {"success": False, "output_path": output_path, "message": "待导出列表为空"}

    valid, msg = _ensure_output_dir(output_path)
    if not valid:
        return {"success": False, "output_path": output_path, "message": msg}

    pdf_handler = _new_pdf_handler()
    service = InvoiceService(pdf_handler)
    dup_set = set(duplicate_codes) if duplicate_codes else set()

    try:
        success = service.export_to_excel(pdf_infos, output_path, duplicate_codes=dup_set)
        if success:
            return {"success": True, "output_path": output_path,
                    "message": f"导出成功，保存至: {output_path}"}
        else:
            return {"success": False, "output_path": output_path, "message": "导出失败，请检查日志"}
    except Exception as e:
        logger.exception("导出 Excel 异常")
        return {"success": False, "output_path": output_path, "message": f"导出异常: {str(e)}"}


def handle_export_invoice_list_from_paths(
    pdf_paths: List[str],
    output_path: str,
    duplicate_codes: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    按 PDF 路径列表直接导出 Excel 文件

    功能描述:
        先批量提取发票字段，再调用 InvoiceService.export_to_excel 导出为 Excel。
        适合 AI 客户端只持有文件路径的场景。

    参数:
        pdf_paths: PDF 文件路径列表
        output_path: 输出 Excel 文件路径
        duplicate_codes: 重复发票号码列表，可选

    返回值:
        Dict[str, Any]: 包含 success、output_path 和 message 的字典
    """
    valid, msg = _validate_pdf_paths(pdf_paths)
    if not valid:
        return {"success": False, "output_path": output_path, "message": msg}

    valid, msg = _ensure_output_dir(output_path)
    if not valid:
        return {"success": False, "output_path": output_path, "message": msg}

    pdf_paths = _normalize_paths(pdf_paths)
    pdf_handler = _new_pdf_handler()
    service = InvoiceService(pdf_handler)
    dup_set = set(duplicate_codes) if duplicate_codes else set()

    try:
        extract_results = service.batch_extract(pdf_paths)
        pdf_infos = []
        for item in extract_results:
            info = item.get("info") or {}
            path = item.get("path", "")
            pdf_infos.append({
                "name": os.path.basename(path),
                "amount": info.get("amount", 0.0),
                "tax_amount": info.get("tax_amount", 0.0),
                "invoice_date": info.get("invoice_date", ""),
                "invoice_code": info.get("invoice_code", ""),
                "path": path,
                "mod_time": "",
                "size": "",
            })

        success = service.export_to_excel(pdf_infos, output_path, duplicate_codes=dup_set)
        if success:
            return {"success": True, "output_path": output_path,
                    "message": f"导出成功，保存至: {output_path}"}
        else:
            return {"success": False, "output_path": output_path, "message": "导出失败，请检查日志"}
    except Exception as e:
        logger.exception("按路径导出 Excel 异常")
        return {"success": False, "output_path": output_path, "message": f"导出异常: {str(e)}"}


def handle_get_server_info() -> Dict[str, Any]:
    """
    获取 MCP Server 元信息

    返回值:
        Dict[str, Any]: 包含 name、version 和 tools 列表的字典
    """
    return {
        "name": SERVER_NAME,
        "version": SERVER_VERSION,
        "tools": [
            "merge_invoices",
            "extract_invoice_info",
            "batch_extract_invoice_info",
            "batch_rename_invoices",
            "export_invoice_list",
            "export_invoice_list_from_paths",
            "get_supported_layouts",
            "get_supported_fields",
            "get_server_info",
        ],
    }


def handle_get_supported_layouts() -> Dict[str, Any]:
    """
    获取支持的布局配置列表

    返回值:
        Dict[str, Any]: 包含 layouts（布局配置列表）的字典
    """
    pdf_handler = _new_pdf_handler()
    layouts = [
        {"name": "横向2x2", "orientation": "landscape", "rows": 2, "cols": 2, "rotate": 0},
        {"name": "横向2x4", "orientation": "landscape", "rows": 2, "cols": 4, "rotate": 0},
        {"name": "竖向1x2", "orientation": "portrait", "rows": 2, "cols": 1, "rotate": 0},
        {"name": "竖向1x3", "orientation": "portrait", "rows": 3, "cols": 1, "rotate": 0},
        {"name": "竖向2x4", "orientation": "portrait", "rows": 4, "cols": 2, "rotate": 0},
    ]

    # 通过 PDFHandler 的解析方法确认这些布局可被识别
    validated_layouts = []
    for layout in layouts:
        parsed = pdf_handler._parse_layout(layout)
        validated_layouts.append({
            "name": layout["name"],
            "orientation": parsed.get("orientation"),
            "rows": parsed.get("rows"),
            "cols": parsed.get("cols"),
            "rotate": parsed.get("rotate"),
        })

    return {"layouts": validated_layouts}


def handle_get_supported_fields() -> Dict[str, Any]:
    """
    获取重命名规则中支持的字段列表

    返回值:
        Dict[str, Any]: 包含 fields（字段列表）的字典
    """
    return {"fields": InvoiceService.get_available_fields()}
