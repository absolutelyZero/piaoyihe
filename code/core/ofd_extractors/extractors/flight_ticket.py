#!/usr/bin/env python3
"""
OFD飞机票提取器

提取航空运输电子客票行程单OFD发票的字段信息
"""

import re
import os
import time
from ..base import OFDExtractor


class OFDFlightTicketExtractor(OFDExtractor):
    """
    OFD飞机票提取器

    处理航空运输电子客票行程单等飞机票类型
    """

    INVOICE_TYPE_KEYWORDS = ['航空', '飞机票', '行程单', '电子客票']

    def extract_amount(self) -> float:
        """
        提取金额（票价）

        Returns:
            float: 提取的票价金额
        """
        try:
            patterns = [
                r'票价[¥￥]?\s*([\d,]+\.?\d*)',
                r'合计[¥￥]?\s*([\d,]+\.?\d*)',
                r'金额[¥￥]?\s*([\d,]+\.?\d*)',
            ]

            for pattern in patterns:
                match = re.search(pattern, self._text)
                if match:
                    amount_str = match.group(1).replace(',', '')
                    return float(amount_str)

        except Exception as e:
            print(f"[OFDFlightTicketExtractor] 提取金额失败: {e}")

        return 0.0

    def extract_invoice_date(self) -> str:
        """
        提取开票日期/乘机日期

        Returns:
            str: 日期字符串，格式YYYY-MM-DD
        """
        try:
            # 尝试提取乘机日期
            pattern = r'(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日'
            match = re.search(pattern, self._text)
            if match:
                year, month, day = match.groups()
                return f"{year}-{int(month):02d}-{int(day):02d}"

            # 尝试YYYY-MM-DD格式
            pattern2 = r'(\d{4})-(\d{2})-(\d{2})'
            match2 = re.search(pattern2, self._text)
            if match2:
                return match2.group(0)

        except Exception as e:
            print(f"[OFDFlightTicketExtractor] 提取日期失败: {e}")

        # 返回文件修改日期
        try:
            mod_time = os.path.getmtime(self.ofd_path)
            return time.strftime('%Y-%m-%d', time.localtime(mod_time))
        except Exception:
            return time.strftime('%Y-%m-%d', time.localtime())

    def extract_invoice_type(self) -> str:
        """
        提取发票类型

        Returns:
            str: 返回"飞机票"
        """
        return '飞机票'

    def extract_product_type(self) -> str:
        """
        提取商品类型/服务名称

        Returns:
            str: 返回"交通运输服务"
        """
        return '*交通运输服务'

    def extract_buyer_name(self) -> str:
        """
        提取购买方名称/旅客姓名

        Returns:
            str: 旅客姓名
        """
        try:
            # 尝试提取旅客姓名
            pattern = r'旅客姓名[：:]\s*([^\n]+)'
            match = re.search(pattern, self._text)
            if match:
                return match.group(1).strip()

            pattern2 = r'姓名[：:]\s*([^\n]+)'
            match2 = re.search(pattern2, self._text)
            if match2:
                return match2.group(1).strip()

            return '旅客'
        except Exception:
            return '旅客'

    def extract_seller_name(self) -> str:
        """
        提取销售方名称/承运人

        Returns:
            str: 航空公司名称
        """
        try:
            # 尝试提取承运人
            pattern = r'承运人[：:]\s*([^\n]+)'
            match = re.search(pattern, self._text)
            if match:
                return match.group(1).strip()

            # 尝试匹配常见航空公司
            airlines = ['中国国航', '南方航空', '东方航空', '海南航空', 
                       '厦门航空', '深圳航空', '四川航空', '山东航空']
            for airline in airlines:
                if airline in self._text:
                    return airline

            return '航空公司'
        except Exception:
            return '航空公司'

    def extract_invoice_code(self) -> str:
        """
        提取发票号码/票号

        Returns:
            str: 票号
        """
        try:
            # 尝试提取票号
            pattern = r'票号[：:]?\s*(\d+)'
            match = re.search(pattern, self._text)
            if match:
                return match.group(1)

            pattern2 = r'印刷序号[：:]?\s*(\w+)'
            match2 = re.search(pattern2, self._text)
            if match2:
                return match2.group(1)

            return ''
        except Exception:
            return ''

    def extract_tax_amount(self) -> float:
        """
        提取税额

        Returns:
            float: 提取的税额（飞机票通常为9%税率）
        """
        try:
            # 飞机票税额通常是票价的9%
            amount = self.extract_amount()
            if amount > 0:
                # 航空客运服务税率9%
                return round(amount / 1.09 * 0.09, 2)
            return 0.0
        except Exception:
            return 0.0
