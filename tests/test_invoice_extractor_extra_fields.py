#!/usr/bin/env python3
"""
发票提取器票种标识与特有字段单元测试

不依赖真实 PDF：直接构造 _text 断言提取结果，
或对 extract_extra_fields 做纯函数级断言。
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'code'))

from core.invoice_extractors.base import InvoiceExtractor
from core.invoice_extractors.factory import InvoiceExtractorFactory
from core.invoice_field_registry import INVOICE_TYPE_KEYS
from core.invoice_extractors.common_invoice import CommonInvoiceExtractor
from core.invoice_extractors.fixed_amount_invoice import FixedAmountInvoiceExtractor
from core.invoice_extractors.toll_invoice import TollInvoiceExtractor
from core.invoice_extractors.taxi_invoice import TaxiInvoiceExtractor
from core.invoice_extractors.train_ticket import TrainTicketExtractor
from core.invoice_extractors.flight_ticket import FlightTicketExtractor
from core.invoice_extractors.vehicle_invoice import VehicleInvoiceExtractor


def make(extractor_cls, text):
    """构造一个已注入文本的提取器（跳过 PDF 打开）"""
    inst = extractor_cls('dummy.pdf')
    inst._text = text
    inst._pages = []
    return inst


class _MinimalExtractor(InvoiceExtractor):
    """最小子类：只实现抽象方法，不覆写钩子"""

    TYPE_KEY = 'test_type'

    def extract_amount(self):
        return 1.0

    def extract_invoice_date(self):
        return '2024-01-01'

    def extract_invoice_type(self):
        return '测试票'

    def extract_product_type(self):
        return ''

    def extract_buyer_name(self):
        return ''

    def extract_seller_name(self):
        return ''

    def extract_invoice_code(self):
        return ''

    def extract_tax_amount(self):
        return 0.0


class TestBaseHook(unittest.TestCase):
    """基类钩子契约"""

    def test_default_extra_fields_empty(self):
        """未覆写钩子时返回空字典"""
        inst = _MinimalExtractor('dummy.pdf')
        self.assertEqual(inst.extract_extra_fields(), {})

    def test_extract_all_contains_type_key(self):
        """extract_all 含 invoice_type_key"""
        inst = _MinimalExtractor('dummy.pdf')
        info = inst.extract_all()
        self.assertEqual(info['invoice_type_key'], 'test_type')

    def test_extract_all_merges_extra_fields(self):
        """extract_all 合并子类特有字段"""

        class WithExtra(_MinimalExtractor):
            def extract_extra_fields(self):
                return {'train_number': 'G1'}

        info = WithExtra('dummy.pdf').extract_all()
        self.assertEqual(info['train_number'], 'G1')
        self.assertEqual(info['invoice_type_key'], 'test_type')

    def test_broken_extra_fields_does_not_break_all(self):
        """特有字段提取抛异常时不影响通用字段"""

        class Broken(_MinimalExtractor):
            def extract_extra_fields(self):
                raise RuntimeError('boom')

        info = Broken('dummy.pdf').extract_all()
        self.assertEqual(info['amount'], 1.0)
        self.assertIn('invoice_type_key', info)


class TestTypeKeys(unittest.TestCase):
    """各提取器的 TYPE_KEY"""

    def test_all_registered_have_unique_type_keys(self):
        """所有注册提取器的 TYPE_KEY 非空、互不重复、并集等于 INVOICE_TYPE_KEYS"""
        extractors = InvoiceExtractorFactory.get_registered_extractors()
        keys = [e.TYPE_KEY for e in extractors]
        for key in keys:
            self.assertTrue(key, '存在 TYPE_KEY 为空的提取器')
        self.assertEqual(len(keys), len(set(keys)), 'TYPE_KEY 存在重复')
        self.assertEqual(set(keys), set(INVOICE_TYPE_KEYS))

    def test_specific_mapping(self):
        """票种标识按设计落位"""
        self.assertEqual(CommonInvoiceExtractor.TYPE_KEY, 'vat_invoice')
        self.assertEqual(TrainTicketExtractor.TYPE_KEY, 'train_ticket')
        self.assertEqual(FlightTicketExtractor.TYPE_KEY, 'flight_ticket')
        self.assertEqual(VehicleInvoiceExtractor.TYPE_KEY, 'vehicle_invoice')
        self.assertEqual(TaxiInvoiceExtractor.TYPE_KEY, 'taxi_invoice')
        self.assertEqual(FixedAmountInvoiceExtractor.TYPE_KEY, 'fixed_amount_invoice')
        self.assertEqual(TollInvoiceExtractor.TYPE_KEY, 'toll_invoice')


class TestTrainTicketExtras(unittest.TestCase):
    """火车票特有字段"""

    TEXT = (
        '电子发票（铁路电子客票）\n'
        '河源东站太湖南站G636\n'
        'HeyuandongTaihunan\n'
        '2026年03月28日07:56\n'
        '4105211990****2519 郭涛\n'
        '￥496.00'
    )

    def test_extract_all_three_fields(self):
        """车次/出发站/到达站都能提取"""
        fields = make(TrainTicketExtractor, self.TEXT).extract_extra_fields()
        self.assertEqual(fields['train_number'], 'G636')
        self.assertEqual(fields['departure_station'], '河源东站')
        self.assertEqual(fields['arrival_station'], '太湖南站')

    def test_labeled_format(self):
        """带标签的版式也能提取"""
        text = '车次: D1234\n出发站: 北京南\n到达站: 上海虹桥'
        fields = make(TrainTicketExtractor, text).extract_extra_fields()
        self.assertEqual(fields['train_number'], 'D1234')
        self.assertEqual(fields['departure_station'], '北京南')
        self.assertEqual(fields['arrival_station'], '上海虹桥')

    def test_missing_returns_empty(self):
        """无相关文案时返回空字符串"""
        fields = make(TrainTicketExtractor, '随便一段文字').extract_extra_fields()
        self.assertEqual(fields['train_number'], '')
        self.assertEqual(fields['departure_station'], '')
        self.assertEqual(fields['arrival_station'], '')


class TestFlightTicketExtras(unittest.TestCase):
    """飞机票特有字段"""

    TEXT = (
        '电子发票（航空运输电子客票行程单）\n'
        '承运人 航班号 座位等级\n'
        '深航 ZH8377 L\n'
        'CNY 760.00'
    )

    def test_extract_flight_and_airline(self):
        """航班号与航空公司都能提取"""
        fields = make(FlightTicketExtractor, self.TEXT).extract_extra_fields()
        self.assertEqual(fields['flight_number'], 'ZH8377')
        self.assertEqual(fields['airline'], '深航')

    def test_airline_from_airline_word(self):
        """能从「XX航空」推断航空公司"""
        fields = make(FlightTicketExtractor, '中国国际航空公司 MU5100').extract_extra_fields()
        self.assertEqual(fields['flight_number'], 'MU5100')
        self.assertIn('航空', fields['airline'])

    def test_missing_returns_empty(self):
        """缺失时为 "" """
        fields = make(FlightTicketExtractor, '无航班信息').extract_extra_fields()
        self.assertEqual(fields['flight_number'], '')
        self.assertEqual(fields['airline'], '')


class TestTaxiExtras(unittest.TestCase):
    """出租车发票特有字段"""

    def test_extract_plate(self):
        """按标签提取车牌号"""
        fields = make(TaxiInvoiceExtractor, '车牌号：粤B12345\n金额 18.50').extract_extra_fields()
        self.assertEqual(fields['plate_number'], '粤B12345')

    def test_extract_plate_without_label(self):
        """无标签时按格式匹配"""
        fields = make(TaxiInvoiceExtractor, '出租车 京A88888 里程3km').extract_extra_fields()
        self.assertEqual(fields['plate_number'], '京A88888')

    def test_missing_returns_empty(self):
        """缺失时为 "" """
        fields = make(TaxiInvoiceExtractor, '无车牌').extract_extra_fields()
        self.assertEqual(fields['plate_number'], '')


class TestVehicleExtras(unittest.TestCase):
    """机动车发票特有字段"""

    VIN = 'LSVAA4187E2109876'

    def test_extract_vin_by_label(self):
        """按「车架号」标签提取 VIN"""
        fields = make(VehicleInvoiceExtractor, f'车架号：{self.VIN}').extract_extra_fields()
        self.assertEqual(fields['vin'], self.VIN)

    def test_extract_vin_by_vehicle_id_label(self):
        """按「车辆识别代号」标签提取"""
        fields = make(VehicleInvoiceExtractor, f'车辆识别代号 {self.VIN}').extract_extra_fields()
        self.assertEqual(fields['vin'], self.VIN)

    def test_missing_returns_empty(self):
        """缺失时为 "" """
        fields = make(VehicleInvoiceExtractor, '无车架号').extract_extra_fields()
        self.assertEqual(fields['vin'], '')


class TestTollExtras(unittest.TestCase):
    """通行费发票特有字段"""

    def test_extract_entry_exit(self):
        """入口/出口都能提取"""
        fields = make(
            TollInvoiceExtractor, '入口：北京南\n出口：天津西\n金额 87.95'
        ).extract_extra_fields()
        self.assertEqual(fields['toll_entry'], '北京南')
        self.assertEqual(fields['toll_exit'], '天津西')

    def test_extract_section(self):
        """路段可提取"""
        fields = make(TollInvoiceExtractor, '路段：京沪高速').extract_extra_fields()
        self.assertEqual(fields['toll_section'], '京沪高速')

    def test_missing_returns_empty(self):
        """缺失时为 "" """
        fields = make(TollInvoiceExtractor, '无路段信息').extract_extra_fields()
        self.assertEqual(fields['toll_entry'], '')
        self.assertEqual(fields['toll_exit'], '')
        self.assertEqual(fields['toll_section'], '')

    def test_product_type_unchanged(self):
        """不改变 extract_product_type 的取值口径：入口-出口拼接"""
        text = '入口：北京南\n出口：天津西'
        inst = make(TollInvoiceExtractor, text)
        # 原有逻辑：入口-出口 拼成 product_type
        self.assertEqual(inst.extract_product_type(), '北京南-天津西')


class TestNoExtraFields(unittest.TestCase):
    """无特有字段的票种"""

    def test_common_invoice_has_no_extras(self):
        """增值税发票无特有字段"""
        self.assertEqual(CommonInvoiceExtractor('dummy.pdf').extract_extra_fields(), {})

    def test_fixed_amount_has_no_extras(self):
        """定额发票无特有字段"""
        self.assertEqual(FixedAmountInvoiceExtractor('dummy.pdf').extract_extra_fields(), {})


if __name__ == '__main__':
    unittest.main()
