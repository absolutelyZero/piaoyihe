#!/usr/bin/env python3
"""
PDF处理核心功能
"""

import fitz  # PyMuPDF
import os

class PDFHandler:
    """PDF处理器类"""
    
    def __init__(self):
        """初始化PDF处理器"""
        pass
    
    def merge_pdfs(self, pdf_paths, output_path, layout):
        """
        合并PDF文件并按指定布局排版
        
        Args:
            pdf_paths: PDF文件路径列表
            output_path: 输出文件路径
            layout: 布局类型，如"横向 2x2"
        
        Returns:
            bool: 合并是否成功
        """
        # 创建新的PDF文档
        output_doc = fitz.open()
        
        try:
            # 解析布局
            layout_config = self._parse_layout(layout)
            
            # 处理每个PDF文件
            current_page = None
            page_count = 0
            
            for pdf_path in pdf_paths:
                # 打开PDF文件
                with fitz.open(pdf_path) as doc:
                    for i in range(len(doc)):
                        # 检查是否需要创建新页
                        if page_count % (layout_config['rows'] * layout_config['cols']) == 0:
                            # 创建新页（A4尺寸）
                            current_page = output_doc.new_page(width=595, height=842)  # A4尺寸
                            page_count = 0
                        
                        # 计算当前页面在新页中的位置
                        row = page_count // layout_config['cols']
                        col = page_count % layout_config['cols']
                        
                        # 计算缩放和位置
                        if layout_config['orientation'] == 'landscape':
                            # 横向布局
                            page_width = 595 / layout_config['cols']
                            page_height = 842 / layout_config['rows']
                            x = col * page_width
                            y = row * page_height
                        else:
                            # 竖向布局
                            page_width = 595 / layout_config['cols']
                            page_height = 842 / layout_config['rows']
                            x = col * page_width
                            y = row * page_height
                        
                        # 获取源页面
                        src_page = doc[i]
                        
                        # 计算缩放比例
                        src_rect = src_page.rect
                        scale_x = page_width / src_rect.width
                        scale_y = page_height / src_rect.height
                        scale = min(scale_x, scale_y)  # 保持比例缩放
                        
                        # 计算最终位置（居中）
                        scaled_width = src_rect.width * scale
                        scaled_height = src_rect.height * scale
                        x += (page_width - scaled_width) / 2
                        y += (page_height - scaled_height) / 2
                        
                        # 插入页面
                        current_page.show_pdf_page(
                            fitz.Rect(x, y, x + scaled_width, y + scaled_height),
                            doc, i
                        )
                        
                        page_count += 1
            
            # 保存输出文件
            output_doc.save(output_path)
            output_doc.close()
            
            return True
            
        except Exception as e:
            print(f"合并PDF失败: {str(e)}")
            output_doc.close()
            raise
    
    def _parse_layout(self, layout):
        """
        解析布局配置
        
        Args:
            layout: 布局类型字符串
            
        Returns:
            dict: 布局配置
        """
        layout_map = {
            "横向 2x2": {
                'orientation': 'landscape',
                'rows': 2,
                'cols': 2
            },
            "竖向 1x2": {
                'orientation': 'portrait',
                'rows': 2,
                'cols': 1
            },
            "竖向 1x3": {
                'orientation': 'portrait',
                'rows': 3,
                'cols': 1
            },
            "竖向 2x4": {
                'orientation': 'portrait',
                'rows': 4,
                'cols': 2
            }
        }
        
        return layout_map.get(layout, layout_map["横向 2x2"])
    
    def extract_amount(self, pdf_path):
        """
        从PDF中提取金额
        
        Args:
            pdf_path: PDF文件路径
            
        Returns:
            float: 提取的金额
        """
        import re
        
        try:
            # 打开PDF文件
            with fitz.open(pdf_path) as doc:
                amount_max = 0.0
                
                # 遍历所有页面
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    # 提取带坐标信息的文本块
                    blocks = page.get_text("blocks")
                    
                    # 定义可能表示金额的关键词
                    amount_keywords = ["价税合计", "合计", "金额", "¥", "￥", "小写", "票价", "金额", "总额", "总金额"]
                    
                    # 遍历文本块，寻找关键词及附近的金额
                    for block in blocks:
                        x0, y0, x1, y1, text, block_no, block_type = block
                        text_clean = text.replace(' ', '').strip()  # 去除空格
                        
                        # 检查当前文本块是否包含关键词
                        for keyword in amount_keywords:
                            if keyword in text_clean:
                                # 策略：关键词和金额在同一文本块内
                                # 使用正则表达式直接在当前文本块中查找金额数字
                                # 支持任意位数小数，支持千分位和不同小数分隔符
                                pattern = r'[¥￥]?\s*(\d+(?:,\d{3})*(?:[.·]\d+)?)'  # 匹配任意长度数字，支持千分位和任意位数小数
                                match = re.search(pattern, text_clean)
                                if match:
                                    amount_str = match.group(1).replace(',', '').replace('·', '.')  # 去除千分位逗号，将间隔点替换为小数点
                                    try:
                                        amount = float(amount_str)
                                        if amount > amount_max:
                                            amount_max = amount
                                    except ValueError:
                                        pass
                    
                    # 额外策略：如果没有找到关键词，直接在整个页面中查找金额格式
                    if amount_max == 0:
                        text = page.get_text()
                        # 匹配各种金额格式
                        patterns = [
                            r'¥\s*(\d+(?:,\d{3})*(?:[.·]\d+)?)',  # ¥123,456.78
                            r'￥\s*(\d+(?:,\d{3})*(?:[.·]\d+)?)',  # ￥123,456.78
                            r'(\d+(?:,\d{3})*(?:[.·]\d+)?)\s*元',  # 123,456.78元
                            r'票价[:：]\s*(\d+(?:,\d{3})*(?:[.·]\d+)?)',  # 票价：123,456.78
                        ]
                        
                        for pattern in patterns:
                            matches = re.findall(pattern, text)
                            for match in matches:
                                try:
                                    amount_str = match.replace(',', '').replace('·', '.')
                                    amount = float(amount_str)
                                    if amount > amount_max:
                                        amount_max = amount
                                except ValueError:
                                    pass
                
                return amount_max
                
        except Exception as e:
            print(f"提取金额失败: {str(e)}")
            return 0.0
