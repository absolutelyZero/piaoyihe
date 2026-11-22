#!/usr/bin/env python3
"""
发票字段实测比对脚本

用真实发票目录校验字段提取是否正确：
- 从基线文件读取期望字段值（基线由人工/ AI 读取票面文本整理，不由被测代码生成）
- 调用被测的 PDFHandler.extract_all_invoice_info 取得实际值
- 逐字段比对并输出差异表

设计约束：
- 脚本自身只使用标准库（json / argparse / pathlib），不直接依赖 PyMuPDF；
  PDF 文本解析由被测代码完成（它本就依赖 PyMuPDF）。
- 样本目录以参数传入，默认指向约定的实测目录，不把绝对路径写死进断言。

用法：
    python scripts/compare_invoice_fields.py
    python scripts/compare_invoice_fields.py --source-dir D:\\some\\invoices
    python scripts/compare_invoice_fields.py --baseline path/to/expected-fields.json
    python scripts/compare_invoice_fields.py --verbose

退出码：
    0  全部一致（或样本目录为空，无可比对项）
    1  存在字段差异或提取异常
"""

import argparse
import json
import os
import sys
from pathlib import Path


# 默认实测样本目录（在 git 仓库之外，不进版本控制）
DEFAULT_SOURCE_DIR = r'D:\minipro\piaoyihe\piaoyihe_test'

# 默认基线文件（相对本脚本所在仓库）
_REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BASELINE = _REPO_ROOT / 'openspec' / 'changes' / 'per-invoice-type-rename-rules' / 'baseline' / 'expected-fields.json'

# 不参与字段比对的原因
EXCLUDED_SUFFIXES = {'.rar', '.zip', '.7z'}

# 比对时容忍为空的字段（基线中值为 None 表示未核实，跳过严格断言）
_UNVERIFIED = object()


def _norm_text(value):
    """归一化字符串：去空白，便于跨排版比较"""
    if value is None:
        return ''
    return ''.join(str(value).split())


def _cmp_values(expected, actual):
    """
    比较期望值与实际值

    返回 (是否一致, 说明)
    """
    if expected is None:
        # 基线未核实
        return _UNVERIFIED, '未核实'

    if isinstance(expected, (int, float)) and not isinstance(expected, bool):
        try:
            actual_num = float(actual)
        except (TypeError, ValueError):
            return False, f'期望数值 {expected}，实际非数值 {actual!r}'
        if abs(actual_num - float(expected)) < 0.005:
            return True, ''
        return False, f'期望 {expected}，实际 {actual}'

    exp_norm = _norm_text(expected)
    act_norm = _norm_text(actual)
    if exp_norm == act_norm:
        return True, ''
    return False, f'期望 {expected!r}，实际 {actual!r}'


def load_baseline(path: Path):
    """读取基线文件"""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def collect_pdfs(source_dir: Path):
    """递归收集样本目录下的 PDF"""
    return sorted(p for p in source_dir.rglob('*.pdf') if p.is_file())


def build_handler():
    """
    构造被测的 PDFHandler

    把仓库的 code 目录加入 sys.path，导入 core.pdf_handler。
    导入失败时返回 None（通常是缺少 PyMuPDF）。
    """
    code_dir = _REPO_ROOT / 'code'
    if str(code_dir) not in sys.path:
        sys.path.insert(0, str(code_dir))
    try:
        from core.pdf_handler import PDFHandler
        return PDFHandler()
    except Exception as exc:  # noqa: BLE001 - 需要把导入失败原因报给用户
        print(f'[错误] 无法导入被测字段提取模块: {exc}', file=sys.stderr)
        print('       请确认已安装 requirements.txt 中的依赖（尤其是 PyMuPDF）。',
              file=sys.stderr)
        return None


