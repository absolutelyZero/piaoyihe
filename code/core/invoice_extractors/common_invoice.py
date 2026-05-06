#!/usr/bin/env python3
"""
普通发票提取器模块

处理增值税普通发票和专用发票的字段提取。
作为兜底提取器，处理常规增值税发票。
"""

import re
import os
import time
from .base import InvoiceExtractor


class CommonInvoiceExtractor(InvoiceExtractor):
    """
    普通发票提取器（增值税普通/专用发票）

    作为兜底提取器，处理常规增值税发票。
    当其他特殊票种提取器无法匹配时，使用此提取器。

    Attributes:
        INVOICE_TYPE_KEYWORDS: 识别关键词，["发票"]作为兜底匹配
    """

    INVOICE_TYPE_KEYWORDS = ["发票"]

    def extract_amount(self) -> float:
        """
        提取金额

        提取策略（按优先级）：
        1. 查找"价税合计"、"合计"等关键词附近的金额
        2. 全局查找金额格式（¥符号、元单位等）
        3. 返回找到的最大金额

        Returns:
            float: 提取的金额，失败返回0.0
        """
        amount_max = 0.0

        # 策略1：查找关键词附近的金额
        amount_keywords = ["价税合计", "合计", "金额", "小写"]

        for keyword in amount_keywords:
            if keyword in self._text:
                # 在关键词附近查找金额
                pattern = rf'{keyword}.*?[¥￥]?\s*(\d+(?:,\d{3})*(?:\.\d+)?)'
                matches = re.findall(pattern, self._text)
                for match in matches:
                    try:
                        amount_str = match.replace(',', '')
                        amount = float(amount_str)
                        if amount > amount_max:
                            amount_max = amount
                    except ValueError:
                        pass

        # 策略2：全局查找金额格式
        if amount_max == 0:
            patterns = [
                r'[¥￥]\s*(\d+(?:,\d{3})*(?:\.\d+)?)',
                r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*元',
            ]

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

        提取策略（按优先级）：
        1. 优先匹配"开票日期:"后面的日期
        2. 匹配其他日期格式（YYYY年MM月DD日、YYYY-MM-DD等）
        3. 返回文件修改日期作为备选

        Returns:
            str: 日期字符串，格式YYYY-MM-DD
        """
        # 策略1：优先匹配"开票日期:"
        invoice_date_pattern = r'开票日期[:：]\s*(\d{4})年(\d{1,2})月(\d{1,2})日?'
        match = re.search(invoice_date_pattern, self._text)
        if match:
            year, month, day = match.groups()
            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"

        # 策略2：匹配其他日期格式
        date_patterns = [
            r'(\d{4})年(\d{1,2})月(\d{1,2})日',
            r'(\d{4})年(\d{1,2})月(\d{1,2})',
            r'(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})',
        ]

        for pattern in date_patterns:
            matches = re.findall(pattern, self._text)
            for match in matches:
                if len(match) == 3:
                    year, month, day = match
                    if 1 <= int(month) <= 12 and 1 <= int(day) <= 31:
                        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"

        # 策略3：返回文件修改日期
        mod_time = os.path.getmtime(self.pdf_path)
        return time.strftime('%Y-%m-%d', time.localtime(mod_time))

    def extract_invoice_type(self) -> str:
        """
        提取发票类型

        提取策略（按优先级）：
        1. 优先匹配"发票类型:"字段
        2. 匹配标题中的发票类型（如"电子发票（普通发票）"）
        3. 通过关键词判断（专票/普票）

        Returns:
            str: 发票类型，如"专票"、"普票"
        """
        type_keywords = {
            "专票": ["增值税专用发票", "电子专用发票", "专用发票"],
            "普票": ["增值税普通发票", "电子普通发票", "普通发票"],
        }

        # 策略1：匹配"发票类型:"字段
        invoice_type_pattern = r'发票类型[:：]\s*([^\n]+)'
        match = re.search(invoice_type_pattern, self._text)
        if match:
            invoice_type = match.group(1).strip()
            for standard_type, keywords in type_keywords.items():
                for keyword in keywords:
                    if keyword in invoice_type:
                        return standard_type
            return invoice_type

        # 策略2：匹配标题格式
        title_pattern = r'电子发票\s*[（(]([^)）]+)[)）]'
        match = re.search(title_pattern, self._text)
        if match:
            title_type = match.group(1).strip()
            for standard_type, keywords in type_keywords.items():
                for keyword in keywords:
                    if keyword in title_type:
                        return standard_type

        # 策略3：关键词匹配
        for standard_type, keywords in type_keywords.items():
            for keyword in keywords:
                if keyword in self._text:
                    return standard_type

        return "普票"

    def extract_product_type(self) -> str:
        """
        提取商品类型/服务名称

        提取策略（按优先级）：
        1. 匹配"货物或应税劳务名称"字段
        2. 匹配"项目名称"、"商品名称"、"服务名称"字段
        3. 提取*星号包裹的内容（税收分类编码后的名称）

        Returns:
            str: 商品或服务名称，无则返回"商品"
        """
        patterns = [
            r'货物或应税劳务.*?名\s*称[:：]\s*([^\n]+)',
            r'项目名称[:：]\s*([^\n]+)',
            r'商品名称[:：]\s*([^\n]+)',
            r'服务名称[:：]\s*([^\n]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, self._text)
            if match:
                product = match.group(1).strip()
                product = product.replace('*', '').strip()
                if product:
                    return product[:20]

        # 提取*包裹的内容
        star_pattern = r'\*([^*]+)\*'
        matches = re.findall(star_pattern, self._text)
        if matches:
            product = matches[0].strip()
            if product and len(product) > 1:
                return product[:20]

        return "商品"

    def extract_buyer_name(self) -> str:
        """
        提取购买方名称

        提取策略（按优先级）：
        1. 匹配"购买方信息"区域内的"名称:"
        2. 查找第一个包含公司关键词的"名称:"
        3. 查找第一个公司名称

        Returns:
            str: 购买方名称
        """
        # 策略1：匹配"购买方信息"区域
        buyer_pattern = r'购[买\n]*方[\n\s]*信[\n\s]*息[\n\s]*.*?名[\n\s]*称[：:]\s*([\u4e00-\u9fa5a-zA-Z0-9（）()]+)'
        match = re.search(buyer_pattern, self._text, re.DOTALL)
        if match:
            buyer = match.group(1).strip().replace('\n', '').replace(' ', '')
            if len(buyer) > 4:
                return buyer[:30]

        # 策略2：查找第一个包含公司关键词的"名称:"
        name_pattern = r'名[\n\s]*称[：:]\s*([\u4e00-\u9fa5a-zA-Z0-9（）()]+)'
        matches = re.findall(name_pattern, self._text)
        company_keywords = ['公司', '企业', '股份', '有限', '集团', '厂', '店', '中心', '工作室']
        for buyer in matches:
            buyer = buyer.strip().replace('\n', '').replace(' ', '')
            if len(buyer) > 4 and any(keyword in buyer for keyword in company_keywords):
                return buyer[:30]

        # 策略3：查找第一个公司名称
        company_pattern = r'([\u4e00-\u9fa5a-zA-Z0-9（）()]*(?:公司|企业|股份|有限|集团|厂|店|中心|工作室)[\u4e00-\u9fa5a-zA-Z0-9（）()]*)'
        matches = re.findall(company_pattern, self._text)
        for buyer in matches:
            buyer = buyer.strip().replace('\n', '').replace(' ', '')
            if len(buyer) > 4:
                return buyer[:30]

        return "购买方"

    def extract_seller_name(self) -> str:
        """
        提取销售方名称

        提取策略（按优先级）：
        1. 匹配"销售方信息"区域内的"名称:"
        2. 查找第二个"名称:"（第一个是购买方）
        3. 查找最后一个公司名称

        Returns:
            str: 销售方名称
        """
        # 策略1：匹配"销售方信息"区域
        seller_pattern = r'销[售\n]*方[\n\s]*信[\n\s]*息[\n\s]*.*?名[\n\s]*称[：:]\s*([\u4e00-\u9fa5a-zA-Z0-9（）()]+)'
        match = re.search(seller_pattern, self._text, re.DOTALL)
        if match:
            seller = match.group(1).strip().replace('\n', '').replace(' ', '')
            if len(seller) > 4:
                return seller[:30]

        # 策略2：查找第二个"名称:"
        name_pattern = r'名[\n\s]*称[：:]\s*([\u4e00-\u9fa5a-zA-Z0-9（）()]+)'
        matches = re.findall(name_pattern, self._text)
        company_keywords = ['公司', '企业', '股份', '有限', '集团', '厂', '店', '中心', '工作室']
        if len(matches) >= 2:
            seller = matches[1].strip().replace('\n', '').replace(' ', '')
            if len(seller) > 4 and any(keyword in seller for keyword in company_keywords):
                return seller[:30]

        # 策略3：查找最后一个公司名称
        company_pattern = r'([\u4e00-\u9fa5a-zA-Z0-9（）()]*(?:公司|企业|股份|有限|集团|厂|店|中心|工作室)[\u4e00-\u9fa5a-zA-Z0-9（）()]*)'
        matches = re.findall(company_pattern, self._text)
        if matches:
            seller = matches[-1].strip().replace('\n', '').replace(' ', '')
            if len(seller) > 4:
                return seller[:30]

        return "销售方"

    def extract_invoice_code(self) -> str:
        """
        提取发票号码

        提取策略（按优先级）：
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

        # 策略2：匹配"代码:"字段（在发票信息区域）
        code_pattern = r'代码[:：]\s*(\d{20})'
        match = re.search(code_pattern, self._text)
        if match:
            return match.group(1).strip()

        # 策略3：匹配20位数字代码格式（通常是发票号码）
        code_pattern = r'\b(\d{20})\b'
        matches = re.findall(code_pattern, self._text)
        for code in matches:
            # 发票号码通常以特定数字开头
            if code.startswith(('0', '1')):
                return code

        return ""
