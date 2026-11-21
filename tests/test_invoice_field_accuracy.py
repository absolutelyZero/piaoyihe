# -*- coding: utf-8 -*-
"""发票字段提取准确度自动化测试

两层：
1. `TestGroundTruthIntegrity` —— 基准文件自身的一致性（不依赖语料目录，始终执行）
2. `TestInvoiceFieldAccuracy` —— 对真实语料跑全量提取并与基准比对；语料目录不存在时跳过

语料目录可通过环境变量 `PIAOYIHE_INVOICE_CORPUS` 覆盖。
"""

import hashlib
import json
import os
import sys
import unittest
from collections import Counter

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CODE_DIR = os.path.join(_REPO_ROOT, 'code')
_PYLIBS_DIR = os.path.join(_REPO_ROOT, '.pylibs')
for _path in (_PYLIBS_DIR, _CODE_DIR):
    if os.path.isdir(_path) and _path not in sys.path:
        sys.path.insert(0, _path)

TRUTH_PATH = os.path.join(_REPO_ROOT, 'tests', 'data', 'invoice_field_ground_truth.json')
SUPPORTED_EXT = ('.pdf', '.jpg', '.jpeg', '.png', '.ofd')
CORPUS_DIR = os.environ.get('PIAOYIHE_INVOICE_CORPUS') or r'D:\公司文档\05.培训(公共)\报销'

# 与 scripts/evaluate_invoice_extraction.py 的 BASELINES 保持一致
BASELINES = {
    'invoice_type_key': 0.93,
    'amount': 0.99,
    'tax_amount': 0.99,
    'invoice_date': 0.99,
    'invoice_code': 0.99,
    'buyer_name': 1.0,
    'seller_name': 1.0,
}


def _file_sha256(path, _buf_size=1 << 20):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for chunk in iter(lambda: handle.read(_buf_size), b''):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_paths(truth, corpus_dir):
    """把基准 rel 映射到语料里的实际路径

    语料可能被应用自身的批量重命名改过文件名，因此 rel 失配时按 sha256 内容指纹回退。
    返回 {基准 rel: 实际绝对路径}（找不到的不出现在结果里）。
    """
    resolved = {}
    missing = []
    for rel, case in truth.items():
        path = os.path.join(corpus_dir, rel)
        if os.path.isfile(path):
            resolved[rel] = path
        else:
            missing.append(rel)
    if not missing:
        return resolved

    # 语料里存在字节完全相同的重复票据（同一张票放在不同目录），
    # 因此一个指纹可能对应多个基准行，按发现顺序依次认领。
    wanted = {}
    for rel in missing:
        digest = truth[rel].get('sha256')
        if digest:
            wanted.setdefault(digest, []).append(rel)
    if not wanted:
        return resolved

    known = set(os.path.normcase(path) for path in resolved.values())
    for dirpath, _dirnames, filenames in os.walk(corpus_dir):
        for name in filenames:
            if os.path.splitext(name)[1].lower() not in SUPPORTED_EXT:
                continue
            path = os.path.join(dirpath, name)
            if os.path.normcase(path) in known:
                continue
            try:
                digest = _file_sha256(path)
            except OSError:
                continue
            pending = wanted.get(digest)
            if pending:
                resolved[pending.pop(0)] = path
                if not pending:
                    wanted.pop(digest, None)
            if not wanted:
                return resolved
    return resolved


def load_truth():
    with open(TRUTH_PATH, encoding='utf-8') as handle:
        return json.load(handle)


