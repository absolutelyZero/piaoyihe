#!/usr/bin/env python3
"""
按票种重命名规则单元测试

覆盖：旧配置迁移、规则规整、apply_rule 占位符行为、
batch_rename 按票种选规则与未配置跳过。
不依赖真实 PDF（Mock PDFHandler）。
"""

import os
import sys
import shutil
import uuid
import unittest
import contextlib
from unittest.mock import Mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'code'))


@contextlib.contextmanager
def temp_dir():
    """
    可写的临时目录上下文管理器

    不使用 tempfile.TemporaryDirectory：其在部分沙箱环境下创建的目录
    会带受限权限而无法写入子文件。改用 os.makedirs + uuid 命名，
    并在退出时尽力清理。
    """
    base = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.testtmp')
    os.makedirs(base, exist_ok=True)
    path = os.path.join(base, 'case_' + uuid.uuid4().hex[:10])
    os.makedirs(path, exist_ok=True)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)

from core.invoice_service import (
    InvoiceService,
    migrate_rename_rules,
    normalize_rename_rules,
)
from core.invoice_field_registry import INVOICE_TYPE_KEYS


def info(type_key, **overrides):
    """构造一份提取结果"""
    base = {
        'invoice_type_key': type_key,
        'invoice_type': '普票',
        'invoice_date': '2024-01-01',
        'amount': 100.0,
        'invoice_code': '001',
        'buyer_name': 'A公司',
        'seller_name': 'B公司',
        'product_type': '办公用品',
    }
    base.update(overrides)
    return base


class TestMigrateRenameRules(unittest.TestCase):
    """旧配置迁移"""

    def test_migrate_from_legacy(self):
        """有旧规则、无新结构 -> 迁移到全部票种"""
        config = {'rename_rule': '{金额}-{发票类型}'}
        self.assertTrue(migrate_rename_rules(config))
        self.assertIn('rename_rules', config)
        self.assertEqual(set(config['rename_rules']), set(INVOICE_TYPE_KEYS))
        for key in INVOICE_TYPE_KEYS:
            self.assertEqual(config['rename_rules'][key], '{金额}-{发票类型}')
        # 旧键保留
        self.assertEqual(config['rename_rule'], '{金额}-{发票类型}')

    def test_no_overwrite_existing(self):
        """已有 rename_rules -> 不覆盖"""
        config = {
            'rename_rule': '{旧规则}',
            'rename_rules': {'vat_invoice': '{新规则}'},
        }
        self.assertFalse(migrate_rename_rules(config))
        self.assertEqual(config['rename_rules'], {'vat_invoice': '{新规则}'})

    def test_no_legacy_no_rules(self):
        """两者皆无 -> 不生成空规则，返回 False"""
        config = {}
        self.assertFalse(migrate_rename_rules(config))
        self.assertNotIn('rename_rules', config)

    def test_blank_legacy_not_migrated(self):
        """旧规则为空白 -> 不迁移"""
        config = {'rename_rule': '   '}
        self.assertFalse(migrate_rename_rules(config))
        self.assertNotIn('rename_rules', config)

    def test_non_dict_rename_rules_is_migrated(self):
        """rename_rules 存在但不是字典 -> 视为无效，允许迁移"""
        config = {'rename_rule': '{R}', 'rename_rules': 'garbage'}
        self.assertTrue(migrate_rename_rules(config))
        self.assertEqual(config['rename_rules']['vat_invoice'], '{R}')

    def test_non_dict_config(self):
        """config 不是字典 -> 安全返回 False"""
        self.assertFalse(migrate_rename_rules(None))
        self.assertFalse(migrate_rename_rules('x'))


class TestNormalizeRenameRules(unittest.TestCase):
    """规则集合规整"""

    def test_all_keys_present(self):
        """结果总是含全部 7 个票种键"""
        result = normalize_rename_rules({'vat_invoice': 'a'})
        self.assertEqual(set(result), set(INVOICE_TYPE_KEYS))
        self.assertEqual(result['vat_invoice'], 'a')
        self.assertEqual(result['train_ticket'], '')

    def test_drops_illegal_keys(self):
        """丢弃非法票种键"""
        result = normalize_rename_rules({'illegal': 'x', 'vat_invoice': 'a'})
        self.assertNotIn('illegal', result)

    def test_non_string_values_become_empty(self):
        """非字符串值规整为空串"""
        result = normalize_rename_rules({'vat_invoice': 123})
        self.assertEqual(result['vat_invoice'], '')

    def test_none_input(self):
        """None 输入 -> 全空规则"""
        result = normalize_rename_rules(None)
        self.assertEqual(set(result), set(INVOICE_TYPE_KEYS))
        self.assertTrue(all(v == '' for v in result.values()))


