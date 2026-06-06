#!/usr/bin/env python3
"""
OFD普通发票提取器

提取增值税普通发票、专用发票等常见OFD发票的字段信息
"""

import re
import os
import time
from ..base import OFDExtractor


class OFDCommonInvoiceExtractor(OFDExtractor):
    """
    OFD普通发票提取器

    处理增值税普通发票、专用发票等
    """

    INVOICE_TYPE_KEYWORDS = ['发票', '增值税']

    def extract_amount(self) -> float:
        """
        提取金额（价税合计）

        策略：
        1. 从OFD的XML数据中提取精确字段
        2. 回退到文本正则匹配

        Returns:
            float: 提取的金额，失败返回0.0
        """
        try:
            # 尝试从OFD结构化数据提取
            if self._ofd and hasattr(self._ofd, 'get_invoice_data'):
                data = self._ofd.get_invoice_data()
                if data and 'TotalAmount' in data:
                    return float(data['TotalAmount'])

            # 回退到文本匹配
            patterns = [
                r'价税合计[¥￥]?\s*([\d,]+\.?\d*)',
                r'合\s*计[¥￥]?\s*([\d,]+\.?\d*)',
                r'金\s*额[¥￥]?\s*([\d,]+\.?\d*)',
            ]

            for pattern in patterns:
                match = re.search(pattern, self._text)
                if match:
                    amount_str = match.group(1).replace(',', '')
                    return float(amount_str)

        except Exception as e:
            print(f"[OFDCommonInvoiceExtractor] 提取金额失败: {e}")

        return 0.0

    def extract_invoice_date(self) -> str:
        """
        提取开票日期

        Returns:
            str: 日期字符串，格式YYYY-MM-DD
        """
        try:
            # 尝试从OFD结构化数据提取
            if self._ofd and hasattr(self._ofd, 'get_invoice_data'):
                data = self._ofd.get_invoice_data()
                if data and 'IssueDate' in data:
                    return data['IssueDate']

            # 回退到文本匹配
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
            print(f"[OFDCommonInvoiceExtractor] 提取开票日期失败: {e}")

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
            str: 发票类型，如"普票"、"专票"
        """
        try:
            if '专用发票' in self._text:
                return '专票'
            elif '普通发票' in self._text:
                return '普票'
            elif '电子发票' in self._text:
                return '电子普票'
            else:
                return '普票'
        except Exception:
            return '普票'

    def extract_product_type(self) -> str:
        """
        提取商品类型

        Returns:
            str: 商品或服务名称
        """
        try:
            # 尝试提取货物或应税劳务名称
            pattern = r'货物或应税劳务.*?名称\s*([\u4e00-\u9fa5]+)'
            match = re.search(pattern, self._text, re.DOTALL)
            if match:
                return match.group(1).strip()
            return '*商品'
        except Exception:
            return '*商品'

    def extract_buyer_name(self) -> str:
        """
        提取购买方名称

        Returns:
            str: 购买方名称
        """
        try:
            # 尝试从OFD结构化数据提取
            if self._ofd and hasattr(self._ofd, 'get_invoice_data'):
                data = self._ofd.get_invoice_data()
                if data and 'BuyerName' in data:
                    return data['BuyerName']

            # 回退到文本匹配
            pattern = r'购买方.*?名\s*称\s*[:：]\s*([^\n]+)'
            match = re.search(pattern, self._text, re.DOTALL)
            if match:
                return match.group(1).strip()

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
            # 尝试从OFD结构化数据提取
            if self._ofd and hasattr(self._ofd, 'get_invoice_data'):
                data = self._ofd.get_invoice_data()
                if data and 'SellerName' in data:
                    return data['SellerName']

            # 回退到文本匹配
            pattern = r'销售方.*?名\s*称\s*[:：]\s*([^\n]+)'
            match = re.search(pattern, self._text, re.DOTALL)
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
            # 尝试从OFD结构化数据提取
            if self._ofd and hasattr(self._ofd, 'get_invoice_data'):
                data = self._ofd.get_invoice_data()
                if data:
                    # 发票代码+发票号码
                    code = data.get('InvoiceCode', '')
                    number = data.get('InvoiceNumber', '')
                    if code and number:
                        return f"{code}{number}"
                    return number or code

            # 回退到文本匹配
            pattern = r'发票号码\s*[:：]?\s*(\d+)'
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
            float: 提取的税额
        """
        try:
            # 尝试从OFD结构化数据提取
            if self._ofd and hasattr(self._ofd, 'get_invoice_data'):
                data = self._ofd.get_invoice_data()
                if data and 'TaxAmount' in data:
                    return float(data['TaxAmount'])

            # 回退到文本匹配
            pattern = r'税\s*额[¥￥]?\s*([\d,]+\.?\d*)'
            match = re.search(pattern, self._text)
            if match:
                amount_str = match.group(1).replace(',', '')
                return float(amount_str)

            return 0.0
        except Exception:
            return 0.0