class TestGroundTruthIntegrity(unittest.TestCase):
    """基准文件的结构与覆盖面自检"""

    @classmethod
    def setUpClass(cls):
        cls.payload = load_truth()
        cls.invoices = cls.payload['invoices']
        cls.by_rel = {row['rel']: row for row in cls.invoices}

    def test_file_count_matches_meta(self):
        self.assertEqual(len(self.invoices), self.payload['_meta']['file_count'])

    def test_every_row_has_expected_block(self):
        for row in self.invoices:
            with self.subTest(file=row['rel']):
                self.assertIn('expected', row)
                self.assertIn(row['evidence'],
                              ('text_fully_parsed', 'not_an_invoice', 'image_no_text_layer'))

    def test_type_coverage_declared(self):
        counts = Counter(row['expected']['invoice_type_key'] for row in self.invoices)
        declared = self.payload['_meta']['coverage']['expected_type_counts']
        for key, declared_value in declared.items():
            key = None if key == 'not_invoice' else key
            self.assertEqual(counts.get(key, 0), declared_value, '票种计数不一致: %s' % key)

    def test_known_types_are_present(self):
        counts = Counter(row['expected']['invoice_type_key'] for row in self.invoices)
        for type_key in ('vat_invoice', 'train_ticket', 'flight_ticket', 'toll_invoice'):
            self.assertGreater(counts[type_key], 0, '语料缺少 %s 样本' % type_key)

    def test_images_are_not_expected_as_invoices(self):
        for row in self.invoices:
            if row['kind'] == 'image':
                with self.subTest(file=row['rel']):
                    self.assertIsNone(row['expected']['invoice_type_key'])

    def test_rows_have_content_fingerprint(self):
        """每行都要有 sha256，语料被重命名后仍能按内容匹配"""
        for row in self.invoices:
            with self.subTest(file=row['rel']):
                digest = row.get('sha256')
                self.assertIsNotNone(digest, '缺少 sha256 内容指纹')
                self.assertEqual(len(digest), 64)
                int(digest, 16)  # 必须是合法十六进制

    def test_multi_invoice_rows_are_flagged(self):
        for row in self.invoices:
            if row['n_invoices'] >= 2:
                with self.subTest(file=row['rel']):
                    self.assertEqual(row['evidence'], 'text_fully_parsed')
                    self.assertIn('合并', row['note'])


