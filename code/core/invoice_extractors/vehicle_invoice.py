#!/usr/bin/env python3
"""
机动车发票提取器模块

处理机动车销售统一发票和二手车销售统一发票的字段提取。
"""

import re
import os
import time
from .base import InvoiceExtractor


class VehicleInvoiceExtractor(InvoiceExtractor):
    """
    机动车发票提取器

    处理机动车销售统一发票和二手车销售统一发票。

    Attributes:
        INVOICE_TYPE_KEYWORDS: 识别关键词
    """

    INVOICE_TYPE_KEYWORDS = ['机动车', '二手车', '车辆销售']

    def extract_amount(self) -> float:
        """
        提取金额

        提取策略：
        1. 匹配"价税合计"字段
        2. 匹配"合计金额"字段
        3. 匹配¥符号后的数字

        Returns:
            float: 金额，失败返回0.0
        """
        patterns = [
            r'价税合计[:：]\s*[¥￥]?\s*(\d+(?:,\d{3})*(?:\.\d+)?)',
            r'合计金额[:：]\s*[¥￥]?\s*(\d+(?:,\d{3})*(?:\.\d+)?)',
            r'[¥￥]\s*(\d+(?:,\d{3})*(?:\.\d+)?)',
        ]

        amount_max = 0.0
        for pattern in patterns:
            matches = re.findall(pattern, self._text)
            for match in matches:
                try:
                    amount_str = match.replace(',', '')
                    amount = float(amount_str)
                    if amount > amount_max:
                        amount_max = amount
                except ValueError:
                    pass

        return amount_max

    def extract_invoice_date(self) -> str:
        """
        提取开票日期

        提取策略：
        1. 匹配"开票日期"字段
        2. 匹配其他日期格式
        3. 返回文件修改日期作为备选

        Returns:
            str: 日期字符串，格式YYYY-MM-DD
        """
        patterns = [
            r'开票日期[:：]\s*(\d{4})[-年](\d{1,2})[-月](\d{1,2})',
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
            str: "机动车发票"或"二手车发票"
        """
        if '二手车' in self._text:
            return "二手车发票"
        return "机动车发票"

    def extract_product_type(self) -> str:
        """
        提取车辆类型/品牌

        提取策略：
        1. 匹配"车辆类型"字段
        2. 匹配"品牌型号"字段

        Returns:
            str: 车辆类型或品牌，无则返回空字符串
        """
        patterns = [
            r'车辆类型[:：]\s*([^\n]+)',
            r'品牌型号[:：]\s*([^\n]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, self._text)
            if match:
                return match.group(1).strip()[:20]

        return ""

    def extract_buyer_name(self) -> str:
        """
        提取购买方（买方）名称

        提取策略：
        1. 匹配"购买方"或"买方"字段
        2. 匹配"名称"字段（通常是第一个）

        Returns:
            str: 购买方名称
        """
        patterns = [
            r'购买方[:：]\s*([^\n]+)',
            r'买方[:：]\s*([^\n]+)',
            r'名称[:：]\s*([^\n]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, self._text)
            if match:
                buyer = match.group(1).strip()
                if len(buyer) > 2:
                    return buyer[:30]

        return "购买方"

    def extract_seller_name(self) -> str:
        """
        提取销售方（卖方）名称

        提取策略：
        1. 匹配"销售方"或"卖方"字段
        2. 匹配"销货单位"字段

        Returns:
            str: 销售方名称
        """
        patterns = [
            r'销售方[:：]\s*([^\n]+)',
            r'卖方[:：]\s*([^\n]+)',
            r'销货单位[:：]\s*([^\n]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, self._text)
            if match:
                seller = match.group(1).strip()
                if len(seller) > 2:
                    return seller[:30]

        return "销售方"

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