class TestApplyRule(unittest.TestCase):
    """apply_rule 行为"""

    def test_empty_rule_returns_none(self):
        """空规则返回 None"""
        self.assertIsNone(InvoiceService.apply_rule('', {}))
        self.assertIsNone(InvoiceService.apply_rule(None, {}))

    def test_basic_replacement(self):
        """基本占位符替换"""
        result = InvoiceService.apply_rule(
            '{发票类型}-{开票日期}', info('vat_invoice')
        )
        self.assertEqual(result, '普票-2024-01-01')

    def test_missing_field_keeps_placeholder(self):
        """空值字段保留占位符原文"""
        result = InvoiceService.apply_rule(
            '{发票类型}-{商品类型}',
            {'invoice_type': '普票', 'product_type': ''},
            type_key='vat_invoice'
        )
        self.assertEqual(result, '普票-{商品类型}')

    def test_none_field_keeps_placeholder(self):
        """None 值保留占位符原文"""
        result = InvoiceService.apply_rule(
            '{发票类型}-{商品类型}',
            {'invoice_type': '普票', 'product_type': None},
        )
        self.assertEqual(result, '普票-{商品类型}')

    def test_zero_amount_replaced(self):
        """金额 0 是有效值，按数值格式替换"""
        result = InvoiceService.apply_rule('{金额}', {'amount': 0})
        self.assertEqual(result, '0.00')

    def test_amount_two_decimals(self):
        """金额两位小数"""
        self.assertEqual(
            InvoiceService.apply_rule('{金额}', {'amount': 100.5}), '100.50'
        )
        self.assertEqual(
            InvoiceService.apply_rule('{金额}', {'amount': 92168.52}), '92168.52'
        )

    def test_type_specific_field(self):
        """票种特有字段可替换"""
        result = InvoiceService.apply_rule(
            '{车次}-{出发站}',
            {'train_number': 'G636', 'departure_station': '河源东站'},
            type_key='train_ticket'
        )
        self.assertEqual(result, 'G636-河源东站')

    def test_cross_type_field_fallback(self):
        """规则里用了该票种字段集之外的占位符，仍能兜底替换"""
        result = InvoiceService.apply_rule(
            '{车牌号}', {'plate_number': '粤B12345'}, type_key='vat_invoice'
        )
        self.assertEqual(result, '粤B12345')

    def test_sanitizes_invalid_chars(self):
        """非法字符被清理"""
        result = InvoiceService.apply_rule('{买方名字}', {'buyer_name': 'A/B:C'})
        self.assertEqual(result, 'A_B_C')