@unittest.skipUnless(os.path.isdir(CORPUS_DIR), '语料目录不存在，跳过真实语料评测: %s' % CORPUS_DIR)
class TestInvoiceFieldAccuracy(unittest.TestCase):
    """对真实语料评测票种判定与字段准确率"""

    @classmethod
    def setUpClass(cls):
        from core.pdf_handler import PDFHandler

        cls.truth = {row['rel']: row for row in load_truth()['invoices']}
        cls.paths = resolve_paths(cls.truth, CORPUS_DIR)
        handler = PDFHandler()
        cls.produced = {}
        for rel, path in cls.paths.items():
            try:
                import contextlib
                import io
                with contextlib.redirect_stdout(io.StringIO()):
                    cls.produced[rel] = handler.extract_all_invoice_info(path)
            except Exception as exc:  # 单文件异常不中断
                cls.produced[rel] = None
                print('提取异常 %s: %s: %s' % (rel, type(exc).__name__, exc))

    # -- 工具方法 ---------------------------------------------------------
    def _scored_records(self):
        for rel, case in self.truth.items():
            expected = case['expected']
            if expected['invoice_type_key'] is None:
                continue
            if case['n_invoices'] >= 2:
                continue
            info = self.produced.get(rel)
            if not info:
                continue
            yield rel, expected, info

    @staticmethod
    def _norm(value):
        return ('' if value is None else str(value)).strip().replace(' ', '')

    def _assert_numeric(self, field, got, want, rel):
        self.assertIsNotNone(want, '%s 的基准值为空，基准文件有问题' % rel)
        self.assertIsNotNone(got, '%s 未提取到 %s' % (rel, field))
        self.assertAlmostEqual(float(got), float(want), places=2, msg='%s 的 %s 不符' % (rel, field))

    # -- 用例 -------------------------------------------------------------
    def test_no_missed_invoice(self):
        missed = [rel for rel, case in self.truth.items()
                  if case['expected']['invoice_type_key'] and not self.produced.get(rel)
                  and rel in self.paths]
        self.assertEqual(missed, [], '存在漏检发票: %s' % missed)

    def test_type_accuracy(self):
        total = 0
        matched = 0
        for rel, case in self.truth.items():
            if rel not in self.paths:
                continue
            total += 1
            want = case['expected']['invoice_type_key']
            info = self.produced.get(rel)
            got = (info or {}).get('invoice_type_key')
            matched += (got == want)
        self.assertGreater(total, 0)
        self.assertGreaterEqual(matched / total, BASELINES['invoice_type_key'],
                                '票种判定准确率 %.1f%% 低于基线 %.0f%%'
                                % (matched * 100.0 / total, BASELINES['invoice_type_key'] * 100))

    def test_amount_accuracy(self):
        compared = matched = 0
        for rel, expected, info in self._scored_records():
            if expected['amount'] is None:
                continue
            compared += 1
            got = info.get('amount')
            if got is not None and abs(float(got) - float(expected['amount'])) < 0.005:
                matched += 1
        self.assertGreater(compared, 0)
        self.assertGreaterEqual(matched / compared, BASELINES['amount'], '金额准确率不足')

    def test_tax_amount_accuracy(self):
        compared = matched = 0
        for rel, expected, info in self._scored_records():
            if expected['tax_amount'] is None:
                continue
            compared += 1
            got = info.get('tax_amount')
            if got is not None and abs(float(got) - float(expected['tax_amount'])) < 0.005:
                matched += 1
        self.assertGreater(compared, 0)
        self.assertGreaterEqual(matched / compared, BASELINES['tax_amount'], '税额准确率不足')

    def test_invoice_date_accuracy(self):
        compared = matched = 0
        for rel, expected, info in self._scored_records():
            if not expected['invoice_date']:
                continue
            compared += 1
            matched += (info.get('invoice_date') == expected['invoice_date'])
        self.assertGreater(compared, 0)
        self.assertGreaterEqual(matched / compared, BASELINES['invoice_date'], '开票日期准确率不足')

    def test_invoice_code_accuracy(self):
        compared = matched = 0
        for rel, expected, info in self._scored_records():
            if not expected['invoice_code']:
                continue
            compared += 1
            matched += (self._norm(info.get('invoice_code')) == self._norm(expected['invoice_code']))
        self.assertGreater(compared, 0)
        self.assertGreaterEqual(matched / compared, BASELINES['invoice_code'], '发票号码准确率不足')

    def test_buyer_name_accuracy(self):
        compared = matched = 0
        for rel, expected, info in self._scored_records():
            if not expected['buyer_name']:
                continue
            compared += 1
            matched += (self._norm(info.get('buyer_name')) == self._norm(expected['buyer_name']))
        self.assertGreater(compared, 0)
        self.assertGreaterEqual(matched / compared, BASELINES['buyer_name'], '买方名称准确率不足')

    def test_seller_name_accuracy(self):
        compared = matched = 0
        for rel, expected, info in self._scored_records():
            if not expected['seller_name']:
                continue
            compared += 1
            matched += (self._norm(info.get('seller_name')) == self._norm(expected['seller_name']))
        self.assertGreater(compared, 0)
        self.assertGreaterEqual(matched / compared, BASELINES['seller_name'], '销方名称准确率不足')

    def test_train_ticket_buyer_is_passenger(self):
        """火车票票种设计：buyer_name 取旅客姓名，seller 固定中国铁路"""
        for rel, expected, info in self._scored_records():
            if expected['invoice_type_key'] != 'train_ticket':
                continue
            with self.subTest(file=rel):
                self.assertTrue(info.get('buyer_name'), '火车票未取到旅客姓名')
                self.assertEqual(self._norm(info.get('seller_name')), '中国铁路')

    def test_amount_uses_tax_inclusive_total(self):
        """金额口径：全电发票取「价税合计（小写）」，不是「合 计」行金额"""
        rel = '251101\\住宿.pdf'
        expected = self.truth.get(rel, {}).get('expected', {})
        if rel not in self.paths:
            self.skipTest('样例文件不存在')
        info = self.produced.get(rel) or {}
        self._assert_numeric('amount', info.get('amount'), expected.get('amount'), rel)
        self.assertGreater(float(info.get('amount')), 0)

    def test_flight_and_toll_seller_never_empty(self):
        """机票/通行费（旧版竖排标签版式）的销售方名称必须能取到"""
        broken = []
        for rel, expected, info in self._scored_records():
            if expected['invoice_type_key'] not in ('flight_ticket', 'toll_invoice'):
                continue
            if not info.get('seller_name'):
                broken.append(rel)
        self.assertEqual(broken, [], '机票/通行费 seller 为空: %s' % broken)

    def test_flight_and_toll_buyer_never_empty(self):
        """机票/通行费（旧版竖排标签版式）的购买方名称必须能取到"""
        broken = []
        for rel, expected, info in self._scored_records():
            if expected['invoice_type_key'] not in ('flight_ticket', 'toll_invoice'):
                continue
            if not info.get('buyer_name'):
                broken.append(rel)
        self.assertEqual(broken, [], '机票/通行费 buyer 为空: %s' % broken)


