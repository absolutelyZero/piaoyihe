#!/usr/bin/env python3
"""
OFD通行费发票提取器

提取通行费增值税电子普通发票OFD发票的字段信息
"""

import re
import os
import time
from ..base import OFDExtractor


class OFDTollInvoiceExtractor(OFDExtractor):
    """
    OFD通行费发票提取器

    处理通行费增值税电子普通发票等类型
    """

    INVOICE_TYPE_KEYWORDS = ['通行费', 'ETC', '高速公路', '收费公路']

    def extract_amount(self) -> float:
        """
        提取金额（价税合计）

        Returns:
            float: 提取的金额
        """
        try:
            patterns = [
                r'价税合计[¥￥]?\s*([\d,]+\.?\d*)',
                r'合计[¥￥]?\s*([\d,]+\.?\d*)',
                r'金额[¥￥]?\s*([\d,]+\.?\d*)',
                r'([\d,]+\.?\d*)\s*元',
            ]

            for pattern in patterns:
                match = re.search(pattern, self._text)
                if match:
                    amount_str = match.group(1).replace(',', '')
                    return float(amount_str)

        except Exception as e:
            print(f"[OFDTollInvoiceExtractor] 提取金额失败: {e}")

        return 0.0

    def extract_invoice_date(self) -> str:
        """
        提取开票日期/通行日期

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
            print(f"[OFDTollInvoiceExtractor] 提取日期失败: {e}")

        try:
            mod_time = os.path.getmtime(self.ofd_path)
            return time.strftime('%Y-%m-%d', time.localtime(mod_time))
        except Exception:
            return time.strftime('%Y-%m-%d', time.localtime())

    def extract_invoice_type(self) -> str:
        """
        提取发票类型

        Returns:
            str: 返回"通行费"
        """
        return '通行费'

    def extract_product_type(self) -> str:
        """
        提取商品类型

        Returns:
            str: 返回"道路通行服务"
        """
        return '*道路通行服务'

    def extract_buyer_name(self) -> str:
        """
        提取购买方名称

        Returns:
            str: 购买方名称
        """
        try:
            pattern = r'购买方[：:]\s*([^\n]+)'
            match = re.search(pattern, self._text)
            if match:
                return match.group(1).strip()

            pattern2 = r'车牌号[：:]\s*([^\n]+)'
            match2 = re.search(pattern2, self._text)
            if match2:
                return match2.group(1).strip()

            return '购买方'
        except Exception:
            return '购买方'

    def extract_seller_name(self) -> str:
        """
        提取销售方名称

        Returns:
            str: 销售方名称
        """
        try:
            pattern = r'销售方[：:]\s*([^\n]+)'
            match = re.search(pattern, self._text)
            if match:
                return match.group(1).strip()

            pattern2 = r'经营单位[：:]\s*([^\n]+)'
            match2 = re.search(pattern2, self._text)
            if match2:
                return match2.group(1).strip()

            return '收费公路经营管理单位'
        except Exception:
            return '收费公路经营管理单位'

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
            float: 提取的税额（通行费通常为3%税率）
        """
        try:
            # 通行费税额通常是金额的3%
            amount = self.extract_amount()
            if amount > 0:
                # 通行费服务税率3%
                return round(amount / 1.03 * 0.03, 2)
            return 0.0
        except Exception:
            return 0.0
