#!/usr/bin/env python3
"""
OFD定额发票提取器

提取定额发票OFD发票的字段信息
"""

import re
import os
import time
from ..base import OFDExtractor


class OFDFixedAmountInvoiceExtractor(OFDExtractor):
    """
    OFD定额发票提取器

    处理定额发票等类型
    """

    INVOICE_TYPE_KEYWORDS = ['定额发票', '定额']

    def extract_amount(self) -> float:
        """
        提取金额（票面金额）

        Returns:
            float: 提取的金额
        """
        try:
            # 定额发票金额通常是固定的几个档位
            patterns = [
                r'([\d,]+\.?\d*)\s*元',
                r'金额[¥￥]?\s*([\d,]+\.?\d*)',
                r'面值[¥￥]?\s*([\d,]+\.?\d*)',
            ]

            for pattern in patterns:
                match = re.search(pattern, self._text)
                if match:
                    amount_str = match.group(1).replace(',', '')
                    return float(amount_str)

            # 常见定额发票金额
            amounts = [10, 20, 50, 100, 200, 500, 1000]
            for amt in amounts:
                if f'{amt}元' in self._text or f'¥{amt}' in self._text:
                    return float(amt)

        except Exception as e:
            print(f"[OFDFixedAmountInvoiceExtractor] 提取金额失败: {e}")

        return 0.0

    def extract_invoice_date(self) -> str:
        """
        提取开票日期

        Returns:
            str: 日期字符串，格式YYYY-MM-DD
        """
        try:
            pattern = r'(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日'
            match = re.search(pattern, self._text)
            if match:
                year, month, day = match.groups()
                return f"{year}-{int(month):02d}-{int(day):02d}"

            pattern2 = r'(\d{4})-(\d{2})-(\d{2})'
            match2 = re.search(pattern2, self._text)
            if match2:
                return match2.group(0)

        except Exception as e:
            print(f"[OFDFixedAmountInvoiceExtractor] 提取日期失败: {e}")

        try:
            mod_time = os.path.getmtime(self.ofd_path)
            return time.strftime('%Y-%m-%d', time.localtime(mod_time))
        except Exception:
            return time.strftime('%Y-%m-%d', time.localtime())

    def extract_invoice_type(self) -> str:
        """
        提取发票类型

        Returns:
            str: 返回"定额发票"
        """
        return '定额发票'

    def extract_product_type(self) -> str:
        """
        提取商品类型

        Returns:
            str: 返回"通用定额发票"
        """
        return '*通用定额发票'

    def extract_buyer_name(self) -> str:
        """
        提取购买方名称

        Returns:
            str: 购买方名称
        """
        return '购买方'

    def extract_seller_name(self) -> str:
        """
        提取销售方名称

        Returns:
            str: 销售方名称
        """
        try:
            pattern = r'单位[：:]\s*([^\n]+)'
            match = re.search(pattern, self._text)
            if match:
                return match.group(1).strip()

            return '销售方'
        except Exception:
            return '销售方'

    def extract_invoice_code(self) -> str:
        """
        提取发票号码

        Returns:
            str: 发票号码
        """
        try:
            pattern = r'发票号码[：:]?\s*(\d+)'
            match = re.search(pattern, self._text)
            if match:
                return match.group(1)

            return ''
        except Exception:
            return ''

    def extract_tax_amount(self) -> float:
        """
        提取税额

        Returns:
            float: 提取的税额（定额发票通常无税额或按3%计算）
        """
        try:
            # 定额发票税额通常按3%计算
            amount = self.extract_amount()
            if amount > 0:
                return round(amount / 1.03 * 0.03, 2)
            return 0.0
        except Exception:
            return 0.0
