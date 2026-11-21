#!/usr/bin/env python3
"""
发票票种与字段注册表单元测试

覆盖：
- 7 个票种标识齐全、标签完整
- 各票种字段集符合 design.md 决策 2 的划分
- 默认模板的占位符只引用该票种字段集内的字段
- 实测基线文件自洽性
"""

import json
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'code'))

from core.invoice_field_registry import (
    ALL_FIELD_KEYS,
    DEFAULT_RULE_TEMPLATES,
    INVOICE_TYPE_KEYS,
    INVOICE_TYPE_LABELS,
    TYPE_FIELD_SPECS,
    get_default_template,
    get_fields,
    get_type_label,
    resolve_field_key,
)

_SRC_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_SRC_DIR)
_BASELINE_PATH = os.path.join(
    _PROJECT_ROOT, 'openspec', 'changes', 'archive',
    '2026-11-12-per-invoice-type-rename-rules', 'baseline', 'expected-fields.json'
)

_COMMON_DISPLAYS = {'发票类型', '开票日期', '发票号码', '金额'}


class TestInvoiceTypeKeys(unittest.TestCase):
    """票种标识与标签"""

    def test_seven_type_keys(self):
        """恰好 7 个票种标识且顺序固定"""
        self.assertEqual(len(INVOICE_TYPE_KEYS), 7)
        self.assertEqual(INVOICE_TYPE_KEYS, [
            'vat_invoice',
            'train_ticket',
            'flight_ticket',
            'vehicle_invoice',
            'taxi_invoice',
            'fixed_amount_invoice',
            'toll_invoice',
        ])

    def test_every_key_has_label(self):
        """每个票种都有中文标签"""
        for key in INVOICE_TYPE_KEYS:
            self.assertIn(key, INVOICE_TYPE_LABELS)
            self.assertTrue(INVOICE_TYPE_LABELS[key])

    def test_get_type_label_unknown(self):
        """未知票种原样返回标识"""
        self.assertEqual(get_type_label('nope'), 'nope')
        self.assertEqual(get_type_label('vat_invoice'), '增值税发票')


class TestFieldSpecs(unittest.TestCase):
    """字段集划分"""

    def test_all_types_have_specs(self):
        """每个票种都定义了字段集"""
        for key in INVOICE_TYPE_KEYS:
            self.assertIn(key, TYPE_FIELD_SPECS)
            self.assertTrue(TYPE_FIELD_SPECS[key])

    def test_common_fields_everywhere(self):
        """7 个票种均含发票类型/开票日期/发票号码/金额"""
        for key in INVOICE_TYPE_KEYS:
            displays = {d for d, _ in TYPE_FIELD_SPECS[key]}
            self.assertTrue(
                _COMMON_DISPLAYS.issubset(displays),
                f'{key} 缺少通用字段: {_COMMON_DISPLAYS - displays}'
            )

    def test_train_ticket_has_no_product_type(self):
        """火车票字段集不含商品类型"""
        displays = {d for d, _ in TYPE_FIELD_SPECS['train_ticket']}
        self.assertNotIn('商品类型', displays)

    def test_fixed_amount_only_common(self):
        """定额发票字段集恰好为通用四项"""
        displays = [d for d, _ in TYPE_FIELD_SPECS['fixed_amount_invoice']]
        self.assertEqual(set(displays), _COMMON_DISPLAYS)
        self.assertEqual(len(displays), 4)

    def test_extra_fields_present(self):
        """各票种特有字段按 design 决策 2 落位"""
        cases = {
            'train_ticket': {'车次', '出发站', '到达站'},
            'flight_ticket': {'航班号', '航空公司'},
            'vehicle_invoice': {'车架号'},
            'taxi_invoice': {'车牌号'},
            'toll_invoice': {'入口', '出口', '路段'},
        }
        for key, expected in cases.items():
            displays = {d for d, _ in TYPE_FIELD_SPECS[key]}
            self.assertTrue(
                expected.issubset(displays),
                f'{key} 缺少特有字段: {expected - displays}'
            )

    def test_vehicle_keeps_product_type(self):
        """机动车发票保留车辆类型/品牌（商品类型）可用性"""
        displays = {d for d, _ in TYPE_FIELD_SPECS['vehicle_invoice']}
        self.assertIn('商品类型', displays)

    def test_no_duplicate_field_keys_within_type(self):
        """同一票种内字段键不重复"""
        for key in INVOICE_TYPE_KEYS:
            keys = [k for _, k in TYPE_FIELD_SPECS[key]]
            self.assertEqual(len(keys), len(set(keys)), f'{key} 字段键重复')

    def test_all_spec_keys_in_all_field_keys(self):
        """每个票种的字段键都落在 ALL_FIELD_KEYS 内"""
        for key in INVOICE_TYPE_KEYS:
            for _display, field_key in TYPE_FIELD_SPECS[key]:
                self.assertIn(field_key, ALL_FIELD_KEYS)

    def test_all_field_keys_is_union(self):
        """ALL_FIELD_KEYS 恰好是所有票种字段键的并集"""
        union = set()
        for key in INVOICE_TYPE_KEYS:
            union.update(k for _, k in TYPE_FIELD_SPECS[key])
        self.assertEqual(set(ALL_FIELD_KEYS), union)
        self.assertEqual(len(ALL_FIELD_KEYS), len(union))


