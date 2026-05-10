#!/usr/bin/env python3
"""
飞机票提取器模块

处理航空电子客票行程单的字段提取。
飞机票具有特殊性：金额通常是票价+税费，有明确的乘机人，日期是乘机日期。
"""

import re
import os
import time
from .base import InvoiceExtractor


class FlightTicketExtractor(InvoiceExtractor):
    """
    飞机票/航空电子客票行程单提取器

    飞机票的特殊性：
    - 金额通常是票价+税费（合计金额）
    - 有明确的乘机人
    - 日期是乘机日期或填开日期
    - 有航空公司名称

    Attributes:
        INVOICE_TYPE_KEYWORDS: 识别关键词
    """

    INVOICE_TYPE_KEYWORDS = ['航空', '机票', '电子客票行程单']

    def extract_amount(self) -> float:
        """
        提取票价（通常是合计金额）

        提取策略：
        1. 匹配"合计"字段（优先级最高）
        2. 匹配"CNY"后的金额
        3. 匹配"总金额"、"价税合计"字段
        4. 匹配¥符号后的数字
        5. 返回找到的最大金额

        Returns:
            float: 票价金额，失败返回0.0
        """
        # 策略1：优先匹配"合计"字段（通常是最终金额）
        total_pattern = r'合计[:：]?\s*(?:CNY)?\s*[¥￥]?\s*(\d+(?:,\d{3})*(?:\.\d+)?)'
        match = re.search(total_pattern, self._text)
        if match:
            try:
                amount_str = match.group(1).replace(',', '')
                return float(amount_str)
            except ValueError:
                pass

        # 策略2：匹配CNY金额格式
        patterns = [
            r'CNY\s*(\d+(?:,\d{3})*(?:\.\d+)?)',  # CNY 760.00
            r'总金额[:：]\s*(?:CNY)?\s*[¥￥]?\s*(\d+(?:,\d{3})*(?:\.\d+)?)',
            r'价税合计[:：]\s*(?:CNY)?\s*[¥￥]?\s*(\d+(?:,\d{3})*(?:\.\d+)?)',
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
        提取日期（乘机日期或填开日期）

        提取策略：
        1. 优先匹配填开日期
        2. 匹配乘机日期
        3. 返回文件修改日期作为备选

        Returns:
            str: 日期字符串，格式YYYY-MM-DD
        """
        patterns = [
            r'填开日期[:：]\s*(\d{4})[-年](\d{1,2})[-月](\d{1,2})',
            r'乘机日期[:：]\s*(\d{4})[-年](\d{1,2})[-月](\d{1,2})',
            r'日期[:：]\s*(\d{4})[-年](\d{1,2})[-月](\d{1,2})',
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
            str: "飞机票"
        """
        return "飞机票"

    def extract_product_type(self) -> str:
        """
        飞机票没有商品类型

        Returns:
            str: 空字符串
        """
        return ""

    def extract_buyer_name(self) -> str:
        """
        提取购买方名称或乘机人姓名

        提取策略：
        1. 匹配"购买方名称"字段（电子发票常用，优先级最高）
        2. 匹配"乘机人"字段
        3. 匹配"旅客姓名"字段
        4. 匹配"姓名"字段

        Returns:
            str: 购买方名称或乘机人姓名，无则返回空字符串
        """
        # 策略1：匹配"购买方名称"（电子发票常用）
        # 精确匹配，确保获取公司名称而不是后面的统一社会信用代码
        pattern = r'购买方名称[:：]\s*([\u4e00-\u9fa5]{2,30}(?:公司|企业|股份|集团))'
        match = re.search(pattern, self._text)
        if match:
            buyer = match.group(1).strip()
            if len(buyer) > 2:
                return buyer[:30]

        # 策略1b：宽松匹配购买方名称（处理无冒号或特殊格式）
        pattern = r'购买方名称[:：]?\s*([^\n]{2,30}?)(?=\s|$|统一社会信用)'
        match = re.search(pattern, self._text)
        if match:
            buyer = match.group(1).strip()
            # 过滤掉识别号等无关内容
            if len(buyer) > 2 and '9141' not in buyer and '统一' not in buyer:
                return buyer[:30]

        # 策略2-4：匹配乘机人/旅客信息
        patterns = [
            r'乘机人[:：]\s*([^\n]+)',
            r'旅客姓名[:：]\s*([^\n]+)',
            r'姓名[:：]\s*([^\n]+)',
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
        提取销售方名称（航空公司或填开单位）

        提取策略：
        1. 匹配"填开单位"字段（优先级最高，电子发票常用）
        2. 匹配"销售方"字段
        3. 匹配"XX航空"格式
        4. 匹配"航空公司"关键词

        Returns:
            str: 销售方名称，无则返回空字符串
        """
        # 策略1：精确匹配"填开单位"后的公司名称
        # 确保匹配到"上海华程西南国际旅行社有限公司"而不是"填开日期"
        pattern = r'填开单位[:：]\s*([\u4e00-\u9fa5]{2,30}(?:公司|旅行社|企业))'
        match = re.search(pattern, self._text)
        if match:
            seller = match.group(1).strip()
            if len(seller) > 2 and '日期' not in seller:
                return seller[:30]

        # 策略1b：匹配填开单位，但排除"填开日期"的干扰
        # 使用否定前瞻确保不是"日期"
        pattern = r'填开单位(?!.*日期)[:：]?\s*([\u4e00-\u9fa5]{2,30})'
        match = re.search(pattern, self._text)
        if match:
            seller = match.group(1).strip()
            if len(seller) > 2 and '日期' not in seller and '20' not in seller:
                return seller[:30]

        # 策略1c：直接搜索"填开单位:"后的内容，限制长度避免跨行匹配错误
        lines = self._text.split('\n')
        for line in lines:
            if '填开单位' in line and '日期' not in line:
                # 提取冒号后的内容
                if ':' in line or '：' in line:
                    parts = re.split(r'[:：]', line, 1)
                    if len(parts) > 1:
                        seller = parts[1].strip()
                        # 过滤掉日期和识别号
                        if len(seller) > 2 and len(seller) < 30 and '日期' not in seller and not re.match(r'\d{4}年', seller):
                            return seller[:30]

        # 策略2：匹配"销售方"
        pattern = r'销售方[:：]\s*([^\n]+)'
        match = re.search(pattern, self._text)
        if match:
            seller = match.group(1).strip()
            if len(seller) > 2:
                return seller[:30]

        # 策略3：尝试提取航空公司名称
        pattern = r'([\u4e00-\u9fa5]+航空[\u4e00-\u9fa5]*)'
        match = re.search(pattern, self._text)
        if match:
            return match.group(1).strip()[:30]

        # 策略4：匹配"承运人"（也是航空公司）
        pattern = r'承运人[:：]\s*([^\n]+)'
        match = re.search(pattern, self._text)
        if match:
            seller = match.group(1).strip()
            if len(seller) > 1:
                return seller[:30]

        return ""
