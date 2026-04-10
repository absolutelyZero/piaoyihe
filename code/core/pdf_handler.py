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
    
    def merge_pdfs(self, pdf_paths, output_path, layout, mode='普通'):
        """
        合并PDF文件并按指定布局排版
        
        Args:
            pdf_paths: PDF文件路径列表
            output_path: 输出文件路径
            layout: 布局类型，如"横向 2x2"
            mode: 模式，可选值：'普通'、'图像'
        
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
            
            # 根据模式和布局确定页面尺寸
            # 图像模式下2x2布局使用横向纸张
            is_landscape = (mode == '图像' and layout_config['rows'] == 2 and layout_config['cols'] == 2)
            
            if is_landscape:
                page_width = 842  # A4横向宽度
                page_height = 595  # A4横向高度
                # 横向纸张不需要再旋转内容
                layout_config['rotate'] = 0
            else:
                page_width = 595  # A4纵向宽度
                page_height = 842  # A4纵向高度
            
            # 计算可用区域（扣除页边距）
            available_width = page_width - 2 * margin
            available_height = page_height - 2 * margin
            
            # 处理每个PDF文件
            current_page = None
            page_count = 0
            
            for pdf_path in pdf_paths:
                # 打开PDF文件
                with fitz.open(pdf_path) as doc:
                    for i in range(len(doc)):
                        # 检查是否需要创建新页
                        if page_count % (layout_config['rows'] * layout_config['cols']) == 0:
                            # 创建新页（根据方向设置尺寸）
                            current_page = output_doc.new_page(width=page_width, height=page_height)
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
                        
                        # 检查是否需要旋转
                        rotate = layout_config.get('rotate', 0)
                        
                        # 获取源页面
                        src_page = doc[i]
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
                        
                        # 计算居中位置（基于单元格起始位置）
                        center_x = x + (cell_width - scaled_width) / 2
                        center_y = y + (cell_height - scaled_height) / 2
                        
                        # 根据模式选择插入方式
                        if mode == '普通':
                            # 普通模式：直接插入PDF页面
                            current_page.show_pdf_page(
                                fitz.Rect(center_x, center_y, center_x + scaled_width, center_y + scaled_height),
                                doc, i,
                                rotate=rotate
                            )
                            
                            # 额外复制注释对象（包括监制章）
                            src_page = doc[i]
                            annotations = list(src_page.annots()) if src_page.annots() else []
                            print(f"找到 {len(annotations)} 个注释对象")
                            for annot_idx, annot in enumerate(annotations):
                                try:
                                    print(f"  注释 {annot_idx + 1}: 类型={annot.type}, 位置={annot.rect}")
                                    
                                    # 只处理Stamp类型的注释（监制章）
                                    if annot.type[0] != 13:  # 13对应Stamp类型
                                        print(f"  跳过非Stamp类型注释")
                                        continue
                                    
                                    # 方案B：将注释渲染为图片插入（最可靠）
                                    # 直接渲染注释区域为图片
                                    pix = src_page.get_pixmap(dpi=450, clip=annot.rect)
                                    
                                    # 处理90度旋转
                                    if rotate == 90:
                                        # 先旋转图片
                                        from PIL import Image
                                        import io
                                        # 将pixmap转换为PIL Image
                                        img_data = pix.tobytes("png")
                                        pil_img = Image.open(io.BytesIO(img_data))
                                        # 旋转90度（逆时针）
                                        pil_img = pil_img.rotate(90, expand=True)
                                        # 转换回bytes
                                        img_buffer = io.BytesIO()
                                        pil_img.save(img_buffer, format='PNG')
                                        img_buffer.seek(0)
                                        # 创建新的pixmap
                                        pix = fitz.Pixmap(img_buffer)
                                        
                                        # 计算旋转后的坐标（逆时针旋转90度）
                                        # 原始坐标：(x0,y0) -> (y0, src_rect.width - x1)
                                        new_x0 = center_x + (annot.rect.y0) * scale
                                        new_y0 = center_y + (src_rect.width - annot.rect.x1) * scale
                                        new_x1 = center_x + (annot.rect.y1) * scale
                                        new_y1 = center_y + (src_rect.width - annot.rect.x0) * scale
                                        new_rect = fitz.Rect(new_x0, new_y0, new_x1, new_y1)
                                    else:
                                        # 调整注释位置以匹配缩放
                                        new_x0 = center_x + annot.rect.x0 * scale
                                        new_y0 = center_y + annot.rect.y0 * scale
                                        new_x1 = center_x + annot.rect.x1 * scale
                                        new_y1 = center_y + annot.rect.y1 * scale
                                        new_rect = fitz.Rect(new_x0, new_y0, new_x1, new_y1)
                                    
                                    print(f"  调整后位置: {new_rect}")
                                    # 插入渲染后的图片
                                    current_page.insert_image(new_rect, pixmap=pix)
                                    print(f"  成功将注释渲染为图片插入")
                                    
                                except Exception as e:
                                    print(f"处理注释失败: {str(e)}")
                        else:
                            # 图像模式：先转换为图片再插入
                            src_page = doc[i]
                            # 渲染页面为图片（高分辨率）
                            pix = src_page.get_pixmap(dpi=150)
                            
                            # 如果需要旋转90度，创建旋转后的图片
                            if rotate == 90:
                                # 使用Pixmap的旋转方法（创建新的旋转后的pixmap）
                                from PIL import Image
                                import io
                                
                                # 将pixmap转换为PIL Image
                                img_data = pix.tobytes("png")
                                pil_img = Image.open(io.BytesIO(img_data))
                                # 旋转90度（逆时针）
                                pil_img = pil_img.rotate(90, expand=True)
                                # 转换回bytes
                                img_buffer = io.BytesIO()
                                pil_img.save(img_buffer, format='PNG')
                                img_buffer.seek(0)
                                # 创建新的pixmap
                                pix = fitz.Pixmap(img_buffer)
                            
                            img_width = pix.width
                            img_height = pix.height
                            
                            scale_x = (cell_width - gap) / img_width
                            scale_y = (cell_height - gap) / img_height
                            scale = min(scale_x, scale_y)
                            
                            final_width = img_width * scale
                            final_height = img_height * scale
                            
                            # 计算居中位置（与普通模式保持一致）
                            img_x = center_x + (scaled_width - final_width) / 2
                            img_y = center_y + (scaled_height - final_height) / 2
                            
                            # 创建图像矩形
                            img_rect = fitz.Rect(img_x, img_y, img_x + final_width, img_y + final_height)
                            
                            # 插入图像
                            current_page.insert_image(img_rect, pixmap=pix)
                        
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