class TestBatchRenameByType(unittest.TestCase):
    """batch_rename 按票种选规则"""

    def _make_files(self, tmpdir, names):
        paths = []
        for name in names:
            p = os.path.join(tmpdir, name)
            with open(p, 'w') as f:
                pass
            paths.append(p)
        return paths

    def test_mixed_types_use_own_rules(self):
        """混合票种各用各的规则"""
        with temp_dir() as tmpdir:
            paths = self._make_files(tmpdir, ['a.pdf', 'b.pdf'])
            handler = Mock()
            handler.extract_all_invoice_info = Mock(side_effect=[
                info('vat_invoice', invoice_type='普票', invoice_date='2024-01-01'),
                info('train_ticket', invoice_type='火车票', invoice_date='2024-02-02'),
            ])
            service = InvoiceService(handler)
            rules = {
                'vat_invoice': '{发票类型}-{开票日期}',
                'train_ticket': '{发票类型}_{开票日期}',
            }
            result = service.batch_rename(paths, rules)

            self.assertEqual(result['renamed_count'], 2)
            self.assertTrue(os.path.exists(os.path.join(tmpdir, '普票-2024-01-01.pdf')))
            self.assertTrue(os.path.exists(os.path.join(tmpdir, '火车票_2024-02-02.pdf')))

    def test_unconfigured_type_skipped(self):
        """未配置规则的票种跳过并计数"""
        with temp_dir() as tmpdir:
            paths = self._make_files(tmpdir, ['a.pdf', 'b.pdf'])
            handler = Mock()
            handler.extract_all_invoice_info = Mock(side_effect=[
                info('vat_invoice'),
                info('fixed_amount_invoice', invoice_type='定额发票'),
            ])
            service = InvoiceService(handler)
            rules = {'vat_invoice': '{发票类型}'}
            result = service.batch_rename(paths, rules)

            self.assertEqual(result['renamed_count'], 1)
            self.assertEqual(result['skipped_unconfigured_count'], 1)
            # 定额发票保持原名
            self.assertTrue(os.path.exists(os.path.join(tmpdir, 'b.pdf')))

    def test_all_types_unconfigured(self):
        """全部票种未配置 -> 一个都不改名"""
        with temp_dir() as tmpdir:
            paths = self._make_files(tmpdir, ['a.pdf'])
            handler = Mock()
            handler.extract_all_invoice_info = Mock(return_value=info('vat_invoice'))
            service = InvoiceService(handler)
            result = service.batch_rename(paths, {})

            self.assertEqual(result['renamed_count'], 0)
            self.assertEqual(result['skipped_unconfigured_count'], 1)
            self.assertTrue(os.path.exists(os.path.join(tmpdir, 'a.pdf')))

    def test_missing_type_key_treated_as_unconfigured(self):
        """info 缺 invoice_type_key -> 按未配置处理，不抛异常"""
        with temp_dir() as tmpdir:
            paths = self._make_files(tmpdir, ['a.pdf'])
            handler = Mock()
            handler.extract_all_invoice_info = Mock(return_value={
                'invoice_type': '普票', 'amount': 1.0,
            })
            service = InvoiceService(handler)
            result = service.batch_rename(paths, {'vat_invoice': '{发票类型}'})

            self.assertEqual(result['renamed_count'], 0)
            self.assertEqual(result['skipped_unconfigured_count'], 1)
            self.assertEqual(result['failed_count'], 0)

    def test_dry_run_no_change(self):
        """dry_run 不落盘"""
        with temp_dir() as tmpdir:
            paths = self._make_files(tmpdir, ['a.pdf', 'b.pdf'])
            handler = Mock()
            handler.extract_all_invoice_info = Mock(return_value=info('vat_invoice'))
            service = InvoiceService(handler)
            result = service.batch_rename(
                paths, {'vat_invoice': '{发票类型}'}, dry_run=True
            )

            self.assertEqual(result['renamed_count'], 2)
            self.assertTrue(os.path.exists(os.path.join(tmpdir, 'a.pdf')))
            self.assertTrue(os.path.exists(os.path.join(tmpdir, 'b.pdf')))

    def test_conflict_suffix(self):
        """同名冲突仍产生 (1) 后缀"""
        with temp_dir() as tmpdir:
            paths = self._make_files(tmpdir, ['a.pdf', 'b.pdf'])
            handler = Mock()
            handler.extract_all_invoice_info = Mock(return_value=info('vat_invoice'))
            service = InvoiceService(handler)
            result = service.batch_rename(paths, {'vat_invoice': '{发票类型}'})

            self.assertEqual(result['renamed_count'], 2)
            self.assertTrue(os.path.exists(os.path.join(tmpdir, '普票.pdf')))
            self.assertTrue(os.path.exists(os.path.join(tmpdir, '普票(1).pdf')))

    def test_result_keys_complete(self):
        """返回值包含全部统计键"""
        with temp_dir() as tmpdir:
            paths = self._make_files(tmpdir, ['a.pdf'])
            handler = Mock()
            handler.extract_all_invoice_info = Mock(return_value=info('vat_invoice'))
            service = InvoiceService(handler)
            result = service.batch_rename(paths, {'vat_invoice': '{发票类型}'})

            for key in ('renamed_count', 'failed_count', 'unrecognized_files',
                        'skipped_image_count', 'skipped_ofd_count',
                        'skipped_unconfigured_count', 'renamed_map'):
                self.assertIn(key, result)

    def test_progress_called(self):
        """进度回调被调用 total 次"""
        with temp_dir() as tmpdir:
            paths = self._make_files(tmpdir, ['a.pdf', 'b.pdf', 'c.pdf'])
            handler = Mock()
            handler.extract_all_invoice_info = Mock(return_value=info('vat_invoice'))
            service = InvoiceService(handler)
            calls = []
            service.batch_rename(
                paths, {'vat_invoice': '{发票类型}'},
                on_progress=lambda c, t: calls.append((c, t))
            )
            self.assertEqual(len(calls), 3)
            self.assertEqual(calls[-1], (3, 3))


class TestGetAvailableFields(unittest.TestCase):
    """字段查询按票种分组"""

    def test_returns_types_grouping(self):
        """返回 types 分组，长度 7"""
        result = InvoiceService.get_available_fields()
        self.assertIn('types', result)
        self.assertEqual(len(result['types']), 7)

    def test_each_type_has_key_label_fields(self):
        """每个分组含 key/label/fields"""
        for item in InvoiceService.get_available_fields()['types']:
            self.assertIn('key', item)
            self.assertIn('label', item)
            self.assertIn('fields', item)
            self.assertTrue(item['fields'])
            for f in item['fields']:
                self.assertIn('display', f)
                self.assertIn('key', f)

    def test_flat_fields_compatible(self):
        """扁平 fields 仍含 amount（兼容既有调用方）"""
        flat = InvoiceService.get_available_fields()['fields']
        self.assertTrue(any(f['key'] == 'amount' for f in flat))

    def test_type_fields_match_registry(self):
        """各分组 fields 与注册表一致"""
        from core.invoice_field_registry import get_fields
        result = InvoiceService.get_available_fields()
        for item in result['types']:
            expected = [(d, k) for d, k in get_fields(item['key'])]
            actual = [(f['display'], f['key']) for f in item['fields']]
            self.assertEqual(actual, expected)


if __name__ == '__main__':
    unittest.main()
