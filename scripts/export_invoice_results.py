#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""发票识别结果导出（标准结果文件）

对指定目录下的全部票据文件（PDF / 图片 / OFD）执行字段提取，
按发票字段注册表（invoice_field_registry）的字段口径导出标准结果文件：

    <out-dir>/发票识别结果.xlsx
        工作表「发票列表」：每文件一行，含票种、7 票种全部字段、识别状态、失败原因
        工作表「汇总统计」：分票种文件数/成功数/金额税额合计 + 分字段非空覆盖率
    <out-dir>/发票识别结果.json
        与表格同构的机器可读结果（含 _meta 说明）

用法：
    python scripts/export_invoice_results.py --source-dir "D:\\dir" --out-dir reports

退出码：0 导出成功；1 导出失败。
"""

import argparse
import contextlib
import io
import json
import os
import sys
import time
from collections import Counter, OrderedDict

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SUPPORTED_EXT = ('.pdf', '.jpg', '.jpeg', '.png', '.ofd')
IMAGE_EXT = ('.jpg', '.jpeg', '.png')

# 失败原因分类
REASON_IMAGE = '图片票据（提取器不支持图片，需 OCR）'
REASON_TRIP = '网约车/出租车行程单（非发票）'
REASON_PAYMENT = '非发票凭证（电子缴款凭证）'
REASON_OFD = 'OFD 文件（未参与字段提取）'
REASON_NO_MATCH = '未命中任何票种关键词'
REASON_ERROR = '提取过程异常'


# 注册表 _COMMON_FIELDS 只有 发票类型/开票日期/发票号码/金额，税额需单独补入
EXTRA_FIELD_KEYS = ('tax_amount',)


def field_order(base_keys):
    """把额外字段插入到注册表字段之后，保持稳定顺序"""
    keys = list(base_keys)
    for key in EXTRA_FIELD_KEYS:
        if key not in keys:
            keys.append(key)
    return keys


def _ensure_paths():
    """把仓库内 code 与 .pylibs（本地依赖）加入 sys.path"""
    for path in (os.path.join(_REPO_ROOT, '.pylibs'), os.path.join(_REPO_ROOT, 'code')):
        if os.path.isdir(path) and path not in sys.path:
            sys.path.insert(0, path)


def collect_files(root):
    """递归收集受支持的票据文件，按路径排序"""
    files = []
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            if os.path.splitext(name)[1].lower() in SUPPORTED_EXT:
                files.append(os.path.join(dirpath, name))
    files.sort()
    return files


def read_pdf_text(path):
    """读取 PDF 文本层，失败返回空串"""
    try:
        import pymupdf
    except ImportError:  # pragma: no cover
        import fitz as pymupdf
    try:
        with pymupdf.open(path) as doc:
            return '\n'.join(page.get_text() for page in doc)
    except Exception:
        return ''


def classify_failure(path):
    """为未提取到发票信息的文件归类失败原因"""
    ext = os.path.splitext(path)[1].lower()
    if ext in IMAGE_EXT:
        return REASON_IMAGE
    if ext == '.ofd':
        return REASON_OFD
    text = read_pdf_text(path)
    if not text.strip():
        return 'PDF 无文本层（扫描件，需 OCR）'
    # 票面文字常被空格/换行割裂，同时用「去空白正文 + 文件名」判定
    probe = ''.join(text.split()) + os.path.splitext(os.path.basename(path))[0]
    if '行程报销单' in probe or '行程单' in probe or '行程总计' in probe or '可开票金额' in probe:
        return REASON_TRIP
    if '缴款凭证' in probe:
        return REASON_PAYMENT
    return REASON_NO_MATCH


def build_rows(files, source_dir):
    """逐个文件提取字段，返回结果行"""
    from core.pdf_handler import PDFHandler
    from core.invoice_field_registry import ALL_FIELD_KEYS, INVOICE_TYPE_LABELS

    handler = PDFHandler()
    field_keys = field_order(ALL_FIELD_KEYS)
    rows = []
    for index, path in enumerate(files, 1):
        rel = os.path.relpath(path, source_dir)
        stat = os.stat(path)
        started = time.time()
        buf = io.StringIO()
        info = None
        error = None
        try:
            with contextlib.redirect_stdout(buf):
                info = handler.extract_all_invoice_info(path)
        except Exception as exc:  # 单文件异常不中断整批
            info = None
            error = '%s: %s' % (type(exc).__name__, exc)
        elapsed = round((time.time() - started) * 1000, 1)

        row = OrderedDict()
        row['序号'] = index
        row['相对路径'] = rel
        row['文件名'] = os.path.basename(path)
        row['识别状态'] = '成功' if info else '未识别'
        row['票种标识'] = (info or {}).get('invoice_type_key', '')
        row['票种'] = INVOICE_TYPE_LABELS.get(row['票种标识'], '')
        for key in field_keys:
            row[key] = (info or {}).get(key, '')
        if info:
            row['失败原因'] = ''
        else:
            row['失败原因'] = REASON_ERROR if error else classify_failure(path)
        row['耗时毫秒'] = elapsed
        row['文件大小'] = stat.st_size
        row['修改时间'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stat.st_mtime))
        if error:
            row['异常信息'] = error
        rows.append(row)
        if index % 20 == 0:
            print('  已处理 %d/%d' % (index, len(files)))
    return rows, field_keys, INVOICE_TYPE_LABELS


def summarize(rows, field_keys, type_labels):
    """分票种汇总 + 分字段非空覆盖率"""
    groups = OrderedDict()
    for key in type_labels:
        groups[type_labels[key]] = {'票种标识': key, '文件数': 0, '识别成功': 0, '未识别': 0,
                                    '金额合计': 0.0, '税额合计': 0.0}
    groups['未识别（非发票/图片）'] = {'票种标识': '', '文件数': 0, '识别成功': 0, '未识别': 0,
                                       '金额合计': 0.0, '税额合计': 0.0}

    for row in rows:
        label = row['票种'] or '未识别（非发票/图片）'
        bucket = groups.setdefault(label, {'票种标识': row['票种标识'], '文件数': 0, '识别成功': 0,
                                           '未识别': 0, '金额合计': 0.0, '税额合计': 0.0})
        bucket['文件数'] += 1
        if row['识别状态'] == '成功':
            bucket['识别成功'] += 1
            amount = row.get('amount') or 0
            tax = row.get('tax_amount') or 0
            try:
                bucket['金额合计'] += float(amount)
            except (TypeError, ValueError):
                pass
            try:
                bucket['税额合计'] += float(tax)
            except (TypeError, ValueError):
                pass
        else:
            bucket['未识别'] += 1

    coverage = OrderedDict()
    for key in field_keys:
        filled = sum(1 for row in rows if row.get(key) not in ('', None))
        coverage[key] = filled

    return groups, coverage


def write_excel(rows, groups, coverage, field_keys, output_path):
    """写标准结果文件（xlsx）"""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = '发票列表'

    headers = list(rows[0].keys()) if rows else []
    sheet.append(headers)
    for row in rows:
        sheet.append([row.get(header, '') for header in headers])

    head_fill = PatternFill('solid', fgColor='305496')
    for cell in sheet[1]:
        cell.font = Font(color='FFFFFF', bold=True)
        cell.fill = head_fill
        cell.alignment = Alignment(horizontal='center', vertical='center')
    sheet.freeze_panes = 'A2'
    sheet.auto_filter.ref = 'A1:%s%d' % (get_column_letter(len(headers)), len(rows) + 1)

    widths = {'序号': 6, '相对路径': 46, '文件名': 40, '识别状态': 10, '票种': 12,
              '票种标识': 18, '失败原因': 30, '文件大小': 10, '修改时间': 20, '耗时毫秒': 10}
    for idx, header in enumerate(headers, 1):
        sheet.column_dimensions[get_column_letter(idx)].width = widths.get(header, 16)

    fail_fill = PatternFill('solid', fgColor='FCE4E4')
    status_col = headers.index('识别状态') + 1
    for row_index in range(2, len(rows) + 2):
        if sheet.cell(row=row_index, column=status_col).value == '未识别':
            for column in range(1, len(headers) + 1):
                sheet.cell(row=row_index, column=column).fill = fail_fill

    summary = workbook.create_sheet('汇总统计')
    summary.append(['口径', '票种', '文件数', '识别成功', '未识别', '金额合计', '税额合计'])
    for label, bucket in groups.items():
        if not bucket['文件数']:
            continue
        summary.append(['分票种统计', label, bucket['文件数'], bucket['识别成功'], bucket['未识别'],
                        round(bucket['金额合计'], 2), round(bucket['税额合计'], 2)])
    summary.append(['分票种统计', '合计', len(rows),
                    sum(1 for r in rows if r['识别状态'] == '成功'),
                    sum(1 for r in rows if r['识别状态'] != '成功'),
                    round(sum((r.get('amount') or 0) for r in rows
                              if isinstance(r.get('amount'), (int, float))), 2),
                    round(sum((r.get('tax_amount') or 0) for r in rows
                              if isinstance(r.get('tax_amount'), (int, float))), 2)])
    summary.append([])
    summary.append(['字段覆盖', '字段', '非空文件数', '占比'])
    total = len(rows) or 1
    for key, filled in coverage.items():
        summary.append(['字段覆盖', key, filled, '%.1f%%' % (filled * 100.0 / total)])
    for cell in summary[1]:
        cell.font = Font(bold=True)

    workbook.save(output_path)


def main():
    parser = argparse.ArgumentParser(description='导出发票识别标准结果文件')
    parser.add_argument('--source-dir', required=True, help='待识别票据所在目录')
    parser.add_argument('--out-dir', default=os.path.join(_REPO_ROOT, 'reports'),
                        help='结果文件输出目录（默认 reports）')
    args = parser.parse_args()

    source_dir = os.path.abspath(args.source_dir)
    if not os.path.isdir(source_dir):
        print('[错误] 目录不存在: %s' % source_dir)
        return 1

    _ensure_paths()
    files = collect_files(source_dir)
    if not files:
        print('[错误] 目录内无受支持的票据文件: %s' % source_dir)
        return 1
    print('发现票据文件 %d 个: %s' % (len(files), source_dir))

    started = time.time()
    rows, field_keys, type_labels = build_rows(files, source_dir)
    groups, coverage = summarize(rows, field_keys, type_labels)

    os.makedirs(args.out_dir, exist_ok=True)
    excel_path = os.path.join(args.out_dir, '发票识别结果.xlsx')
    json_path = os.path.join(args.out_dir, '发票识别结果.json')
    write_excel(rows, groups, coverage, field_keys, excel_path)

    success = sum(1 for r in rows if r['识别状态'] == '成功')
    payload = OrderedDict()
    payload['_meta'] = OrderedDict([
        ('title', '发票识别标准结果文件'),
        ('source_dir', source_dir),
        ('generated_on', time.strftime('%Y-%m-%d %H:%M:%S')),
        ('generator', 'scripts/export_invoice_results.py'),
        ('field_order_source', 'core.invoice_field_registry.ALL_FIELD_KEYS + tax_amount'),
        ('field_convention', OrderedDict([
            ('amount', '价税合计（小写）金额；火车票取票价；行程单取合计'),
            ('tax_amount', '合计行税额'),
            ('invoice_date', '开票日期（YYYY-MM-DD）'),
            ('invoice_code', '发票号码（20 位全电发票号码；旧版票面仅有 12 位代码/8 位号码时为空）'),
            ('buyer_name', '购买方名称；火车票为旅客姓名（该票种设计）'),
            ('seller_name', '销售方名称'),
        ])),
        ('total_files', len(rows)),
        ('recognized', success),
        ('not_recognized', len(rows) - success),
        ('elapsed_seconds', round(time.time() - started, 1)),
    ])
    payload['invoices'] = rows
    payload['summary'] = OrderedDict([
        ('by_type', groups),
        ('field_coverage', coverage),
    ])
    with open(json_path, 'w', encoding='utf-8') as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=1)

    print('已导出: %s' % excel_path)
    print('已导出: %s' % json_path)
    print('文件 %d / 识别成功 %d / 未识别 %d / 耗时 %.1fs'
          % (len(rows), success, len(rows) - success, time.time() - started))
    return 0


if __name__ == '__main__':
    sys.exit(main())