class TestHelpers(unittest.TestCase):
    """辅助函数"""

    def test_get_fields_known_type(self):
        """已知票种返回其字段集"""
        fields = get_fields('train_ticket')
        displays = [d for d, _ in fields]
        self.assertIn('车次', displays)

    def test_get_fields_returns_copy(self):
        """返回的是副本，外部修改不影响注册表"""
        fields = get_fields('vat_invoice')
        fields.append(('伪造', 'fake'))
        self.assertNotIn('伪造', [d for d, _ in get_fields('vat_invoice')])

    def test_get_fields_unknown_falls_back_to_all(self):
        """未知票种/None 时退回全部字段"""
        for arg in (None, 'unknown_type'):
            fields = get_fields(arg)
            self.assertEqual({k for _, k in fields}, set(ALL_FIELD_KEYS))

    def test_resolve_field_key(self):
        """全部显示名可反查为字段键"""
        self.assertEqual(resolve_field_key('开票日期'), 'invoice_date')
        self.assertEqual(resolve_field_key('金额'), 'amount')
        self.assertEqual(resolve_field_key('车次'), 'train_number')
        self.assertEqual(resolve_field_key('车牌号'), 'plate_number')
        self.assertIsNone(resolve_field_key('不存在的字段'))

    def test_resolve_every_display_name(self):
        """注册表中所有显示名都能反查"""
        for key in INVOICE_TYPE_KEYS:
            for display, field_key in TYPE_FIELD_SPECS[key]:
                self.assertEqual(resolve_field_key(display), field_key)


class TestDefaultTemplates(unittest.TestCase):
    """默认模板"""

    def test_every_type_has_template(self):
        """7 个票种均有默认模板"""
        for key in INVOICE_TYPE_KEYS:
            self.assertIn(key, DEFAULT_RULE_TEMPLATES)
            self.assertTrue(get_default_template(key))

    def test_get_default_template_unknown(self):
        """未知票种返回空字符串"""
        self.assertEqual(get_default_template('nope'), '')

    def test_template_placeholders_within_field_set(self):
        """每条模板的占位符都落在该票种字段集内"""
        for key in INVOICE_TYPE_KEYS:
            allowed = {d for d, _ in TYPE_FIELD_SPECS[key]}
            used = set(re.findall(r'\{([^}]+)\}', DEFAULT_RULE_TEMPLATES[key]))
            self.assertTrue(
                used.issubset(allowed),
                f'{key} 模板引用了该票种没有的字段: {used - allowed}'
            )

    def test_all_placeholders_resolvable(self):
        """所有模板的占位符都能反查到字段键"""
        for key in INVOICE_TYPE_KEYS:
            for name in re.findall(r'\{([^}]+)\}', DEFAULT_RULE_TEMPLATES[key]):
                self.assertIsNotNone(
                    resolve_field_key(name), f'{key} 模板占位符 {name} 无法解析'
                )


class TestBaselineConsistency(unittest.TestCase):
    """实测基线文件自洽性"""

    def setUp(self):
        if not os.path.exists(_BASELINE_PATH):
            self.skipTest(f'基线文件不存在（正常应随变更提交）: {_BASELINE_PATH}')

    def _load(self):
        with open(_BASELINE_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)

    def test_baseline_parsable(self):
        """基线可被 json.load 解析且含 invoices 列表"""
        data = self._load()
        self.assertIn('invoices', data)
        self.assertIsInstance(data['invoices'], list)
        self.assertTrue(data['invoices'])

    def test_type_keys_valid(self):
        """每个条目的 invoice_type_key 都在 INVOICE_TYPE_KEYS 内"""
        data = self._load()
        for item in data['invoices']:
            expected = item.get('expected')
            if not expected:
                continue
            key = expected.get('invoice_type_key')
            self.assertIn(
                key, INVOICE_TYPE_KEYS,
                f'{item.get("file")} 的票种标识非法: {key}'
            )

    def test_expected_field_keys_known(self):
        """基线中用到的字段键都能在注册表中查到"""
        data = self._load()
        known = set(ALL_FIELD_KEYS) | {'invoice_type_key', 'tax_amount'}
        for item in data['invoices']:
            expected = item.get('expected') or {}
            for field_key in expected:
                self.assertIn(
                    field_key, known,
                    f'{item.get("file")} 使用了未知字段键: {field_key}'
                )

    def test_coverage_declared(self):
        """基线声明了覆盖与未覆盖票种，且两者都合法"""
        data = self._load()
        coverage = data.get('_meta', {}).get('coverage', {})
        covered = coverage.get('covered_types', [])
        missing = coverage.get('missing_types', [])
        for key in covered + missing:
            self.assertIn(key, INVOICE_TYPE_KEYS)
        # 已覆盖与未覆盖不重叠，且并集为全部 7 类
        self.assertFalse(set(covered) & set(missing))
        self.assertEqual(set(covered) | set(missing), set(INVOICE_TYPE_KEYS))


if __name__ == '__main__':
    unittest.main()
