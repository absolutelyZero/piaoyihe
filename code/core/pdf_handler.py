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
            
            # 页边距设置（单位：点，1点=1/72英寸）
            margin = 20  # 页边距
            
            # 计算可用区域（扣除页边距）
            available_width = 595 - 2 * margin
            available_height = 842 - 2 * margin
            
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
                            
                            # 如果是多发票页面，绘制分割线
                            if layout_config['rows'] * layout_config['cols'] > 1:
                                self._draw_dividers(current_page, layout_config, margin, available_width, available_height)
                        
                        # 计算当前页面在新页中的位置
                        row = page_count // layout_config['cols']
                        col = page_count % layout_config['cols']
                        
                        # 计算每个单元格的尺寸（基于可用区域）
                        cell_width = available_width / layout_config['cols']
                        cell_height = available_height / layout_config['rows']
                        
                        # 计算位置（加上页边距偏移）
                        x = margin + col * cell_width
                        y = margin + row * cell_height
                        
                        # 获取源页面
                        src_page = doc[i]
                        
                        # 检查是否需要旋转
                        rotate = layout_config.get('rotate', 0)
                        
                        # 计算缩放比例（留出小间隙）
                        gap = 5  # 发票之间的间隙
                        src_rect = src_page.rect
                        
                        # 如果需要旋转90度，交换宽高进行缩放计算
                        if rotate == 90:
                            scale_x = (cell_width - gap) / src_rect.height
                            scale_y = (cell_height - gap) / src_rect.width
                        else:
                            scale_x = (cell_width - gap) / src_rect.width
                            scale_y = (cell_height - gap) / src_rect.height
                        
                        scale = min(scale_x, scale_y)  # 保持比例缩放
                        
                        # 计算最终尺寸
                        if rotate == 90:
                            scaled_width = src_rect.height * scale
                            scaled_height = src_rect.width * scale
                        else:
                            scaled_width = src_rect.width * scale
                            scaled_height = src_rect.height * scale
                        
                        # 计算最终位置（居中）
                        x += (cell_width - scaled_width) / 2
                        y += (cell_height - scaled_height) / 2
                        
                        # 插入页面（带旋转）
                        current_page.show_pdf_page(
                            fitz.Rect(x, y, x + scaled_width, y + scaled_height),
                            doc, i,
                            rotate=rotate
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
    
    def _draw_dividers(self, page, layout_config, margin, available_width, available_height):
        """
        绘制虚线分割线
        
        Args:
            page: PDF页面对象
            layout_config: 布局配置
            margin: 页边距
            available_width: 可用宽度
            available_height: 可用高度
        """
        # 虚线参数
        dash_length = 5    # 实线段长度
        gap_length = 3     # 空白段长度
        line_color = (0.6, 0.6, 0.6)  # 浅灰色
        line_width = 0.5
        
        # 计算单元格尺寸
        cell_width = available_width / layout_config['cols']
        cell_height = available_height / layout_config['rows']
        
        # 绘制垂直分割线
        for col in range(1, layout_config['cols']):
            x = margin + col * cell_width
            y_start = margin
            y_end = margin + available_height
            self._draw_dashed_line(page, x, y_start, x, y_end, dash_length, gap_length, line_color, line_width)
        
        # 绘制水平分割线
        for row in range(1, layout_config['rows']):
            y = margin + row * cell_height
            x_start = margin
            x_end = margin + available_width
            self._draw_dashed_line(page, x_start, y, x_end, y, dash_length, gap_length, line_color, line_width)
    
    def _draw_dashed_line(self, page, x1, y1, x2, y2, dash_length, gap_length, color, width):
        """
        绘制单条虚线
        
        Args:
            page: PDF页面对象
            x1, y1: 起点坐标
            x2, y2: 终点坐标
            dash_length: 实线段长度
            gap_length: 空白段长度
            color: 线条颜色
            width: 线条宽度
        """
        import math
        
        # 计算线段总长度和方向
        dx = x2 - x1
        dy = y2 - y1
        total_length = math.sqrt(dx * dx + dy * dy)
        
        if total_length == 0:
            return
        
        # 归一化方向向量
        ux = dx / total_length
        uy = dy / total_length
        
        # 交替绘制实线和空白
        current = 0
        is_dash = True
        
        while current < total_length:
            if is_dash:
                # 绘制实线段
                seg_start = current
                seg_end = min(current + dash_length, total_length)
                page.draw_line(
                    fitz.Point(x1 + ux * seg_start, y1 + uy * seg_start),
                    fitz.Point(x1 + ux * seg_end, y1 + uy * seg_end),
                    color=color,
                    width=width
                )
                current = seg_end
            else:
                # 跳过空白段
                current = min(current + gap_length, total_length)
            
            is_dash = not is_dash
    
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
                'cols': 2,
                'rotate': 90  # 每张发票旋转90度
            },
            "竖向 1x2": {
                'orientation': 'portrait',
                'rows': 2,
                'cols': 1,
                'rotate': 0
            },
            "竖向 1x3": {
                'orientation': 'portrait',
                'rows': 3,
                'cols': 1,
                'rotate': 0
            },
            "竖向 2x4": {
                'orientation': 'portrait',
                'rows': 4,
                'cols': 2,
                'rotate': 0
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
    
    def extract_invoice_date(self, pdf_path):
        """
        从PDF中提取开票日期
        
        Args:
            pdf_path: PDF文件路径
            
        Returns:
            str: 提取的开票日期，格式为YYYY-MM-DD
        """
        import re
        
        try:
            # 打开PDF文件
            with fitz.open(pdf_path) as doc:
                # 遍历所有页面
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    text = page.get_text()
                    
                    # 优先匹配"开票日期:"后面的日期
                    invoice_date_pattern = r'开票日期[:：]\s*(\d{4})年(\d{1,2})月(\d{1,2})日?'
                    match = re.search(invoice_date_pattern, text)
                    if match:
                        year, month, day = match.groups()
                        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                    
                    # 如果没有找到"开票日期:"，再匹配其他日期格式
                    # 匹配YYYY年MM月DD日格式
                    date_patterns = [
                        r'(\d{4})年(\d{1,2})月(\d{1,2})日',  # YYYY年MM月DD日
                        r'(\d{4})年(\d{1,2})月(\d{1,2})',    # YYYY年MM月DD
                        r'(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})',  # YYYY-MM-DD, YYYY/MM/DD
                    ]
                    
                    for pattern in date_patterns:
                        matches = re.findall(pattern, text)
                        for match in matches:
                            if len(match) == 3:
                                year, month, day = match
                                # 验证日期范围
                                if 1 <= int(month) <= 12 and 1 <= int(day) <= 31:
                                    return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                
                # 如果没有找到开票日期，返回文件修改日期
                import os
                import time
                mod_time = os.path.getmtime(pdf_path)
                return time.strftime('%Y-%m-%d', time.localtime(mod_time))
                
        except Exception as e:
            print(f"提取开票日期失败: {str(e)}")
            # 返回文件修改日期作为备选
            import os
            import time
            mod_time = os.path.getmtime(pdf_path)
            return time.strftime('%Y-%m-%d', time.localtime(mod_time))
