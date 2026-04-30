#!/usr/bin/env python3
"""
出租车发票提取器模块

处理出租车发票和出租汽车发票的字段提取。
"""

import re
import os
import time
from .base import InvoiceExtractor


class TaxiInvoiceExtractor(InvoiceExtractor):
    """
    出租车发票提取器

    处理出租车发票和出租汽车发票。

    Attributes:
        INVOICE_TYPE_KEYWORDS: 识别关键词
    """

    INVOICE_TYPE_KEYWORDS = ['出租车', '出租汽车', '的士']

    def extract_amount(self) -> float:
        """
        提取金额

        提取策略：
        1. 匹配"金额"字段
        2. 匹配"¥"符号后的数字
        3. 匹配"元"单位

        Returns:
            float: 金额，失败返回0.0
        """
        patterns = [
            r'金额[:：]\s*[¥￥]?\s*(\d+(?:\.\d+)?)',
            r'[¥￥]\s*(\d+(?:\.\d+)?)',
            r'(\d+(?:\.\d+)?)\s*元',
        ]

        for pattern in patterns:
            match = re.search(pattern, self._text)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    pass

        return 0.0

    def extract_invoice_date(self) -> str:
        """
        提取日期

        提取策略：
        1. 匹配"日期"字段
        2. 匹配其他日期格式
        3. 返回文件修改日期作为备选

        Returns:
            str: 日期字符串，格式YYYY-MM-DD
        """
        patterns = [
            r'日期[:：]\s*(\d{4})[-年](\d{1,2})[-月](\d{1,2})',
            r'(\d{4})[-年](\d{1,2})[-月](\d{1,2})',
            r'(\d{4})/(\d{1,2})/(\d{1,2})',
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
            str: "出租车发票"
        """
        return "出租车发票"

    def extract_product_type(self) -> str:
        """
        出租车发票没有商品类型

        Returns:
            str: 空字符串
        """
        return ""

    def extract_buyer_name(self) -> str:
        """
        出租车发票通常没有购买方名称

        Returns:
            str: 空字符串
        """
        return ""

    def extract_seller_name(self) -> str:
        """
        提取出租车公司名称

        提取策略：
        1. 匹配"XX出租"格式
        2. 匹配"XX出租车"格式
        3. 匹配"XX出租汽车"格式

        Returns:
            str: 出租车公司名称，无则返回空字符串
        """
        patterns = [
            r'([\u4e00-\u9fa5]+出租汽车公司?)',
            r'([\u4e00-\u9fa5]+出租车)',
            r'([\u4e00-\u9fa5]+出租)',
        ]

        for pattern in patterns:
            match = re.search(pattern, self._text)
            if match:
                return match.group(1).strip()[:30]

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
