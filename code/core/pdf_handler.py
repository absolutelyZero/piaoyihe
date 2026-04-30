#!/usr/bin/env python3
"""
PDF处理核心功能

该模块提供PDF合并和发票字段提取功能。
发票字段提取采用策略模式，通过invoice_extractors模块实现。
"""

import fitz  # PyMuPDF
import os
import time
from .invoice_extractors.factory import InvoiceExtractorFactory


class PDFHandler:
    """
    PDF处理器类

    提供PDF合并和发票字段提取功能。
    发票字段提取通过工厂模式自动选择合适的提取器。

    Attributes:
        无实例属性
    """

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

            # 根据布局方向确定页面尺寸
            # 横向布局使用横向A4纸张，竖向布局使用纵向A4纸张
            is_landscape = layout_config['orientation'] == 'landscape'

            if is_landscape:
                page_width = 842  # A4横向宽度
                page_height = 595  # A4横向高度
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

                        # 使用较小的缩放比例以适应单元格
                        scale = min(scale_x, scale_y)

                        # 计算居中偏移
                        if rotate == 90:
                            scaled_width = src_rect.height * scale
                            scaled_height = src_rect.width * scale
                        else:
                            scaled_width = src_rect.width * scale
                            scaled_height = src_rect.height * scale

                        offset_x = (cell_width - scaled_width) / 2
                        offset_y = (cell_height - scaled_height) / 2

                        # 创建目标矩形（居中放置）
                        target_rect = fitz.Rect(
                            x + offset_x,
                            y + offset_y,
                            x + offset_x + scaled_width,
                            y + offset_y + scaled_height
                        )

                        # 显示页面到目标矩形
                        if mode == '图像':
                            # 图像模式：使用矩阵变换
                            if rotate == 90:
                                # 创建旋转矩阵
                                mat = fitz.Matrix(0, scale, -scale, 0, 0, 0)
                            else:
                                mat = fitz.Matrix(scale, 0, 0, scale, 0, 0)

                            # 使用show_pdf_page替代，更可靠
                            current_page.show_pdf_page(
                                target_rect,
                                doc,
                                i,
                                rotate=rotate
                            )
                        else:
                            # 普通模式：直接嵌入页面
                            current_page.show_pdf_page(
                                target_rect,
                                doc,
                                i,
                                rotate=rotate
                            )

                        page_count += 1

            # 保存输出文件
            output_doc.save(output_path)
            return True

        except Exception as e:
            print(f"合并PDF失败: {str(e)}")
            return False

        finally:
            # 确保关闭输出文档
            if output_doc:
                output_doc.close()

    def _draw_dividers(self, page, layout_config, margin, available_width, available_height):
        """
        绘制分割线

        Args:
            page: PDF页面对象
            layout_config: 布局配置
            margin: 页边距
            available_width: 可用宽度
            available_height: 可用高度
        """
        rows = layout_config['rows']
        cols = layout_config['cols']

        # 计算单元格尺寸
        cell_width = available_width / cols
        cell_height = available_height / rows

        # 绘制水平分割线
        for i in range(1, rows):
            y = margin + i * cell_height
            self._draw_dashed_line(
                page,
                margin, y,
                margin + available_width, y,
                dash_length=5,
                gap_length=3,
                color=(0.7, 0.7, 0.7),
                width=0.5
            )

        # 绘制垂直分割线
        for i in range(1, cols):
            x = margin + i * cell_width
            self._draw_dashed_line(
                page,
                x, margin,
                x, margin + available_height,
                dash_length=5,
                gap_length=3,
                color=(0.7, 0.7, 0.7),
                width=0.5
            )

    def _draw_dashed_line(self, page, x1, y1, x2, y2, dash_length=5, gap_length=3, color=(0, 0, 0), width=1):
        """
        绘制虚线

        Args:
            page: PDF页面对象
            x1: 起点x坐标
            y1: 起点y坐标
            x2: 终点x坐标
            y2: 终点y坐标
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
            # 新格式（不带空格）
            # 横向布局：A4纸横向，发票保持横向不旋转
            "横向2x2": {
                'orientation': 'landscape',  # A4纸横向
                'rows': 2,
                'cols': 2,
                'rotate': 0  # 发票不旋转
            },
            "横向2x4": {
                'orientation': 'landscape',  # A4纸横向
                'rows': 2,
                'cols': 4,
                'rotate': 0  # 发票不旋转
            },
            # 竖向布局：A4纸纵向，发票不旋转
            "竖向1x2": {
                'orientation': 'portrait',  # A4纸纵向
                'rows': 2,
                'cols': 1,
                'rotate': 0
            },
            "竖向1x3": {
                'orientation': 'portrait',  # A4纸纵向
                'rows': 3,
                'cols': 1,
                'rotate': 0
            },
            "竖向2x4": {
                'orientation': 'portrait',  # A4纸纵向
                'rows': 4,
                'cols': 2,
                'rotate': 0
            },
            # 旧格式（带空格，兼容旧配置）
            "横向 2x2": {
                'orientation': 'landscape',
                'rows': 2,
                'cols': 2,
                'rotate': 0
            },
            "横向 2x4": {
                'orientation': 'landscape',
                'rows': 2,
                'cols': 4,
                'rotate': 0
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

        return layout_map.get(layout, layout_map["横向2x2"])

    def extract_amount(self, pdf_path):
        """
        从PDF中提取金额

        通过工厂模式获取合适的提取器，调用其extract_amount方法

        Args:
            pdf_path: PDF文件路径

        Returns:
            float: 提取的金额，失败返回0.0
        """
        try:
            extractor = InvoiceExtractorFactory.get_extractor(pdf_path)
            if extractor:
                with extractor:
                    return extractor.extract_amount()
        except Exception as e:
            print(f"提取金额失败: {str(e)}")

        return 0.0

    def extract_invoice_date(self, pdf_path):
        """
        从PDF中提取开票日期

        通过工厂模式获取合适的提取器，调用其extract_invoice_date方法

        Args:
            pdf_path: PDF文件路径

        Returns:
            str: 提取的开票日期，格式为YYYY-MM-DD，失败返回文件修改日期
        """
        try:
            extractor = InvoiceExtractorFactory.get_extractor(pdf_path)
            if extractor:
                with extractor:
                    return extractor.extract_invoice_date()
        except Exception as e:
            print(f"提取开票日期失败: {str(e)}")

        # 返回文件修改日期作为备选
        mod_time = os.path.getmtime(pdf_path)
        return time.strftime('%Y-%m-%d', time.localtime(mod_time))

    def extract_invoice_type(self, pdf_path):
        """
        从PDF中提取发票类型

        通过工厂模式获取合适的提取器，调用其extract_invoice_type方法

        Args:
            pdf_path: PDF文件路径

        Returns:
            str: 提取的发票类型，失败返回"普票"
        """
        try:
            extractor = InvoiceExtractorFactory.get_extractor(pdf_path)
            if extractor:
                with extractor:
                    return extractor.extract_invoice_type()
        except Exception as e:
            print(f"提取发票类型失败: {str(e)}")

        return "普票"

    def extract_product_type(self, pdf_path):
        """
        从PDF中提取商品类型/服务名称

        通过工厂模式获取合适的提取器，调用其extract_product_type方法

        Args:
            pdf_path: PDF文件路径

        Returns:
            str: 提取的商品类型，失败返回"商品"
        """
        try:
            extractor = InvoiceExtractorFactory.get_extractor(pdf_path)
            if extractor:
                with extractor:
                    return extractor.extract_product_type()
        except Exception as e:
            print(f"提取商品类型失败: {str(e)}")

        return "商品"

    def extract_buyer_name(self, pdf_path):
        """
        从PDF中提取买方（购买方）名称

        通过工厂模式获取合适的提取器，调用其extract_buyer_name方法

        Args:
            pdf_path: PDF文件路径

        Returns:
            str: 提取的买方名称，失败返回"购买方"
        """
        try:
            extractor = InvoiceExtractorFactory.get_extractor(pdf_path)
            if extractor:
                with extractor:
                    return extractor.extract_buyer_name()
        except Exception as e:
            print(f"提取买方名称失败: {str(e)}")

        return "购买方"

    def extract_seller_name(self, pdf_path):
        """
        从PDF中提取销方（销售方）名称

        通过工厂模式获取合适的提取器，调用其extract_seller_name方法

        Args:
            pdf_path: PDF文件路径

        Returns:
            str: 提取的销售方名称，失败返回"销售方"
        """
        try:
            extractor = InvoiceExtractorFactory.get_extractor(pdf_path)
            if extractor:
                with extractor:
                    return extractor.extract_seller_name()
        except Exception as e:
            print(f"提取销方名称失败: {str(e)}")

        return "销售方"

    def extract_invoice_code(self, pdf_path):
        """
        从PDF中提取发票号码

        通过工厂模式获取合适的提取器，调用其extract_invoice_code方法

        Args:
            pdf_path: PDF文件路径

        Returns:
            str: 提取的发票号码，失败返回空字符串
        """
        try:
            extractor = InvoiceExtractorFactory.get_extractor(pdf_path)
            if extractor:
                with extractor:
                    return extractor.extract_invoice_code()
        except Exception as e:
            print(f"提取发票号码失败: {str(e)}")

        return ""

    def extract_all_invoice_info(self, pdf_path):
        """
        一次性提取所有发票信息

        通过工厂模式获取合适的提取器，调用其extract_all方法

        Args:
            pdf_path: PDF文件路径

        Returns:
            dict or None: 包含所有字段信息的字典，无法识别则返回None
                - amount: 金额
                - invoice_date: 开票日期
                - invoice_type: 发票类型
                - product_type: 商品类型
                - buyer_name: 购买方名称
                - seller_name: 销售方名称
        """
        try:
            extractor = InvoiceExtractorFactory.get_extractor(pdf_path)

            if extractor:
                with extractor:
                    return extractor.extract_all()
            else:
                # 无法识别该文件类型（可能是图片）
                return None
        except Exception as e:
            print(f"提取发票信息失败: {str(e)}")
            return None
