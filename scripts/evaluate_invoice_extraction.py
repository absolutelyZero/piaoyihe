#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""发票字段提取准确度评测（可复跑）

以 `tests/data/invoice_field_ground_truth.json` 为基准，对语料目录做全量字段提取，
输出：
    <out-dir>/字段提取评测明细.json   逐文件逐字段的 got/want/ok
    <out-dir>/字段提取测试报告.md      分票种/分字段准确率 + 缺陷清单 + 根因

用法：
    python scripts/evaluate_invoice_extraction.py
    python scripts/evaluate_invoice_extraction.py --source-dir "D:\\dir" --out-dir reports

退出码：0 达成本脚本内声明的基线；1 低于基线或语料缺失。
"""

import argparse
import contextlib
import hashlib
import io
import json
import os
import sys
import time
from collections import Counter, OrderedDict, defaultdict

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_SOURCE_DIR = r'D:\公司文档\05.培训(公共)\报销'
DEFAULT_TRUTH = os.path.join(_REPO_ROOT, 'tests', 'data', 'invoice_field_ground_truth.json')
DEFAULT_OUT_DIR = os.path.join(_REPO_ROOT, 'reports')

SUPPORTED_EXT = ('.pdf', '.jpg', '.jpeg', '.png', '.ofd')

# 字段名 → ground truth 中的键名
FIELD_ALIASES = OrderedDict([
    ('invoice_type_key', 'invoice_type_key'),
    ('amount', 'amount'),
    ('tax_amount', 'tax_amount'),
    ('invoice_date', 'invoice_date'),
    ('invoice_code', 'invoice_code'),
    ('buyer_name', 'buyer_name'),
    ('seller_name', 'seller_name'),
])

NUMERIC_FIELDS = ('amount', 'tax_amount')

# 基线阈值：不低于本次实测值，用于阻止回归
# 基线阈值 = 本次实测值向下取整，用于阻止回归；键名与 measured 一一对应
BASELINES = OrderedDict([
    ('type_accuracy', 0.93),          # 实测 93.8%（145 个文件里 9 个票种判定不一致：6 假阳性 + 3 合并件）
    ('amount_accuracy', 0.99),        # 实测 100%
    ('tax_amount_accuracy', 0.99),    # 实测 100%
    ('invoice_date_accuracy', 0.99),  # 实测 100%
    ('invoice_code_accuracy', 0.99),  # 实测 100%
    ('buyer_name_accuracy', 1.0),     # 实测 100%（P0/P1 修复后）
    ('seller_name_accuracy', 1.0),    # 实测 100%（P0/P1 修复后）
    ('false_negative_rate', 0.0),     # 实测 0
])


def _ensure_paths():
    for path in (os.path.join(_REPO_ROOT, '.pylibs'), os.path.join(_REPO_ROOT, 'code')):
        if os.path.isdir(path) and path not in sys.path:
            sys.path.insert(0, path)


def collect_files(root):
    files = []
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            if os.path.splitext(name)[1].lower() in SUPPORTED_EXT:
                files.append(os.path.join(dirpath, name))
    files.sort()
    return files


def _norm(value):
    return ('' if value is None else str(value)).strip().replace(' ', '').replace('\u3000', '')


def _compare(field, got, want):
    """返回 True/False；want 缺失时返回 None（不可比）"""
    if want is None or want == '':
        return None
    if field in NUMERIC_FIELDS:
        try:
            lhs, rhs = float(got), float(want)
        except (TypeError, ValueError):
            return False
        return abs(lhs - rhs) < 0.005
    return _norm(got) == _norm(want)


def _file_sha256(path, _buf_size=1 << 20):
    """文件内容指纹，用于语料被重命名后仍能匹配基准行"""
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for chunk in iter(lambda: handle.read(_buf_size), b''):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_renamed(truth, produced, source_dir):
    """基准行的 rel 在提取结果里找不到时，按 sha256 内容指纹重新定位

    语料可能被应用自身的批量重命名改过文件名，此时 rel 会失配、表现为「漏检」。
    做法：把「已提取到但没被任何基准行认领」的文件按内容哈希，与缺失基准行的
    sha256 配对。只有在确实有基准行没匹配上时才计算指纹（避免每次评测都哈希语料）。
    命中后把提取结果搬到基准 rel 名下，返回 {基准 rel: 语料实际 rel}。
    """
    missing = [rel for rel in truth if rel not in produced and (truth[rel] or {}).get('sha256')]
    if not missing:
        return OrderedDict()

    # 语料里存在字节完全相同的重复票据，一个指纹可能对应多个基准行
    wanted = OrderedDict()
    for rel in missing:
        wanted.setdefault(truth[rel]['sha256'], []).append(rel)
    resolved = OrderedDict()
    for actual_rel in list(produced.keys()):
        if not wanted:
            break
        path = os.path.join(source_dir, actual_rel)
        if not os.path.isfile(path):
            continue
        try:
            digest = _file_sha256(path)
        except OSError:
            continue
        pending = wanted.get(digest)
        if not pending:
            continue
        truth_rel = pending.pop(0)
        if not pending:
            wanted.pop(digest, None)
        produced[truth_rel] = produced.pop(actual_rel)
        resolved[truth_rel] = actual_rel
    return resolved


def extract_all(files, source_dir):
    """逐文件执行字段提取，返回 {rel: info}"""
    from core.pdf_handler import PDFHandler

    handler = PDFHandler()
    results = {}
    for index, path in enumerate(files, 1):
        rel = os.path.relpath(path, source_dir)
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                results[rel] = handler.extract_all_invoice_info(path)
        except Exception as exc:  # 单文件异常不中断整批
            results[rel] = None
            print('  [异常] %s: %s: %s' % (rel, type(exc).__name__, exc))
        if index % 20 == 0:
            print('  已处理 %d/%d' % (index, len(files)))
    return results


def evaluate(source_dir, truth_path):
    """跑全量提取并逐字段比对，返回评测结果结构"""
    with io.open(truth_path, encoding='utf-8') as handle:
        truth_payload = json.load(handle)
    truth = OrderedDict((row['rel'], row) for row in truth_payload['invoices'])

    files = collect_files(source_dir)
    started = time.time()
    produced = extract_all(files, source_dir)
    renamed = resolve_renamed(truth, produced, source_dir)
    elapsed = round(time.time() - started, 1)

    records = []
    for rel, case in truth.items():
        info = produced.get(rel)
        expected = case.get('expected') or {}
        want_type = expected.get('invoice_type_key')
        record = OrderedDict()
        record['rel'] = rel
        record['kind'] = case.get('kind')
        record['evidence'] = case.get('evidence')
        record['note'] = case.get('note', '')
        record['n_invoices'] = case.get('n_invoices', 1)
        record['app_recognized'] = info is not None
        record['expect_recognized'] = want_type is not None
        record['type_ok'] = (info is not None) == (want_type is not None) and \
                            (want_type is None or (info or {}).get('invoice_type_key') == want_type)
        # 多票合并件与未识别件不参与字段一致率
        record['field_scored'] = bool(info) and bool(want_type) and record['n_invoices'] < 2
        record['fields'] = OrderedDict()
        for field, gt_key in FIELD_ALIASES.items():
            want = expected.get(gt_key)
            got = (info or {}).get(field)
            verdict = None if not record['field_scored'] else _compare(field, got, want)
            record['fields'][field] = OrderedDict([('got', got), ('want', want), ('ok', verdict)])
        records.append(record)

    missing = [rel for rel in truth if rel not in produced]
    extra = [rel for rel in produced if rel not in truth]
    return OrderedDict([
        ('source_dir', source_dir),
        ('truth_path', truth_path),
        ('evaluated_on', time.strftime('%Y-%m-%d %H:%M:%S')),
        ('elapsed_seconds', elapsed),
        ('file_count', len(files)),
        ('missing_from_corpus', missing),
        ('missing_from_truth', extra),
        ('renamed_in_corpus', OrderedDict(renamed)),
        ('records', records),
    ])


def summarize(result):
    """分票种/分字段统计 + 缺陷清单 + 假阳性/漏检清单"""
    records = result['records']

    expected_invoices = [r for r in records if r['expect_recognized']]
    not_invoices = [r for r in records if not r['expect_recognized']]
    false_negatives = [r['rel'] for r in expected_invoices if not r['app_recognized']]
    false_positives = [(r['rel'], (r['fields']['invoice_type_key']['got'] or '')) for r in not_invoices
                       if r['app_recognized']]
    type_mismatch = [(r['rel'], r['fields']['invoice_type_key']['got'], r['fields']['invoice_type_key']['want'])
                     for r in expected_invoices
                     if r['app_recognized'] and not r['type_ok']]

    totals = OrderedDict((field, [0, 0]) for field in FIELD_ALIASES)
    by_type = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for record in records:
        if not record['field_scored']:
            continue
        type_key = record['fields']['invoice_type_key']['want'] or '?'
        for field, cell in record['fields'].items():
            if cell['ok'] is None:
                continue
            totals[field][0] += 1
            by_type[type_key][field][0] += 1
            if cell['ok']:
                totals[field][1] += 1
                by_type[type_key][field][1] += 1

    def rate(pair):
        compared, matched = pair
        return (matched / compared) if compared else None

    type_total = len(records)
    type_correct = sum(1 for r in records if r['type_ok'])

    defects = []
    for record in records:
        if not record['field_scored']:
            continue
        bad = [(field, cell['got'], cell['want']) for field, cell in record['fields'].items()
               if cell['ok'] is False]
        if bad:
            defects.append(OrderedDict([
                ('rel', record['rel']),
                ('invoice_type_key', record['fields']['invoice_type_key']['want']),
                ('fields', [OrderedDict([('field', f), ('got', g), ('want', w)]) for f, g, w in bad]),
            ]))

    return OrderedDict([
        ('expected_invoices', len(expected_invoices)),
        ('recognized', len(expected_invoices) - len(false_negatives)),
        ('false_negatives', false_negatives),
        ('false_positive_count', len(false_positives)),
        ('false_positives', false_positives),
        ('type_accuracy', type_correct / type_total if type_total else None),
        ('type_mismatch', type_mismatch),
        ('field_rates', OrderedDict((field, OrderedDict([
            ('compared', totals[field][0]), ('matched', totals[field][1]), ('rate', rate(totals[field]))]))
            for field in FIELD_ALIASES)),
        ('by_type', OrderedDict((type_key, OrderedDict(
            (field, OrderedDict([('compared', pair[0]), ('matched', pair[1]), ('rate', rate(pair))]))
            for field, pair in fields.items()))
            for type_key, fields in by_type.items())),
        ('defects', defects),
    ])


def check_baselines(stats):
    """与 BASELINES 比较，返回 (是否达标, [(指标, 实测, 基线)])"""
    measured = OrderedDict([
        ('type_accuracy', stats['type_accuracy']),
        ('false_negative_rate', len(stats['false_negatives']) / max(stats['expected_invoices'], 1)),
    ])
    for field in ('amount', 'tax_amount', 'invoice_date', 'invoice_code', 'buyer_name', 'seller_name'):
        measured['%s_accuracy' % field] = stats['field_rates'][field]['rate']
    rows = []
    passed = True
    for name, baseline in BASELINES.items():
        actual = measured.get(name)
        if actual is None:
            rows.append((name, None, baseline, 'N/A'))
            continue
        if name == 'false_negative_rate':
            ok = actual <= baseline
        else:
            ok = actual >= baseline
        passed = passed and ok
        rows.append((name, actual, baseline, 'PASS' if ok else 'FAIL'))
    return passed, rows


# 缺陷 → 根因映射（依据源码与票面文本层实证）
ROOT_CAUSES = [
    OrderedDict([
        ('title', '机票票面新版式未被识别策略覆盖'),
        ('status', '已修复（2026-11-12）：flight_ticket.py 增加「购买方信息/销售方信息」锚点分支与全文公司名顺序兜底，'
                   '7 个文件的 buyer/seller 全部正确'),
        ('scope', 'flight_ticket 的 buyer_name / seller_name（7 个文件全部命中）'),
        ('detail', '新版全电机票票面为「购买方信息 → 浙江贵仁信息科技股份有限公司 → 名称: → 统一社会信用代码 … → '
                   '销售方信息 → 苏州程会玩国际旅行社有限公司 → 名称:」的标签成组、取值成组版式，'
                   '标签与取值分离且购买方/销售方取值顺序与标签顺序不一致。'),
        ('code', 'code\\core\\invoice_extractors\\flight_ticket.py:140 只匹配「购买方名称：」紧邻取值的版式；'
                 ':148 的宽松正则在标签后无值时继续向后吞行，最终抓到「备注」里的乘机人信息'
                 '（如 `谢永高;航班:杭州萧山-哈尔滨太平;航班号:3U3157;起`，且被 30 字截断）；'
                 'seller 的 4 条策略只认「填开单位/销售方/航空公司」，新版票面均无这些字样 → 返回空串。'),
        ('fix', '新增按「购买方信息 / 销售方信息」锚点分区、再在该分区内取「名称」后取值的解析分支；'
                '对无标签紧邻值的版式按文本顺序回退配对；不再回退到乘机人/备注行。'),
    ]),
    OrderedDict([
        ('title', '通行费发票的买家/卖家/发票号码/出入口缺失'),
        ('status', '已修复（2026-11-12）：toll_invoice.py 增加全文公司名顺序推断、12 位代码+8 位号码回填、'
                   '「XX站入 / XX站出」出入口解析'),
        ('scope', 'toll_invoice 的 buyer_name / seller_name（3 个文件全部命中），另有 invoice_code / toll_entry / toll_exit'),
        ('detail', '这 3 张是旧版「XX增值税电子普通发票」，票面同时存在「发票代码（12 位）」「发票号码（8 位）」'
                   '和买卖双方名称，但文本层把标签与取值分块堆放。'),
        ('code', 'code\\core\\invoice_extractors\\common_invoice.py:365 extract_invoice_code 的 4 条策略全部只认 20 位数字 '
                 '→ 旧版票面取空；seller/buyer 走 _extract_name_by_layout，因左右栏判定与关键词表限制返回空串。'),
        ('fix', '增加旧版版式分支：识别「发票代码（12 位）+ 发票号码（8 位）」组合并按 代码+号码 回填；'
                '通行费票种补充「XX站入 / XX站出」正则提取 toll_entry / toll_exit。'),
    ]),
    OrderedDict([
        ('title', '公司名关键词表缺「宾馆/酒店/饭店/旅行社」'),
        ('status', '已修复（2026-11-12）：common_invoice.py 的 company_pattern 与 company_keywords 补齐后缀，'
                   '2 个住宿发票 seller 已正确'),
        ('scope', '2 个酒店住宿发票的 seller_name 被回填成买方名称'),
        ('detail', '`2509\\09-03苏州\\苏州住宿.pdf` 真卖方 `苏州市御阁商务宾馆`、'
                   '`251101\\住宿.pdf` 真卖方 `南京市雨花台区梦之香宾馆`，两者都被输出成买方 `浙江贵仁信息科技股份有限公司`。'),
        ('code', 'code\\core\\invoice_extractors\\common_invoice.py:262 的 company_pattern 关键词表为 '
                 '「公司|企业|股份|有限|集团|厂|店|中心|工作室|部」，不含「宾馆/酒店/饭店/旅行社」→ 版式法取不到候选，'
                 '随后 extract_seller_name 的策略「第二个名称:」:347 直接取 matches[1]（即买方名称）。'),
        ('fix', '关键词表补「宾馆|酒店|饭店|大酒店|旅行社|合作社|事务所」；'
                '并在 seller 兜底前校验「取到的名称不得等于 buyer_name」，相等时返回空串而非买方名称。'),
    ]),
    OrderedDict([
        ('title', 'can_handle 仅做纯关键词包含判断，无长度/密度约束'),
        ('status', '未修复（P3）：6 个假阳性仍存在，tests/test_invoice_field_accuracy.py '
                   'test_can_handle_is_keyword_only 作为回归锚点'),
        ('scope', '6 个假阳性：5 个网约车行程单被判 vat_invoice，1 份 HR 手册被判 train_ticket'),
        ('detail', '`员工手册2020.1.1.pdf` 是 44 页 HR 手册（正文 28553 字），因正文出现「1.2 火车票：个人自行购买」'
                   '命中 train_ticket 关键词；曹操/百度行程单正文含「发票」字样命中 CommonInvoiceExtractor 兜底，'
                   '并产出 `：0.0元\\n\\n\\n行程时间：2024-08` 这类垃圾 product_type。'),
        ('code', 'code\\core\\invoice_extractors\\base.py:87 `return any(keyword in text for keyword in cls.INVOICE_TYPE_KEYWORDS)`。'),
        ('fix', '在 can_handle 增加版式约束（如必须命中「电子发票（」/「增值税」+「发票代码」等票面骨架词）'
                '与文本长度上限；先判定「行程单/缴款凭证」等非发票特征并直接拒绝；'
                '对 product_type 增加清洗，丢弃含「元」「行程时间」等字样的取值。'),
    ]),
    OrderedDict([
        ('title', '多票合并件因关键词优先级漂移票种'),
        ('status', '未修复（P4）：3 个合并打印件仍从 vat_invoice 判成 train_ticket'),
        ('scope', '3 个合并打印 PDF 从 vat_invoice 被判成 train_ticket'),
        ('detail', '`251102\\发票合并打印_7张2x2.pdf`（5 张）、`251102\\发票合并打印_7张3页.pdf`（5 张）、'
                   '`251201\\发票合并_竖向2x1.pdf`（4 张）内含火车票页面，Train 提取器注册顺序在 Common 之前 → 整册被判 train_ticket。'),
        ('code', 'code\\core\\invoice_extractors\\factory.py:59 get_extractor 按 Train, Flight, Vehicle, Taxi, FixedAmount, Toll, Common 顺序逐个 can_handle，命中即返回。'),
        ('fix', '按页统计各票种关键词命中数，取占比最高者作为整册票种；或在合并件场景下标记为多票文件并逐页提取。'),
    ]),
]

# 建议的修复优先级（按影响文件数 × 影响字段数排序）
REMEDIATION = [
    'P0 ~~机票新版式 buyer/seller 解析~~ 已完成：7 个文件、14 个缺陷字段（原占全部缺陷字段的 63.6%），'
    '现在 flight_ticket 的 buyer/seller 均为 100%',
    'P1 ~~通行费旧版票据 buyer/seller~~ 已完成：3 个文件、6 个缺陷字段（27.3%）；'
    '同时补上 12 位代码 + 8 位号码回填与「XX站入/XX站出」出入口解析（这两项基准值为空，不计入缺陷统计）',
    'P2 ~~公司名关键词表补「宾馆/酒店/饭店/旅行社」~~ 已完成：2 个文件、2 个缺陷字段，'
    'seller_name 现为 100%',
    'P3 待办：can_handle 增加版式与文本长度约束、非发票特征直接拒绝——影响 6 个假阳性文件'
    '（5 行程单 + 1 HR 手册），是本语料唯一的误识别来源',
    'P4 待办：合并件按页统计票种——3 个期望为 vat_invoice 的合并打印件因内含火车票页被判成 train_ticket',
    'P5 待办：补齐 vehicle_invoice / taxi_invoice / fixed_amount_invoice 样本（当前 0 覆盖、无法评测）；'
    '另建议把 14 张图片票据纳入 OCR 或标注为「需人工录入」',
]


def _pct(value):
    return '-' if value is None else '%.1f%%' % (value * 100)


def render_report(result, stats, baseline_rows, outputs):
    """生成 Markdown 测试报告"""
    lines = []
    push = lines.append
    push('# 发票字段提取自动化测试报告')
    push('')
    push('- 语料目录：`%s`' % result['source_dir'])
    push('- 基准文件：`%s`' % os.path.relpath(result['truth_path'], _REPO_ROOT))
    push('- 评测时间：%s，提取耗时 %.1fs' % (result['evaluated_on'], result['elapsed_seconds']))
    push('- 文件总数：%d' % len(result['records']))
    push('- 结果文件：`%s`、`%s`' % (outputs['report'], outputs['detail']))
    renamed = result.get('renamed_in_corpus') or {}
    if renamed:
        push('- 语料被重命名：%d 个文件按 sha256 内容指纹重新定位（基准行的 rel 已失配）' % len(renamed))
    push('')
    push('## 0. 语料构成')
    push('')
    composition = OrderedDict()
    for record in result['records']:
        evidence = record['evidence']
        composition[evidence] = composition.get(evidence, 0) + 1
    labels = OrderedDict([
        ('text_fully_parsed', 'PDF 文本层完整（参与字段评比的候选）'),
        ('not_an_invoice', '非发票单据（网约车行程单、社保缴款凭证、HR 手册）'),
        ('image_no_text_layer', '图片票据 .jpg（提取器按设计不处理，需 OCR）'),
    ])
    renamed = result.get('renamed_in_corpus') or {}
    if renamed:
        push('语料目录里的文件名可能被应用自身的批量重命名改过，基准文件对每行记录了 sha256，'
             '本次评测按内容指纹重新定位了以下文件：')
        push('')
        push('| 基准中的相对路径 | 语料中的实际相对路径 |')
        push('| --- | --- |')
        for truth_rel, actual_rel in renamed.items():
            push('| `%s` | `%s` |' % (truth_rel, actual_rel))
        push('')
    push('| 证据类型 | 含义 | 文件数 |')
    push('| --- | --- | --- |')
    for evidence, count in composition.items():
        push('| `%s` | %s | %d |' % (evidence, labels.get(evidence, evidence), count))
    push('')
    push('票种期望分布：' + '、'.join(
        '%s=%d' % (k, v) for k, v in
        sorted(Counter(r['fields']['invoice_type_key']['want'] or '非发票'
                       for r in result['records']).items())) + '。')
    push('')
    push('## 1. 总体结果')
    push('')
    push('| 指标 | 数值 |')
    push('| --- | --- |')
    push('| 应识别发票 | %d |' % stats['expected_invoices'])
    push('| 实际识别 | %d |' % stats['recognized'])
    push('| 漏检（假阴性） | %d |' % len(stats['false_negatives']))
    push('| 误识别（假阳性） | %d |' % stats['false_positive_count'])
    push('| 票种判定准确率 | %s |' % _pct(stats['type_accuracy']))
    push('')
    push('## 2. 分字段准确率')
    push('')
    push('| 字段 | 可比文件 | 一致 | 准确率 |')
    push('| --- | --- | --- | --- |')
    for field, cell in stats['field_rates'].items():
        push('| %s | %d | %d | %s |' % (field, cell['compared'], cell['matched'], _pct(cell['rate'])))
    push('')
    push('> 统计口径：仅「期望识别 + 实际识别 + 非多票合并件」的文件参与；期望值为空（票面确实没有该字段）不计入分母。')
    push('')
    push('## 3. 分票种准确率')
    push('')
    header = '| 票种 | ' + ' | '.join(FIELD_ALIASES) + ' |'
    push(header)
    push('| --- |' + ' --- |' * len(FIELD_ALIASES))
    for type_key, cells in stats['by_type'].items():
        row = ['| `%s` ' % type_key]
        for field in FIELD_ALIASES:
            cell = cells.get(field)
            row.append(' %s ' % (_pct(cell['rate']) if cell else '-'))
        push('|'.join(row) + '|')
    push('')
    if len(stats['by_type']) < 7:
        push('> 未覆盖票种：vehicle_invoice、taxi_invoice、fixed_amount_invoice —— 语料中无对应 PDF 样本。')
        push('')
    push('## 4. 缺陷清单（%d 个文件）' % len(stats['defects']))
    push('')
    if not stats['defects']:
        push('无。')
    else:
        push('| 文件 | 票种 | 字段 | 实际值 | 期望值 |')
        push('| --- | --- | --- | --- | --- |')
        for defect in stats['defects']:
            for item in defect['fields']:
                push('| `%s` | %s | %s | `%s` | `%s` |' % (
                    defect['rel'], defect['invoice_type_key'], item['field'],
                    item['got'], item['want']))
    push('')
    push('## 4.1 字段值质量观察（准确率之外的问题）')
    push('')
    push('以下问题不影响「是否取到正确值」的一致性统计，但会影响重命名/导出可用性：')
    push('')
    push('- `product_type` 在旧版增值税发票上取到密码区乱码，例如 '
         '`- 4 5 0 / 1 / 4 / 2 `、`0900/8379/33880>0/+7`、`0323`；'
         '在 5 个网约车行程单上取到 `：0.0元\\n\\n\\n行程时间：2024-08` 这类跨行垃圾值。')
    push('- `buyer_name` 有 30 字截断（`common_invoice.py` 的 `company[:30]`），'
         '长名称如 `格林豪泰智选酒店(苏州国际教育园石湖店` 会被截成 `格林豪泰智选酒店(苏州国际教育园`。'
         '机票备注行被误抓为 buyer 的问题已随 P0 修复消除。')
    push('- `seller_name` 旧版票面的兜底值 `销售方`、`（章）` 已通过「名称必须含公司类后缀」校验剔除；'
         '仍建议兜底返回空串而非字面值，避免被下游当成真实名称。')
    push('- 票种特有字段的空值属正常范围：非机票票种的 `flight_number` / `airline`、'
         '`vin`、`plate_number`、`toll_entry` / `toll_exit` / `toll_section` 在本语料中 0 覆盖或 0 有效值。')
    push('')
    push('## 5. 票种误判')
    push('')
    if stats['false_positives']:
        push('假阳性（把非发票单据识别成发票）：')
        push('')
        for rel, got in stats['false_positives']:
            push('- `%s` → `%s`' % (rel, got))
        push('')
    if stats['type_mismatch']:
        push('票种混淆：')
        push('')
        for rel, got, want in stats['type_mismatch']:
            push('- `%s`：判成 `%s`，应为 `%s`' % (rel, got, want))
        push('')
    push('## 6. 根因分析')
    push('')
    for index, cause in enumerate(ROOT_CAUSES, 1):
        push('### 6.%d %s' % (index, cause['title']))
        push('')
        push('- 状态：%s' % cause.get('status', '未修复'))
        push('- 影响范围：%s' % cause['scope'])
        push('- 现象：%s' % cause['detail'])
        push('- 代码位置：%s' % cause['code'])
        push('- 修复方向：%s' % cause['fix'])
        push('')
    push('## 7. 修复优先级建议')
    push('')
    for item in REMEDIATION:
        push('- %s' % item)
    push('')
    push('## 8. 基线判定')
    push('')
    push('| 指标 | 实测 | 基线 | 结论 |')
    push('| --- | --- | --- | --- |')
    for name, actual, baseline, verdict in baseline_rows:
        push('| %s | %s | %s | %s |' % (name, _pct(actual), _pct(baseline), verdict))
    push('')
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description='发票字段提取准确度评测')
    parser.add_argument('--source-dir', default=DEFAULT_SOURCE_DIR, help='语料目录')
    parser.add_argument('--truth', default=DEFAULT_TRUTH, help='基准 JSON 路径')
    parser.add_argument('--out-dir', default=DEFAULT_OUT_DIR, help='报告输出目录')
    args = parser.parse_args()

    source_dir = os.path.abspath(args.source_dir)
    if not os.path.isdir(source_dir):
        print('[错误] 语料目录不存在: %s' % source_dir)
        return 1
    if not os.path.isfile(args.truth):
        print('[错误] 基准文件不存在: %s' % args.truth)
        return 1

    _ensure_paths()
    print('评测语料: %s' % source_dir)
    result = evaluate(source_dir, args.truth)
    stats = summarize(result)
    passed, baseline_rows = check_baselines(stats)

    os.makedirs(args.out_dir, exist_ok=True)
    detail_path = os.path.join(args.out_dir, '字段提取评测明细.json')
    report_path = os.path.join(args.out_dir, '字段提取测试报告.md')
    outputs = OrderedDict([
        ('report', os.path.relpath(report_path, _REPO_ROOT)),
        ('detail', os.path.relpath(detail_path, _REPO_ROOT)),
    ])

    with io.open(detail_path, 'w', encoding='utf-8', newline='\n') as handle:
        json.dump(OrderedDict([('summary', stats), ('result', result)]), handle,
                  ensure_ascii=False, indent=1)
        handle.write('\n')
    with io.open(report_path, 'w', encoding='utf-8', newline='\n') as handle:
        handle.write(render_report(result, stats, baseline_rows, outputs))

    print()
    print('票种判定 %s | 应识别 %d | 识别 %d | 漏检 %d | 假阳性 %d'
          % (_pct(stats['type_accuracy']), stats['expected_invoices'], stats['recognized'],
             len(stats['false_negatives']), stats['false_positive_count']))
    for field, cell in stats['field_rates'].items():
        print('  %-16s %3d/%3d  %s' % (field, cell['matched'], cell['compared'], _pct(cell['rate'])))
    print()
    for name, actual, baseline, verdict in baseline_rows:
        print('  [%s] %s 实测 %s / 基线 %s' % (verdict, name, _pct(actual), _pct(baseline)))
    print()
    print('已导出: %s' % report_path)
    print('已导出: %s' % detail_path)
    return 0 if passed else 1


if __name__ == '__main__':
    sys.exit(main())