class TestRenamedCorpusFallback(unittest.TestCase):
    """语料被重命名后，基准行应能按 sha256 内容指纹重新定位（不依赖真实语料）"""

    def setUp(self):
        import shutil
        import tempfile

        from tests._env_patch import SafeTemporaryDirectory

        self.root = SafeTemporaryDirectory(prefix='piaoyihe_rename_')
        self.addCleanup(shutil.rmtree, self.root.name, True)
        self.dir = self.root.name
        self.content = b'%PDF-1.4 fake invoice bytes'

    def _write(self, rel, payload=None):
        path = os.path.join(self.dir, rel)
        parent = os.path.dirname(path)
        if parent and not os.path.isdir(parent):
            os.makedirs(parent)
        with open(path, 'wb') as handle:
            handle.write(self.content if payload is None else payload)
        return path

    def test_rel_hit_needs_no_hashing(self):
        path = self._write('a.pdf')
        truth = {'a.pdf': {'sha256': _file_sha256(path)}}
        self.assertEqual(resolve_paths(truth, self.dir), {'a.pdf': path})

    def test_renamed_file_is_matched_by_content(self):
        path = self._write('新名字.pdf')
        digest = _file_sha256(path)
        truth = {'旧名字.pdf': {'sha256': digest}}
        self.assertEqual(resolve_paths(truth, self.dir), {'旧名字.pdf': path})

    def test_unmatched_digest_stays_unresolved(self):
        self._write('a.pdf')
        truth = {'旧名字.pdf': {'sha256': '0' * 64}}
        self.assertEqual(resolve_paths(truth, self.dir), {})

    def test_duplicate_content_claims_each_row_once(self):
        """字节相同的重复票据：同一指纹被多个基准行引用时，各认领一个文件"""
        first = self._write('周期性报销/副本.pdf')
        second = self._write('251201/正本.pdf')
        digest = _file_sha256(first)
        self.assertEqual(digest, _file_sha256(second), '前置条件：两文件内容必须相同')
        truth = {'旧名A.pdf': {'sha256': digest}, '旧名B.pdf': {'sha256': digest}}
        resolved = resolve_paths(truth, self.dir)
        self.assertEqual(set(resolved), {'旧名A.pdf', '旧名B.pdf'})
        self.assertEqual(sorted(os.path.normcase(os.path.normpath(x)) for x in resolved.values()),
                         sorted(os.path.normcase(os.path.normpath(x)) for x in (first, second)))

    def test_rows_without_sha256_are_not_guessed(self):
        self._write('a.pdf')
        truth = {'旧名字.pdf': {}}
        self.assertEqual(resolve_paths(truth, self.dir), {})


