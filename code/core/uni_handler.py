#!/usr/bin/env python3
"""
统一文档处理器模块 (UniHandler)

这是UI层与核心处理层的唯一交互接口。
提供统一的文档处理接口，自动识别PDF和OFD格式，
调用相应的底层处理器进行处理。

设计原则：
1. UI层只与此模块交互，不直接调用pdf_handler或ofd_handler
2. 所有文件格式差异在此层透明化处理
3. 提供一致的API接口，无论底层是PDF还是OFD
4. 管理临时文件生命周期，确保资源正确释放

使用示例：
    from core.uni_handler import UniHandler
    
    handler = UniHandler()
    
    # 提取字段 - 自动识别文件类型
    amount = handler.extract_amount('invoice.pdf')  # PDF
    amount = handler.extract_amount('invoice.ofd')  # OFD
    
    # 合并文档 - 支持PDF和OFD混合
    handler.merge_documents(['a.pdf', 'b.ofd', 'c.pdf'], 'output.pdf', layout)
    
    # 获取预览
    pixmap = handler.get_preview_pixmap('invoice.ofd')
"""

import os
import tempfile
from typing import List, Optional, Dict, Any, Union
from .pdf_handler import PDFHandler
from .ofd_handler import OFDHandler


class UniHandler:
    """
    统一文档处理器类

    这是UI层与核心处理层的统一接口，对外提供一致的文档处理能力，
    内部自动处理PDF和OFD格式的差异。

    Attributes:
        _pdf_handler: PDF处理器实例（私有）
        _ofd_handler: OFD处理器实例（私有）
        _temp_files: 临时文件列表（用于OFD转PDF）
    """

    def __init__(self):
        """初始化统一文档处理器"""
        self._pdf_handler = PDFHandler()
        self._ofd_handler = OFDHandler()
        self._temp_files: List[str] = []

    def __del__(self):
        """析构时清理所有临时文件"""
        self._cleanup_temp_files()

    def _cleanup_temp_files(self):
        """
        清理所有临时文件
        
        在合并操作或预览完成后自动调用，确保不残留临时PDF文件
        """
        for temp_file in self._temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    print(f"[UniHandler] 清理临时文件: {temp_file}")
            except Exception as e:
                print(f"[UniHandler] 清理临时文件失败: {temp_file}, {e}")
        self._temp_files.clear()

    @staticmethod
    def _is_ofd(file_path: str) -> bool:
        """
        判断文件是否为OFD格式
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 是否为OFD文件
        """
        return file_path.lower().endswith('.ofd')

    @staticmethod
    def _is_pdf(file_path: str) -> bool:
        """
        判断文件是否为PDF格式
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 是否为PDF文件
        """
        return file_path.lower().endswith('.pdf')

    def _convert_ofd_to_pdf(self, ofd_path: str) -> str:
        """
        将OFD转换为临时PDF文件
        
        用于合并或预览操作，转换后的临时文件会被记录以便后续清理
        
        Args:
            ofd_path: OFD文件路径
            
        Returns:
            str: 临时PDF文件路径
            
        Raises:
            Exception: 转换失败时抛出异常
        """
        try:
            temp_pdf = self._ofd_handler.convert_to_pdf(ofd_path)
            self._temp_files.append(temp_pdf)
            print(f"[UniHandler] OFD转PDF成功: {ofd_path} -> {temp_pdf}")
            return temp_pdf
        except Exception as e:
            print(f"[UniHandler] OFD转PDF失败: {ofd_path}, 错误: {e}")
            raise

    # ========================================================================
    # 字段提取接口 - 自动识别文件类型
    # ========================================================================

    def extract_amount(self, file_path: str) -> float:
        """
        提取发票金额
        
        自动识别PDF或OFD格式，调用对应的提取器
        
        Args:
            file_path: 发票文件路径（.pdf 或 .ofd）
            
        Returns:
            float: 提取的金额，失败返回0.0
        """
        try:
            if self._is_ofd(file_path):
                return self._ofd_handler.extract_amount(file_path)
            return self._pdf_handler.extract_amount(file_path)
        except Exception as e:
            print(f"[UniHandler] 提取金额失败: {file_path}, {e}")
            return 0.0

    def extract_invoice_date(self, file_path: str) -> str:
        """
        提取开票日期
        
        Args:
            file_path: 发票文件路径
            
        Returns:
            str: 日期字符串，格式YYYY-MM-DD，失败返回文件修改日期
        """
        try:
            if self._is_ofd(file_path):
                return self._ofd_handler.extract_invoice_date(file_path)
            return self._pdf_handler.extract_invoice_date(file_path)
        except Exception as e:
            print(f"[UniHandler] 提取开票日期失败: {file_path}, {e}")
            # 返回文件修改日期作为备选
            try:
                mod_time = os.path.getmtime(file_path)
                from time import strftime, localtime
                return strftime('%Y-%m-%d', localtime(mod_time))
            except Exception:
                from time import strftime, localtime
                return strftime('%Y-%m-%d', localtime())

    def extract_invoice_type(self, file_path: str) -> str:
        """
        提取发票类型
        
        Args:
            file_path: 发票文件路径
            
        Returns:
            str: 发票类型，如"普票"、"专票"、"火车票"等
        """
        try:
            if self._is_ofd(file_path):
                return self._ofd_handler.extract_invoice_type(file_path)
            return self._pdf_handler.extract_invoice_type(file_path)
        except Exception as e:
            print(f"[UniHandler] 提取发票类型失败: {file_path}, {e}")
            return "普票"

    def extract_product_type(self, file_path: str) -> str:
        """
        提取商品类型/服务名称
        
        Args:
            file_path: 发票文件路径
            
        Returns:
            str: 商品或服务名称
        """
        try:
            if self._is_ofd(file_path):
                return self._ofd_handler.extract_product_type(file_path)
            return self._pdf_handler.extract_product_type(file_path)
        except Exception as e:
            print(f"[UniHandler] 提取商品类型失败: {file_path}, {e}")
            return "商品"

    def extract_buyer_name(self, file_path: str) -> str:
        """
        提取购买方名称
        
        Args:
            file_path: 发票文件路径
            
        Returns:
            str: 购买方名称
        """
        try:
            if self._is_ofd(file_path):
                return self._ofd_handler.extract_buyer_name(file_path)
            return self._pdf_handler.extract_buyer_name(file_path)
        except Exception as e:
            print(f"[UniHandler] 提取购买方名称失败: {file_path}, {e}")
            return "购买方"

    def extract_seller_name(self, file_path: str) -> str:
        """
        提取销售方名称
        
        Args:
            file_path: 发票文件路径
            
        Returns:
            str: 销售方名称
        """
        try:
            if self._is_ofd(file_path):
                return self._ofd_handler.extract_seller_name(file_path)
            return self._pdf_handler.extract_seller_name(file_path)
        except Exception as e:
            print(f"[UniHandler] 提取销售方名称失败: {file_path}, {e}")
            return "销售方"

    def extract_invoice_code(self, file_path: str) -> str:
        """
        提取发票号码
        
        Args:
            file_path: 发票文件路径
            
        Returns:
            str: 发票号码，失败返回空字符串
        """
        try:
            if self._is_ofd(file_path):
                return self._ofd_handler.extract_invoice_code(file_path)
            return self._pdf_handler.extract_invoice_code(file_path)
        except Exception as e:
            print(f"[UniHandler] 提取发票号码失败: {file_path}, {e}")
            return ""

    def extract_tax_amount(self, file_path: str) -> float:
        """
        提取税额
        
        Args:
            file_path: 发票文件路径
            
        Returns:
            float: 提取的税额，失败返回0.0
        """
        try:
            if self._is_ofd(file_path):
                return self._ofd_handler.extract_tax_amount(file_path)
            return self._pdf_handler.extract_tax_amount(file_path)
        except Exception as e:
            print(f"[UniHandler] 提取税额失败: {file_path}, {e}")
            return 0.0

    def extract_all_invoice_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        一次性提取所有发票信息
        
        Args:
            file_path: 发票文件路径
            
        Returns:
            dict or None: 包含所有字段的字典，失败返回None
                - amount: 金额
                - invoice_date: 开票日期
                - invoice_type: 发票类型
                - product_type: 商品类型
                - buyer_name: 购买方名称
                - seller_name: 销售方名称
                - invoice_code: 发票号码
                - tax_amount: 税额
        """
        try:
            if self._is_ofd(file_path):
                return self._ofd_handler.extract_all_invoice_info(file_path)
            return self._pdf_handler.extract_all_invoice_info(file_path)
        except Exception as e:
            print(f"[UniHandler] 提取发票信息失败: {file_path}, {e}")
            return None

    # ========================================================================
    # 文档合并接口 - 支持PDF和OFD混合
    # ========================================================================

    def merge_documents(self, file_paths: List[str], output_path: str, 
                       layout: Union[str, dict], mode: str = '普通') -> bool:
        """
        合并多个文档（支持PDF和OFD混合）
        
        处理流程：
        1. 将所有OFD文件转换为临时PDF
        2. 调用PDFHandler合并所有PDF
        3. 清理临时文件
        
        Args:
            file_paths: 文件路径列表（可包含.pdf和.ofd）
            output_path: 输出PDF文件路径
            layout: 布局配置（字符串或字典）
            mode: 合并模式，'普通'或'图像'
            
        Returns:
            bool: 合并是否成功
        """
        if not file_paths:
            print("[UniHandler] 合并失败: 文件列表为空")
            return False

        try:
            print(f"[UniHandler] 开始合并 {len(file_paths)} 个文件...")
            
            # 转换所有OFD为PDF
            pdf_paths = []
            for i, file_path in enumerate(file_paths):
                if self._is_ofd(file_path):
                    print(f"[UniHandler] 转换OFD文件 {i+1}/{len(file_paths)}: {file_path}")
                    pdf_path = self._convert_ofd_to_pdf(file_path)
                    pdf_paths.append(pdf_path)
                else:
                    pdf_paths.append(file_path)

            # 调用PDFHandler合并
            print(f"[UniHandler] 执行PDF合并...")
            result = self._pdf_handler.merge_pdfs(pdf_paths, output_path, layout, mode)
            
            if result:
                print(f"[UniHandler] 合并成功: {output_path}")
            else:
                print(f"[UniHandler] 合并失败")

            # 清理本次合并产生的临时文件
            self._cleanup_temp_files()

            return result

        except Exception as e:
            print(f"[UniHandler] 合并文档失败: {str(e)}")
            self._cleanup_temp_files()
            return False

    # ========================================================================
    # 预览接口 - 支持PDF和OFD
    # ========================================================================

    def get_preview_pixmap(self, file_path: str) -> Optional[Any]:
        """
        获取文档预览图像
        
        自动处理PDF和OFD格式，返回QPixmap对象供UI显示
        
        Args:
            file_path: 文档文件路径
            
        Returns:
            QPixmap或None: 预览图像，失败返回None
        """
        try:
            if self._is_ofd(file_path):
                # OFD需要先转换为PDF再渲染
                temp_pdf = self._convert_ofd_to_pdf(file_path)
                pixmap = self._render_pdf_to_pixmap(temp_pdf)
                self._cleanup_temp_files()
                return pixmap
            else:
                # PDF直接渲染
                return self._render_pdf_to_pixmap(file_path)
                
        except Exception as e:
            print(f"[UniHandler] 生成预览失败: {file_path}, {e}")
            return None

    def _render_pdf_to_pixmap(self, pdf_path: str) -> Optional[Any]:
        """
        将PDF渲染为QPixmap（内部方法）
        
        Args:
            pdf_path: PDF文件路径
            
        Returns:
            QPixmap或None: 渲染后的图像
        """
        try:
            import fitz
            from PySide6.QtGui import QPixmap
            
            doc = fitz.open(pdf_path)
            page = doc[0]
            # 2x缩放以获得清晰预览
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img_data = pix.tobytes("png")
            doc.close()

            pixmap = QPixmap()
            pixmap.loadFromData(img_data)
            return pixmap
            
        except Exception as e:
            print(f"[UniHandler] PDF渲染失败: {pdf_path}, {e}")
            return None

    # ========================================================================
    # 工具方法
    # ========================================================================

    @staticmethod
    def get_supported_extensions() -> List[str]:
        """
        获取支持的文件扩展名列表
        
        Returns:
            List[str]: 支持的扩展名列表，如 ['.pdf', '.ofd']
        """
        return ['.pdf', '.ofd']

    @staticmethod
    def get_file_filter() -> str:
        """
        获取文件选择对话框的过滤器字符串
        
        Returns:
            str: Qt文件过滤器字符串
        """
        return "发票文件 (*.pdf *.ofd);;PDF文件 (*.pdf);;OFD文件 (*.ofd)"

    def is_supported_file(self, file_path: str) -> bool:
        """
        检查文件是否为支持的格式
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 是否支持该文件格式
        """
        return self._is_pdf(file_path) or self._is_ofd(file_path)