def main():
    parser = argparse.ArgumentParser(
        description='用真实发票目录比对字段提取结果与基线'
    )
    parser.add_argument(
        '--source-dir', default=DEFAULT_SOURCE_DIR,
        help=f'发票样本目录（默认 {DEFAULT_SOURCE_DIR}）'
    )
    parser.add_argument(
        '--baseline', default=str(DEFAULT_BASELINE),
        help='基线文件路径（默认指向本变更的 expected-fields.json）'
    )
    parser.add_argument(
        '--verbose', action='store_true',
        help='输出每个文件的详细比对过程'
    )
    args = parser.parse_args()

    source_dir = Path(args.source_dir)
    baseline_path = Path(args.baseline)

    print('=' * 70)
    print('发票字段实测比对')
    print('=' * 70)
    print(f'样本目录: {source_dir}')
    print(f'基线文件: {baseline_path}')

    # 样本目录不存在：报告并以 0 退出（无可比对项，不视为失败）
    if not source_dir.is_dir():
        print(f'\n[提示] 样本目录不存在，跳过实测: {source_dir}')
        print('       可通过 --source-dir 指定实际的发票目录。')
        print('\n结论: 无样本，未执行比对')
        return 0

    if not baseline_path.is_file():
        print(f'\n[错误] 基线文件不存在: {baseline_path}', file=sys.stderr)
        return 1

    baseline = load_baseline(baseline_path)
    baseline_invoices = baseline.get('invoices', [])

    # 基线显式声明的排除项（如应用自身的合并产物），不报「基线缺失」
    excluded = baseline.get('_meta', {}).get('excluded_from_baseline', {}) or {}
    excluded_names = {Path(k.replace('\\', '/')).name for k in excluded}

    # 基线按「相对路径」索引：兼容只用文件名记录的条目
    by_relpath = {}
    by_name = {}
    for item in baseline_invoices:
        fname = item.get('file', '')
        rel = fname.replace('\\', '/')
        by_relpath[rel] = item
        by_name[Path(rel).name] = item

    pdfs = collect_pdfs(source_dir)
    if not pdfs:
        print(f'\n[提示] 样本目录下未找到 PDF 文件: {source_dir}')
        print('\n结论: 无样本，未执行比对')
        return 0

    handler = build_handler()
    if handler is None:
        return 1

    print(f'\n共发现 {len(pdfs)} 个 PDF，基线含 {len(baseline_invoices)} 条记录\n')

    compared = 0
    matched = 0
    mismatches = []       # (文件名, 字段, 说明)
    unverified = []       # (文件名, 字段)
    no_text_layer = []    # 无法提取文本的文件
    missing_in_baseline = []
    type_coverage = set()

    for pdf in pdfs:
        rel = pdf.relative_to(source_dir).as_posix()

        # 基线声明排除的文件（如合并产物）不计入任何统计
        if pdf.name in excluded_names:
            if args.verbose:
                print(f'[排除] {rel} —— {excluded.get(rel) or excluded.get(pdf.name) or "基线声明排除"}')
            continue

        entry = by_relpath.get(rel) or by_name.get(pdf.name)

        if entry is None:
            missing_in_baseline.append(rel)
            if args.verbose:
                print(f'[跳过] {rel} —— 基线中无对应记录')
            continue

        evidence = entry.get('evidence')
        expected = entry.get('expected')

        # 基线明确标注无文本层：只验证“提不出字段”这一事实，不做字段比对
        if evidence == 'no_text_layer' or expected is None:
            no_text_layer.append(rel)
            if args.verbose:
                print(f'[无文本层] {rel} —— 不参与字段比对')
            continue

        try:
            actual = handler.extract_all_invoice_info(str(pdf))
        except Exception as exc:  # noqa: BLE001
            mismatches.append((rel, '<提取异常>', str(exc)))
            continue

        if actual is None:
            mismatches.append((rel, '<提取结果>', '提取返回 None（无法识别票种）'))
            continue

        compared += 1
        file_ok = True
        type_coverage.add(actual.get('invoice_type_key') or '<未知>')

        if args.verbose:
            print(f'[比对] {rel}  (类型: {actual.get("invoice_type_key")})')

        for field, exp_val in expected.items():
            act_val = actual.get(field)
            ok, detail = _cmp_values(exp_val, act_val)
            if ok is _UNVERIFIED:
                unverified.append((rel, field))
                continue
            if not ok:
                file_ok = False
                mismatches.append((rel, field, detail))
                if args.verbose:
                    print(f'     ✗ {field}: {detail}')
            elif args.verbose:
                print(f'     ✓ {field}')

        if file_ok:
            matched += 1

    # ========== 输出报告 ==========
    print('-' * 70)
    print('比对结果')
    print('-' * 70)
    print(f'参与字段比对的文件: {compared}')
    print(f'全部字段一致的文件: {matched}')

    if mismatches:
        print(f'\n【字段差异】共 {len(mismatches)} 处：')
        for rel, field, detail in mismatches:
            print(f'  ✗ {rel}')
            print(f'      {field}: {detail}')

    if unverified:
        print(f'\n【未核实字段】共 {len(unverified)} 处（基线中标记为未核实，跳过断言）：')
        for rel, field in unverified:
            print(f'  - {rel} :: {field}')

    if no_text_layer:
        print(f'\n【无法提取】共 {len(no_text_layer)} 个（无文本层，不参与字段比对）：')
        for rel in no_text_layer:
            print(f'  - {rel}')

    if missing_in_baseline:
        print(f'\n【基线缺失】共 {len(missing_in_baseline)} 个样本在基线中无记录：')
        for rel in missing_in_baseline:
            print(f'  - {rel}')

    # ========== 票种覆盖情况 ==========
    coverage = baseline.get('_meta', {}).get('coverage', {})
    covered = coverage.get('covered_types', [])
    missing_types = coverage.get('missing_types', [])

    print('\n' + '-' * 70)
    print('票种覆盖情况')
    print('-' * 70)
    print(f'基线声明已覆盖: {len(covered)}/7  {covered}')
    print(f'基线声明未覆盖: {len(missing_types)}/7   {missing_types}')
    if missing_types:
        print(f'\n[注意] 以下票种无真实样本，只能靠单测与构造文案验证，不计入本次实测通过：')
        for t in missing_types:
            print(f'  - {t}')

    # 实际识别到的票种（用于核对基线声明是否准确）
    actual_types = {t for t in type_coverage if t != '<未知>'}
    print(f'\n本次实际识别到的票种: {sorted(actual_types)}')

    # ========== 结论 ==========
    print('\n' + '=' * 70)
    if mismatches:
        print(f'结论: 存在 {len(mismatches)} 处字段差异，实测未通过')
        return 1

    if compared == 0:
        print('结论: 无参与比对的样本（仅有无法提取或基线缺失的文件）')
        return 0

    print(f'结论: 已核实字段全部一致（{matched}/{compared} 个文件通过）')
    if missing_types:
        print(f'      注意: 仍有 {len(missing_types)} 类票种未被真实样本覆盖')
    return 0


if __name__ == '__main__':
    sys.exit(main())
