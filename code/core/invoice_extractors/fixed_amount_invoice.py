#!/usr/bin/env python3
"""
定额发票提取器模块

处理定额发票的字段提取。
定额发票具有固定金额，通常用于小额交易。
"""

import re
import os
import time
from .base import InvoiceExtractor


class FixedAmountInvoiceExtractor(InvoiceExtractor):
    """
    定额发票提取器

    处理定额发票的字段提取。
    定额发票特点：
    - 金额是固定的（如10元、20元、50元、100元等）
    - 通常没有购买方/销售方信息
    - 有发票号码和发票号码

    Attributes:
        INVOICE_TYPE_KEYWORDS: 识别关键词
    """

    INVOICE_TYPE_KEYWORDS = ['定额发票']

    def extract_amount(self) -> float:
        """
        提取金额

        提取策略：
        1. 匹配"金额"字段
        2. 匹配"¥"符号后的数字
        3. 匹配常见的定额金额（10元、20元、50元、100元等）

        Returns:
            float: 金额，失败返回0.0
        """
        # 策略1：匹配金额字段
        patterns = [
            r'金额[:：]\s*[¥￥]?\s*(\d+)',
            r'[¥￥]\s*(\d+)',
            r'(\d+)\s*元',
        ]

        for pattern in patterns:
            match = re.search(pattern, self._text)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    pass

        # 策略2：匹配常见的定额金额标识
        fixed_amounts = [100, 50, 20, 10, 5, 2, 1]
        for amount in fixed_amounts:
            # 查找类似"壹佰元"、"100元"等格式
            patterns = [
                rf'{amount}\s*元',
            ]
            for pattern in patterns:
                if re.search(pattern, self._text):
                    return float(amount)

        return 0.0

    def extract_invoice_date(self) -> str:
        """
        提取日期

        提取策略：
        1. 匹配日期字段
        2. 返回文件修改日期作为备选

        Returns:
            str: 日期字符串，格式YYYY-MM-DD
        """
        patterns = [
            r'日期[:：]\s*(\d{4})[-年](\d{1,2})[-月](\d{1,2})',
            r'(\d{4})[-年](\d{1,2})[-月](\d{1,2})',
        ]

        for pattern in patterns:
            match = re.search(pattern, self._text)
            if match:
                year, month, day = match.groups()
                return f"{year}-{month.zfill(2)}-{day.zfill(2)}"

        mod_time = os.path.getmtime(self.pdf_path)
        return time.strftime('%Y-%m-%d', time.localtime(mod_time))

    def extract_invoice_type(self) -> str:
        """
        返回票种类型

        Returns:
            str: "定额发票"
        """
        return "定额发票"

    def extract_product_type(self) -> str:
        """
        定额发票没有商品类型

        Returns:
            str: 空字符串
        """
        return ""

    def extract_buyer_name(self) -> str:
        """
        定额发票通常没有购买方名称

        Returns:
            str: 空字符串
        """
        return ""

    def extract_seller_name(self) -> str:
        """
        定额发票通常没有销售方名称

        Returns:
            str: 空字符串
        """
        return ""

    def extract_invoice_code(self) -> str:
        """
        提取发票号码

        提取策略：
        1. 匹配"发票号码:"字段
        2. 匹配"代码:"字段
        3. 匹配12位数字代码格式

        Returns:
            str: 发票号码，无则返回空字符串
        """
        # 策略1：匹配"发票号码:"字段
        code_pattern = r'发票号码[:：]\s*(\d{10,12})'
        match = re.search(code_pattern, self._text)
        if match:
            return match.group(1).strip()

        # 策略2：匹配"代码:"字段
        code_pattern = r'代码[:：]\s*(\d{10,12})'
        match = re.search(code_pattern, self._text)
        if match:
            return match.group(1).strip()

        # 策略3：匹配12位数字代码格式
        code_pattern = r'\b(\d{12})\b'
        matches = re.findall(code_pattern, self._text)
        for code in matches:
            if code.startswith(('0', '1')):
                return code

        return ""

    def extract_tax_amount(self) -> float:
        """
        定额发票没有税额

        Returns:
            float: 0.0
        """
        return 0.0