class TestEvaluatorRenameFallback(unittest.TestCase):
    """评测脚本里的 resolve_renamed 也要能在语料改名后把提取结果搬回基准 rel"""

    @classmethod
    def setUpClass(cls):
        import importlib.util

        path = os.path.join(_REPO_ROOT, 'scripts', 'evaluate_invoice_extraction.py')
        spec = importlib.util.spec_from_file_location('evaluate_invoice_extraction', path)
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    def setUp(self):
        from tests._env_patch import SafeTemporaryDirectory

        self.root = SafeTemporaryDirectory(prefix='piaoyihe_eval_')
        self.addCleanup(__import__('shutil').rmtree, self.root.name, True)
        self.dir = self.root.name
        self.payload = b'%PDF-1.4 fake invoice bytes'

    def _write(self, rel, payload=None):
        path = os.path.join(self.dir, rel)
        parent = os.path.dirname(path)
        if parent and not os.path.isdir(parent):
            os.makedirs(parent)
        with open(path, 'wb') as handle:
            handle.write(self.payload if payload is None else payload)
        return path

    def test_result_moves_to_truth_rel(self):
        path = self._write('新名字.pdf')
        digest = self.module._file_sha256(path)
        truth = {'旧名字.pdf': {'sha256': digest}}
        produced = {'新名字.pdf': {'amount': 1.0}}
        resolved = self.module.resolve_renamed(truth, produced, self.dir)
        self.assertEqual(dict(resolved), {'旧名字.pdf': '新名字.pdf'})
        self.assertEqual(produced, {'旧名字.pdf': {'amount': 1.0}})

    def test_duplicate_content_moves_each_result_once(self):
        """字节相同的重复票据：同一指纹对应多个基准行时，逐行搬移结果"""
        first = self._write('周期性报销/副本.pdf')
        second = self._write('251201/正本.pdf')
        digest = self.module._file_sha256(first)
        self.assertEqual(digest, self.module._file_sha256(second), '前置条件：两文件内容必须相同')
        truth = {'旧名A.pdf': {'sha256': digest}, '旧名B.pdf': {'sha256': digest}}
        produced = {'周期性报销/副本.pdf': {'amount': 1.0}, '251201/正本.pdf': {'amount': 2.0}}
        resolved = self.module.resolve_renamed(truth, produced, self.dir)
        self.assertEqual(set(resolved), {'旧名A.pdf', '旧名B.pdf'})
        self.assertEqual(sorted(produced), ['旧名A.pdf', '旧名B.pdf'])
        self.assertEqual(sorted(v['amount'] for v in produced.values()), [1.0, 2.0])

    def test_noop_when_every_row_already_matched(self):
        path = self._write('a.pdf')
        truth = {'a.pdf': {'sha256': self.module._file_sha256(path)}}
        produced = {'a.pdf': {'amount': 1.0}}
        self.assertEqual(dict(self.module.resolve_renamed(truth, produced, self.dir)), {})
        self.assertEqual(produced, {'a.pdf': {'amount': 1.0}})

    def test_noop_when_digest_does_not_match(self):
        self._write('a.pdf')
        truth = {'旧名字.pdf': {'sha256': '0' * 64}}
        produced = {'a.pdf': {'amount': 1.0}}
        self.assertEqual(dict(self.module.resolve_renamed(truth, produced, self.dir)), {})
        self.assertEqual(produced, {'a.pdf': {'amount': 1.0}})


