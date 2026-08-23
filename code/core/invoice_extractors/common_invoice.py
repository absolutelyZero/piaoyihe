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
        company_keywords = ['公司', '企业', '股份', '有限', '集团', '厂', '店', '中心', '工作室', '部']
        for buyer in matches:
            buyer = buyer.strip().replace('\n', '').replace(' ', '')
            if len(buyer) > 4 and any(keyword in buyer for keyword in company_keywords):
                return buyer[:30]

        # 策略3：查找第一个公司名称
        company_pattern = r'([\u4e00-\u9fa5a-zA-Z0-9（）()]*(?:公司|企业|股份|有限|集团|厂|店|中心|工作室|部)[\u4e00-\u9fa5a-zA-Z0-9（）()]*)'
        matches = re.findall(company_pattern, self._text)
        for buyer in matches:
            buyer = buyer.strip().replace('\n', '').replace(' ', '')
            if len(buyer) > 4:
                return buyer[:30]

        return "购买方"

    def _extract_name_by_layout(self, is_seller: bool) -> str:
        """
        基于 fitz 词坐标按页面分栏提取买方或卖方名称

        某些 PDF 发票的文本绘制顺序与视觉阅读顺序不一致，导致
        get_text("block") 提取的左右分栏内容顺序错乱。本方法使用
        page.get_text("words") 获取每个词的坐标，按 x 坐标将页面
        分为左右两栏，再分别提取买卖双方名称。

        Args:
            is_seller: True 表示提取销售方名称，False 表示提取购买方名称

        Returns:
            str: 提取到的名称，失败返回空字符串
        """
        if not hasattr(self, '_words') or not self._words:
            self._words = [page.get_text("words") for page in self._pages]

        seller_labels = ['销', '售方', '销售方']
        buyer_labels = ['购', '买方', '购买方']
        company_pattern = r'([\u4e00-\u9fa5a-zA-Z0-9（）()]*(?:公司|企业|股份|有限|集团|厂|店|中心|工作室|部)[\u4e00-\u9fa5a-zA-Z0-9（）()]*)'

        for words in self._words:
            if not words:
                continue

            # 计算页面左右分栏的中线
            xs = [w[0] for w in words] + [w[2] for w in words]
            min_x, max_x = min(xs), max(xs)
            mid_x = (min_x + max_x) / 2

            # 按 x 坐标分为左右两栏（使用中心点判断，避免跨中线字符被遗漏）
            left_words = [w for w in words if (w[0] + w[2]) / 2 < mid_x]
            right_words = [w for w in words if (w[0] + w[2]) / 2 > mid_x]
            left_text = ' '.join([w[4] for w in sorted(left_words, key=lambda w: (w[1], w[0]))])
            right_text = ' '.join([w[4] for w in sorted(right_words, key=lambda w: (w[1], w[0]))])

            # 为避免备注区域（如"销方开户银行"）中的字符干扰标签检测，
            # 只使用页面上半部分（y < 200）的词汇来判断买卖方分栏
            top_words = [w for w in words if w[1] < 200]
            top_left_words = [w for w in top_words if (w[0] + w[2]) / 2 < mid_x]
            top_right_words = [w for w in top_words if (w[0] + w[2]) / 2 > mid_x]
            top_left_text = ' '.join([w[4] for w in sorted(top_left_words, key=lambda w: (w[1], w[0]))])
            top_right_text = ' '.join([w[4] for w in sorted(top_right_words, key=lambda w: (w[1], w[0]))])

            # 根据标签判断哪边是销售方、哪边是购买方
            seller_in_left = any(label in top_left_text for label in seller_labels)
            seller_in_right = any(label in top_right_text for label in seller_labels)
            buyer_in_left = any(label in top_left_text for label in buyer_labels)
            buyer_in_right = any(label in top_right_text for label in buyer_labels)

            if seller_in_left and not seller_in_right:
                seller_text, buyer_text = left_text, right_text
            elif seller_in_right and not seller_in_left:
                seller_text, buyer_text = right_text, left_text
            elif buyer_in_left and not buyer_in_right:
                seller_text, buyer_text = right_text, left_text
            elif buyer_in_right and not buyer_in_left:
                seller_text, buyer_text = left_text, right_text
            else:
                # 标签在两边都存在或都不存在，默认左侧为销售方
                seller_text, buyer_text = left_text, right_text

            target_text = seller_text if is_seller else buyer_text

            # 在目标栏中提取公司名称
            matches = re.findall(company_pattern, target_text)
            for match in matches:
                company = match.strip().replace(' ', '').replace('\n', '')
                if len(company) > 4:
                    return company[:30]

        return ""

    def extract_seller_name(self) -> str:
        """
        提取销售方名称

        提取策略（按优先级）：
        1. 基于 fitz 坐标按页面分栏提取
        2. 匹配"销售方信息"区域内的"名称:"
        3. 查找第二个"名称:"（第一个是购买方）
        4. 查找最后一个公司名称

        Returns:
            str: 销售方名称
        """
        # 打印原始文本
        print("原始文本:")
        print(self._text)

        # 策略1：基于 fitz 词坐标按页面分栏提取
        seller = self._extract_name_by_layout(is_seller=True)
        if seller:
            return seller

        # 策略2：匹配"销售方信息"区域
        seller_pattern = r'销[售\n]*方[\n\s]*信[\n\s]*息[\n\s]*.*?名[\n\s]*称[：:]\s*([\u4e00-\u9fa5a-zA-Z0-9（）()]+)'
        match = re.search(seller_pattern, self._text, re.DOTALL)
        if match:
            seller = match.group(1).strip().replace('\n', '').replace(' ', '')
            if len(seller) > 4:
                return seller[:30]

        # 策略2：查找第二个"名称:"
        name_pattern = r'名[\n\s]*称[：:]\s*([\u4e00-\u9fa5a-zA-Z0-9（）()]+)'
        matches = re.findall(name_pattern, self._text)
        company_keywords = ['公司', '企业', '股份', '有限', '集团', '厂', '店', '中心', '工作室', '部']
        if len(matches) >= 2:
            seller = matches[1].strip().replace('\n', '').replace(' ', '')
            if len(seller) > 4 and any(keyword in seller for keyword in company_keywords):
                return seller[:30]

        # 策略3：查找最后一个公司名称
        company_pattern = r'([\u4e00-\u9fa5a-zA-Z0-9（）()]*(?:公司|企业|股份|有限|集团|厂|店|中心|工作室|部)[\u4e00-\u9fa5a-zA-Z0-9（）()]*)'
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

    def extract_tax_amount(self) -> float:
        """
        提取税额

        提取策略（按优先级）：
        1. 匹配税率+税额相邻格式（如 13% 20.59）
        2. 匹配合计行中的税额（如 合计 ¥149.53 ¥19.43）
        3. 匹配"税 额"关键词附近的金额
        4. 匹配"合计税额"字段
        5. 返回0.0

        Returns:
            float: 提取的税额，无则返回0.0
        """
        total_amount = self.extract_amount()

        # 策略1：匹配合计行中的税额（最可靠，优先使用）
        # 如：合    计    ¥149.53    ¥19.43
        total_pattern = r'合\s*计.*?[¥￥]\s*(?:-?\d+(?:,\d{3})*(?:\.\d+)?).*?[¥￥]\s*(-?\d+(?:,\d{3})*(?:\.\d+)?)'
        match = re.search(total_pattern, self._text, re.DOTALL)
        if match:
            try:
                return float(match.group(1).replace(',', ''))
            except ValueError:
                pass

        # 策略2：匹配税率+税额相邻格式（表格行中的税额）
        # 如：158.41       13%                  20.59
        tax_rate_patterns = [
            r'(?:-?\d+(?:,\d{3})*(?:\.\d+)?)\s+(\d+(?:\.\d+)?)%\s+(?:CNY\s+)?[¥￥]?\s*(-?\d+(?:,\d{3})*(?:\.\d+)?)',
            r'(\d+(?:\.\d+)?)%\s+(?:CNY\s+)?[¥￥]?\s*(-?\d+(?:,\d{3})*(?:\.\d+)?)',
        ]
        tax_values = set()
        for tax_rate_pattern in tax_rate_patterns:
            matches = re.findall(tax_rate_pattern, self._text)
            for rate_str, tax_str in matches:
                try:
                    tax = float(tax_str.replace(',', ''))
                    # 合理性校验：税额通常小于价税合计
                    if total_amount > 0 and abs(tax) < total_amount:
                        tax_values.add(tax)
                    elif total_amount == 0:
                        tax_values.add(tax)
                except ValueError:
                    pass
        if tax_values:
            # 返回所有税额的合计（支持多行发票和折扣行自动抵消）
            return sum(tax_values)

        # 策略3：匹配"税 额"关键词附近的金额（支持空格）
        if re.search(r'税\s*额', self._text):
            pattern = r'税\s*额[:：]?\s*[¥￥]?\s*(-?\d+(?:,\d{3})*(?:\.\d+)?)'
            matches = re.findall(pattern, self._text)
            for match in matches:
                try:
                    amount = float(match.replace(',', ''))
                    # 过滤掉过大的金额（避免匹配价税合计）
                    if total_amount > 0 and abs(amount) < total_amount * 0.5:
                        return amount
                    elif total_amount == 0:
                        return amount
                except ValueError:
                    pass

        # 策略4：匹配"合计税额"字段
        tax_patterns = [
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
