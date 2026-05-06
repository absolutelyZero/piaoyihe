#!/usr/bin/env python3
"""
通行费发票提取器模块

处理通行费发票、ETC发票、过路费发票的字段提取。
"""

import re
import os
import time
from .base import InvoiceExtractor


class TollInvoiceExtractor(InvoiceExtractor):
    """
    通行费发票提取器

    处理通行费发票、ETC发票、过路费发票。

    Attributes:
        INVOICE_TYPE_KEYWORDS: 识别关键词
    """

    INVOICE_TYPE_KEYWORDS = ['通行费', 'ETC', '过路费', '收费公路']

    def extract_amount(self) -> float:
        """
        提取金额

        提取策略：
        1. 匹配"金额"字段
        2. 匹配"价税合计"字段
        3. 匹配"¥"符号后的数字

        Returns:
            float: 金额，失败返回0.0
        """
        patterns = [
            r'金额[:：]\s*[¥￥]?\s*(\d+(?:\.\d+)?)',
            r'价税合计[:：]\s*[¥￥]?\s*(\d+(?:\.\d+)?)',
            r'[¥￥]\s*(\d+(?:\.\d+)?)',
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
            str: "通行费发票"
        """
        return "通行费发票"

    def extract_product_type(self) -> str:
        """
        提取通行路段/服务名称

        提取策略：
        1. 匹配"路段"字段
        2. 匹配"入口"-"出口"信息

        Returns:
            str: 通行路段信息，无则返回空字符串
        """
        # 尝试提取入口-出口信息
        pattern = r'入口[:：]\s*([^\n]+).*?出口[:：]\s*([^\n]+)'
        match = re.search(pattern, self._text, re.DOTALL)
        if match:
            entry = match.group(1).strip()
            exit_ = match.group(2).strip()
            return f"{entry}-{exit_}"[:20]

        # 尝试提取路段信息
        pattern = r'路段[:：]\s*([^\n]+)'
        match = re.search(pattern, self._text)
        if match:
            return match.group(1).strip()[:20]

        return ""

    def extract_buyer_name(self) -> str:
        """
        提取购买方（车辆所有人）名称

        提取策略：
        1. 匹配"购买方"字段
        2. 匹配"车辆所有人"字段

        Returns:
            str: 购买方名称，无则返回空字符串
        """
        patterns = [
            r'购买方[:：]\s*([^\n]+)',
            r'车辆所有人[:：]\s*([^\n]+)',
            r'名称[:：]\s*([^\n]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, self._text)
            if match:
                buyer = match.group(1).strip()
                if len(buyer) > 2:
                    return buyer[:30]

        return ""

    def extract_invoice_code(self) -> str:
        """
        提取发票号码

        提取策略：
        1. 匹配"发票号码:"字段
        2. 匹配"代码:"字段
        3. 匹配20位数字代码格式

        Returns:
            str: 发票号码，无则返回空字符串
        """
        # 策略1：匹配"发票号码:"字段
        code_pattern = r'发票号码[:：]\s*(\d{20})'
        match = re.search(code_pattern, self._text)
        if match:
            return match.group(1).strip()

        # 策略2：匹配"代码:"字段
        code_pattern = r'代码[:：]\s*(\d{20})'
        match = re.search(code_pattern, self._text)
        if match:
            return match.group(1).strip()

        # 策略3：匹配20位数字代码格式
        code_pattern = r'\b(\d{20})\b'
        matches = re.findall(code_pattern, self._text)
        for code in matches:
            if code.startswith(('0', '1')):
                return code

        return ""

    def extract_seller_name(self) -> str:
        """
        提取销售方（收费单位）名称

        提取策略：
        1. 匹配"销售方"字段
        2. 匹配"收费单位"字段

        Returns:
            str: 销售方名称，无则返回空字符串
        """
        patterns = [
            r'销售方[:：]\s*([^\n]+)',
            r'收费单位[:：]\s*([^\n]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, self._text)
            if match:
                seller = match.group(1).strip()
                if len(seller) > 2:
                    return seller[:30]

        return ""