class TestFieldConventionOnSyntheticText(unittest.TestCase):
    """用纯文本断言字段口径，不依赖 PDF 文件"""

    def _make(self, extractor_cls, text):
        instance = extractor_cls.__new__(extractor_cls)
        instance._text = text
        instance._pages = []
        return instance

    def test_train_ticket_amount_prefers_piaojia(self):
        from core.invoice_extractors.train_ticket import TrainTicketExtractor

        text = ('电子发票（铁路电子客票）\n'
                '发票号码:25329116804008094049\n'
                '2025年12月18日\n'
                'G7613\n'
                '票价:￥117.00\n'
                '3302811989****0430 谢永高\n'
                '开票日期:2025年12月19日\n'
                '杭州东站\n南京南站\n')
        instance = self._make(TrainTicketExtractor, text)
        self.assertAlmostEqual(instance.extract_amount(), 117.0, places=2)
        self.assertEqual(instance.extract_buyer_name(), '谢永高')
        self.assertEqual(instance.extract_invoice_type(), '火车票')

    def test_train_ticket_code_is_20_digits(self):
        from core.invoice_extractors.train_ticket import TrainTicketExtractor

        text = '电子发票（铁路电子客票）\n发票号码:25329116804008094049\n票价:￥117.00\n'
        instance = self._make(TrainTicketExtractor, text)
        self.assertEqual(instance.extract_invoice_code(), '25329116804008094049')

    def test_common_invoice_amount_uses_tax_inclusive(self):
        from core.invoice_extractors.common_invoice import CommonInvoiceExtractor

        text = ('电子发票（普通发票）\n'
                '发票号码:25322000000478324886\n'
                '开票日期:2025年10月16日\n'
                '合 计 ¥213.84 ¥2.14\n'
                '价税合计（大写）贰佰壹拾伍圆玖角捌分（小写）¥215.98\n')
        instance = self._make(CommonInvoiceExtractor, text)
        self.assertAlmostEqual(instance.extract_amount(), 215.98, places=2)
        self.assertAlmostEqual(instance.extract_tax_amount(), 2.14, places=2)

    def test_can_handle_is_keyword_only(self):
        """记录当前 can_handle 的纯关键词实现（缺陷 6.4 的回归锚点）"""
        from core.invoice_extractors.train_ticket import TrainTicketExtractor

        self.assertTrue(TrainTicketExtractor.can_handle('员工手册 1.2 火车票：个人自行购买'))
        self.assertFalse(TrainTicketExtractor.can_handle('电子发票（普通发票）住宿服务'))


