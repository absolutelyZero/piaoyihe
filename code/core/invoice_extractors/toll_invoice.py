#!/usr/bin/env python3
"""
通行费发票提取器模块

处理通行费发票、ETC发票、过路费发票的字段提取。
"""

import re
import os
import time
from typing import Any, Dict
from .base import InvoiceExtractor, iter_company_names


class TollInvoiceExtractor(InvoiceExtractor):
    """
    通行费发票提取器

    处理通行费发票、ETC发票、过路费发票。

    Attributes:
        INVOICE_TYPE_KEYWORDS: 识别关键词
    """

    INVOICE_TYPE_KEYWORDS = ['通行费', 'ETC', '过路费', '收费公路']

    TYPE_KEY = "toll_invoice"

    def extract_amount(self) -> float:
        """
        提取金额（价税合计）

        提取策略（按优先级）：
        1. 匹配"价税合计（大写）… （小写）¥87.95"中的小写金额（新式通行费电子发票）
        2. 匹配"金额"字段（旧式通行费发票）
        3. 匹配"价税合计"字段
        4. 匹配"¥"符号后的数字（兜底）

        Returns:
            float: 金额，失败返回0.0
        """
        patterns = [
            # 新式通行费电子发票（普通发票）：价税合计（大写） 捌拾柒圆玖角伍分 （小写） ¥87.95
            r'（小写）\s*[¥￥]?\s*(\d+(?:,\d{3})*(?:\.\d+)?)',
            r'金额[:：]\s*[¥￥]?\s*(\d+(?:,\d{3})*(?:\.\d+)?)',
            r'价税合计[:：]\s*[¥￥]?\s*(\d+(?:,\d{3})*(?:\.\d+)?)',
            r'[¥￥]\s*(\d+(?:,\d{3})*(?:\.\d+)?)',
        ]

        for pattern in patterns:
            match = re.search(pattern, self._text)
            if match:
                try:
                    return float(match.group(1).replace(',', ''))
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

        # 策略4：旧版纸质发票把「购/买/方」拆成竖排单字，
        # 「名　　　　称:」中间夹全角空格，上面的标签全都不匹配，
        # 改为按票面公司名的出现顺序推断（第 1 个为购买方，第 2 个为销售方）
        names = iter_company_names(self._text)
        if names:
            return names[0][:30]

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

        # 策略3：旧版纸质发票版式——12 位发票代码 + 8 位发票号码
        # 两者可能各占一行（值区），也可能带标签同行（如「发票代码: 023002300111 … 发票号码: 02621811」）
        # 统一拼成 20 位，便于存储与查重（机器编号 499098461547 后接中文大写，不会误中）
        old_layouts = [
            r'发票代码[:：]?\s*(\d{12})\s*(\d{8})(?!\d)',
            r'发票代码[:：]?\s*(\d{12})[\s\S]{0,200}?发票号码[:：]?\s*(\d{8})',
            r'(?<!\d)(\d{12})\s*\n\s*(\d{8})(?!\d)',
        ]
        for code_pattern in old_layouts:
            match = re.search(code_pattern, self._text)
            if match:
                return (match.group(1) + match.group(2)).strip()

        # 策略4：匹配20位数字代码格式
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

        # 策略3：同 extract_buyer_name 的说明，按公司名出现顺序取第 2 个
        names = iter_company_names(self._text)
        if len(names) >= 2:
            return names[1][:30]

        return ""

    def extract_tax_amount(self) -> float:
        """
        提取税额

        提取策略（按优先级）：
        1. 匹配"税率/征收率 + 税额"表格行（如 3% 2.56），支持多行合计
        2. 匹配"税额"字段
        3. 匹配"合计税额"字段
        4. 返回0.0

        Returns:
            float: 提取的税额，无则返回0.0
        """
        total_amount = self.extract_amount()

        # 策略1：匹配"税率/征收率 + 税额"表格行
        # 新式通行费电子发票表格行如：145.40   3%   4.36
        tax_rate_patterns = [
            r'(?:-?\d+(?:,\d{3})*(?:\.\d+)?)\s+(\d+(?:\.\d+)?)%\s+(?:CNY\s+)?[¥￥]?\s*(-?\d+(?:,\d{3})*(?:\.\d+)?)',
            r'(\d+(?:\.\d+)?)%\s+(?:CNY\s+)?[¥￥]?\s*(-?\d+(?:,\d{3})*(?:\.\d+)?)',
        ]
        tax_values = set()
        for tax_rate_pattern in tax_rate_patterns:
            matches = re.findall(tax_rate_pattern, self._text)
            for _rate_str, tax_str in matches:
                try:
                    tax = float(tax_str.replace(',', ''))
                except ValueError:
                    continue
                # 合理性校验：税额通常小于价税合计
                if total_amount > 0 and abs(tax) < total_amount:
                    tax_values.add(tax)
                elif total_amount == 0:
                    tax_values.add(tax)
        if tax_values:
            # 返回所有税额的合计（支持多行发票和折扣行自动抵消）
            return sum(tax_values)

        # 策略2：匹配"税额"字段
        tax_patterns = [
            r'税\s*额[:：]\s*[¥￥]?\s*(-?\d+(?:,\d{3})*(?:\.\d+)?)',
            r'合\s*计\s*税\s*额[:：]\s*[¥￥]?\s*(-?\d+(?:,\d{3})*(?:\.\d+)?)',
        ]

        for pattern in tax_patterns:
            match = re.search(pattern, self._text)
            if match:
                try:
                    return float(match.group(1).replace(',', ''))
                except ValueError:
                    pass

        return 0.0

    def extract_extra_fields(self) -> Dict[str, Any]:
        """
        提取通行费发票特有字段：入口、出口、路段

        注意：不改变现有 extract_product_type() 的取值口径，
        这里只补充独立的入口/出口/路段字段。

        Returns:
            Dict[str, Any]: toll_entry / toll_exit / toll_section
        """
        text = self._text or ""
        entry = ""
        exit_ = ""
        section = ""

        # 入口-出口：同一段文本内匹配
        match = re.search(
            r'入\s*口[:：]?\s*([^\n]{1,20}?)\s*(?:出\s*口[:：]?\s*([^\n]{1,20}?))?(?:\n|$)',
            text
        )
        if match:
            entry = (match.group(1) or '').strip()[:20]
            exit_ = (match.group(2) or '').strip()[:20]

        # 旧版纸质发票版式：车辆与站点写在同一行，形如
        # 「黑A14T6T 哈尔滨机场站入 哈尔滨机场出 2024-12-26 06:53:46」
        # 「吉林龙嘉机场收费站入 吉林长春东收费站出 2025-01-19 13:38:13」
        if not entry or not exit_:
            match = re.search(
                r'([\u4e00-\u9fa5A-Za-z0-9]{2,15}站)入\s+'
                r'([\u4e00-\u9fa5A-Za-z0-9]{2,15}?站?)出',
                text
            )
            if match:
                if not entry:
                    entry = match.group(1).strip()[:20]
                if not exit_:
                    exit_ = match.group(2).strip()[:20]

        # 单独匹配出口（入口未带出出口时）
        if not exit_:
            match = re.search(r'出\s*口[:：]?\s*([^\n]{1,20})', text)
            if match:
                exit_ = match.group(1).strip()[:20]

        # 路段（标签后必须是实际路名，不能是「无路段信息」这类否定描述的残留）
        match = re.search(r'路\s*段[:：]?\s*([^\n]{1,20})', text)
        if match:
            candidate = match.group(1).strip()[:20]
            # 排除「无路段」等否定描述与纯表头词
            if candidate and not candidate.startswith(('无', '信息', '：', ':')) \
                    and '无路' not in match.group(0)[:6]:
                section = candidate

        # 清洗：去掉残留的「出口」标签文字
        entry = re.sub(r'出\s*口[:：]?', '', entry).strip()
        exit_ = re.sub(r'入\s*口[:：]?', '', exit_).strip()

        return {
            'toll_entry': entry,
            'toll_exit': exit_,
            'toll_section': section,
        }
