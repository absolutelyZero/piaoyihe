#!/usr/bin/env python3
"""
火车票提取器模块

处理火车票和铁路电子客票的字段提取。
火车票具有特殊性：金额通常是票价，没有明确的购买方/销售方，日期是乘车日期。
"""

import re
import os
import time
from typing import Any, Dict
from .base import InvoiceExtractor


class TrainTicketExtractor(InvoiceExtractor):
    """
    火车票/铁路电子客票提取器

    火车票的特殊性：
    - 金额通常是票价
    - 没有明确的购买方/销售方
    - 日期是乘车日期
    - 可能有旅客/乘客信息

    Attributes:
        INVOICE_TYPE_KEYWORDS: 识别关键词
    """

    INVOICE_TYPE_KEYWORDS = ['火车票', '铁路电子客票', '列车票']

    TYPE_KEY = "train_ticket"

    def extract_amount(self) -> float:
        """
        提取票价

        提取策略：
        1. 匹配"票价:¥"或"票价:"字段（支持中间有空格）
        2. 匹配"金额:"字段
        3. 匹配¥/￥符号后的数字
        4. 匹配"票价"关键词后的金额

        Returns:
            float: 票价金额，失败返回0.0
        """
        # 策略1：匹配"票价: ¥ 496.00"格式（支持空格）
        pattern = r'票价[:：]?\s*[¥￥]?\s*(\d+(?:,\d{3})*(?:\.\d+)?)'
        match = re.search(pattern, self._text)
        if match:
            try:
                amount_str = match.group(1).replace(',', '')
                return float(amount_str)
            except ValueError:
                pass

        # 策略2：匹配"金额:"字段
        pattern = r'金额[:：]\s*(\d+(?:,\d{3})*(?:\.\d+)?)'
        match = re.search(pattern, self._text)
        if match:
            try:
                amount_str = match.group(1).replace(',', '')
                return float(amount_str)
            except ValueError:
                pass

        # 策略3：匹配¥/￥符号后的数字
        pattern = r'[¥￥]\s*(\d+(?:,\d{3})*(?:\.\d+)?)'
        match = re.search(pattern, self._text)
        if match:
            try:
                amount_str = match.group(1).replace(',', '')
                return float(amount_str)
            except ValueError:
                pass

        return 0.0

    def extract_invoice_date(self) -> str:
        """
        提取日期（乘车日期或开票日期）

        提取策略：
        1. 优先匹配乘车日期
        2. 匹配其他日期格式
        3. 返回文件修改日期作为备选

        Returns:
            str: 日期字符串，格式YYYY-MM-DD
        """
        # 优先匹配乘车日期
        patterns = [
            r'乘车日期[:：]\s*(\d{4})[-年](\d{1,2})[-月](\d{1,2})',
            r'日期[:：]\s*(\d{4})[-年](\d{1,2})[-月](\d{1,2})',
            r'(\d{4})[-年](\d{1,2})[-月](\d{1,2})',
        ]

        for pattern in patterns:
            match = re.search(pattern, self._text)
            if match:
                year, month, day = match.groups()
                return f"{year}-{month.zfill(2)}-{day.zfill(2)}"

        # 返回文件修改日期
        mod_time = os.path.getmtime(self.pdf_path)
        return time.strftime('%Y-%m-%d', time.localtime(mod_time))

    def extract_invoice_type(self) -> str:
        """
        返回票种类型

        Returns:
            str: "火车票"
        """
        return "火车票"

    def extract_product_type(self) -> str:
        """
        火车票没有商品类型

        Returns:
            str: 空字符串
        """
        return ""

    def extract_buyer_name(self) -> str:
        """
        提取旅客/乘客姓名

        火车票通常没有明确的购买方名称，尝试提取旅客姓名。
        铁路电子客票中，旅客信息格式为：身份证号 + 姓名

        Returns:
            str: 旅客姓名，无则返回空字符串
        """
        # 策略1：匹配身份证号（带星号隐藏）后的姓名
        pattern = r'\d{6}\*{4,8}\d{2,4}[\s\t]+([\u4e00-\u9fa5]{2,4})'
        match = re.search(pattern, self._text)
        if match:
            return match.group(1).strip()[:30]

        # 策略2：匹配身份证号后的姓名（铁路电子客票格式）
        # 格式：4105211990****2519    郭涛
        pattern = r'\d{6}(?:\d{4}|\*{4})\d{4}(?:\d{3}|\*{3})\d{1}[\s\t]+([\u4e00-\u9fa5]{2,4})'
        match = re.search(pattern, self._text)
        if match:
            return match.group(1).strip()[:30]

        # 策略3：尝试提取乘客姓名（传统格式）
        pattern = r'旅客[:：]\s*([^\n]+)'
        match = re.search(pattern, self._text)
        if match:
            return match.group(1).strip()[:30]

        # 策略4：尝试提取乘客姓名（其他格式）
        pattern = r'乘客[:：]\s*([^\n]+)'
        match = re.search(pattern, self._text)
        if match:
            return match.group(1).strip()[:30]

        return ""

    def extract_seller_name(self) -> str:
        return "中国铁路"

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

    def extract_tax_amount(self) -> float:
        """
        火车票没有税额

        Returns:
            float: 0.0
        """
        return 0.0

    def extract_extra_fields(self) -> Dict[str, Any]:
        """
        提取火车票特有字段：车次、出发站、到达站

        票面版式（铁路电子客票）：
            河源东站太湖南站G636
            HeyuandongTaihunan
        即「出发站 + 到达站 + 车次」在同一行连续出现。

        提取策略：
        1. 匹配「XX站XX站 + 车次号」的行内组合（最可靠）
        2. 分别按「车次:」标签匹配车次
        3. 分别按「出发站:」「到达站:」标签匹配站点

        Returns:
            Dict[str, Any]: train_number / departure_station / arrival_station
        """
        text = self._text or ""
        train_number = ""
        departure = ""
        arrival = ""

        # 策略1：出发站 + 车次 + 到达站（铁路电子客票典型排版）
        #   票面如「河源东站    G636    太湖南站」
        #   也兼容「河源东站太湖南站G636」这种连写
        match = re.search(
            r'([\u4e00-\u9fa5]{2,7}?站)\s*([GDCZTK]\d{1,4})\s*([\u4e00-\u9fa5]{2,7}?站)',
            text
        )
        if match:
            departure = match.group(1).strip()
            train_number = match.group(2).strip()
            arrival = match.group(3).strip()
        else:
            # 策略1b：站名连写 + 车次（如「河源东站太湖南站G636」）
            match = re.search(
                r'([\u4e00-\u9fa5]{2,7}?站)([\u4e00-\u9fa5]{2,7}?站)([GDCZTK]\d{1,4})',
                text
            )
            if match:
                departure = match.group(1).strip()
                arrival = match.group(2).strip()
                train_number = match.group(3).strip()
            else:
                # 策略2：仅站名连写，不带车次
                match = re.search(
                    r'([\u4e00-\u9fa5]{2,7}?站)\s*([\u4e00-\u9fa5]{2,7}?站)', text
                )
                if match:
                    departure = match.group(1).strip()
                    arrival = match.group(2).strip()

        # 补充：按标签匹配（覆盖带标签的版式）
        if not train_number:
            match = re.search(r'车\s*次[:：]\s*([GDCZTK]\d{1,4})', text)
            if match:
                train_number = match.group(1).strip()

        if not train_number:
            # 兜底：全文找车次号（字母 + 1~4 位数字）
            match = re.search(r'(?<![A-Za-z])([GDCZTK]\d{1,4})(?![0-9])', text)
            if match:
                train_number = match.group(1).strip()

        if not departure:
            match = re.search(r'出发站[:：]\s*([\u4e00-\u9fa5]{2,10}站?)', text)
            if match:
                departure = match.group(1).strip()

        if not arrival:
            match = re.search(r'到达站[:：]\s*([\u4e00-\u9fa5]{2,10}站?)', text)
            if match:
                arrival = match.group(1).strip()

        return {
            'train_number': train_number,
            'departure_station': departure,
            'arrival_station': arrival,
        }