class TestFlightAndTollLayouts(unittest.TestCase):
    """机票/通行费的三类票面版式必须能取到买卖方名称（P0/P1 修复的回归锚点）"""

    def _make(self, extractor_cls, text):
        instance = extractor_cls.__new__(extractor_cls)
        instance._text = text
        instance._pages = []
        return instance

    def test_flight_einvoice_name_before_label(self):
        """新版全电：名称行在「名称:」之前，买卖方标签纵向单字拆行"""
        from core.invoice_extractors.flight_ticket import FlightTicketExtractor

        text = ('电子发票(普通发票)\n'
                '发票号码: 24327000000520465870\n'
                '开票日期: 2024年12月27日\n'
                '购\n买\n方\n信\n息\n'
                '浙江贵仁信息科技股份有限公司\n'
                '名称:\n'
                '统一社会信用代码/纳税人识别号:91330100691720890E\n'
                '销\n售\n方\n信\n息\n'
                '苏州程会玩国际旅行社有限公司\n'
                '名称:\n'
                '统一社会信用代码/纳税人识别号:91320594MA1MBK0R43\n'
                '乘机人:谢永高;航班:杭州萧山-哈尔滨太平;航班号:3U3157\n')
        instance = self._make(FlightTicketExtractor, text)
        self.assertEqual(instance.extract_buyer_name(), '浙江贵仁信息科技股份有限公司')
        self.assertEqual(instance.extract_seller_name(), '苏州程会玩国际旅行社有限公司')

    def test_flight_einvoice_labels_then_values(self):
        """新版全电：标签成组在头、公司名成组在尾（无「购买方信息」连串）"""
        from core.invoice_extractors.flight_ticket import FlightTicketExtractor

        text = ('电子发票（普通发票）\n'
                '发票号码：\n开票日期：\n'
                '名称：\n统一社会信用代码/纳税人识别号：\n'
                '名称：\n统一社会信用代码/纳税人识别号：\n'
                '乘机人：谢永高\n'
                '25117000000047444547\n2025年01月09日\n'
                '浙江贵仁信息科技股份有限公司\n91330100691720890E\n'
                '北京我遥我控科技有限公司\n91110116055565228Q\n')
        instance = self._make(FlightTicketExtractor, text)
        self.assertEqual(instance.extract_buyer_name(), '浙江贵仁信息科技股份有限公司')
        self.assertEqual(instance.extract_seller_name(), '北京我遥我控科技有限公司')

    def test_flight_old_layout_never_returns_chapter_seal(self):
        """旧版增值税电子普通发票：值区公司名顺序推断，不得取到「（章）」"""
        from core.invoice_extractors.flight_ticket import FlightTicketExtractor

        text = ('北京增值税电子普通发票\n'
                '购\n买\n方\n名\n称：\n销\n售\n方\n名\n称：\n'
                '销售方：（章）\n'
                '011002301511\n45517653\n2023年12月11日\n'
                '浙江贵仁信息科技股份有限公司\n91330100691720890E\n'
                '中国银行杭州物联网产业园支行 397470608312\n'
                '北京我遥我控科技有限公司\n91110116055565228Q\n'
                '招商银行股份有限公司北京东三环支行110910951210308\n')
        instance = self._make(FlightTicketExtractor, text)
        self.assertEqual(instance.extract_buyer_name(), '浙江贵仁信息科技股份有限公司')
        self.assertEqual(instance.extract_seller_name(), '北京我遥我控科技有限公司')

    def test_toll_old_layout_buyer_seller_and_entry_exit(self):
        """旧版通行费发票：12 位代码+8 位号码、站点「A站入 B站出」逐项解析"""
        from core.invoice_extractors.toll_invoice import TollInvoiceExtractor

        text = ('黑龙江增值税电子普通发票\n'
                '销 售 方:（章）\n'
                '499098461547\n叁拾圆整\n'
                '浙江贵仁信息科技股份有限公司\n91330100691720890E\n'
                '哈尔滨市城投投资控股有限公司机场专用路分公司\n91230102MA1BEBY954\n'
                '023002300111\n02621811\n2024年12月26日\n'
                '黑A14T6T 哈尔滨机场站入 哈尔滨机场出 2024-12-26 06:53:46\n')
        instance = self._make(TollInvoiceExtractor, text)
        self.assertEqual(instance.extract_buyer_name(), '浙江贵仁信息科技股份有限公司')
        self.assertEqual(instance.extract_seller_name(),
                         '哈尔滨市城投投资控股有限公司机场专用路分公司')
        extras = instance.extract_extra_fields()
        self.assertEqual(extras.get('toll_entry'), '哈尔滨机场站')
        self.assertEqual(extras.get('toll_exit'), '哈尔滨机场')

    def test_toll_old_layout_code_from_12_plus_8(self):
        """旧版通行费：12 位发票代码 + 8 位发票号码拼成 20 位"""
        from core.invoice_extractors.toll_invoice import TollInvoiceExtractor

        text = ('吉林增值税电子普通发票\n499098461547\n玖圆整\n'
                '022002400111\n01650115\n2025年01月19日\n'
                '吉林龙嘉机场收费站入 吉林长春东收费站出 2025-01-19 13:38:13\n')
        instance = self._make(TollInvoiceExtractor, text)
        self.assertEqual(instance.extract_invoice_code(), '02200240011101650115')
        extras = instance.extract_extra_fields()
        self.assertEqual(extras.get('toll_entry'), '吉林龙嘉机场收费站')
        self.assertEqual(extras.get('toll_exit'), '吉林长春东收费站')


if __name__ == '__main__':
    unittest.main(verbosity=2)
