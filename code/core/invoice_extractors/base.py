#!/usr/bin/env python3
"""
发票字段提取器抽象基类模块

提供所有发票提取器的抽象基类，定义统一的接口和通用功能。
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
import fitz


class InvoiceExtractor(ABC):
    """
    发票字段提取器抽象基类

    所有具体票种提取器必须继承此类，实现各字段的提取方法。
    支持上下文管理器协议，确保PDF文档正确关闭。

    Attributes:
        INVOICE_TYPE_KEYWORDS: 类属性，用于识别票种的关键词列表
        pdf_path: PDF文件路径
        _doc: fitz.Document对象，在上下文管理器中打开
        _text: PDF全文文本缓存
        _pages: PDF页面列表缓存
    """

    INVOICE_TYPE_KEYWORDS: List[str] = []

    def __init__(self, pdf_path: str):
        """
        初始化提取器

        Args:
            pdf_path: PDF文件路径
        """
        self.pdf_path = pdf_path
        self._doc = None
        self._text = None
        self._pages = []

    def __enter__(self):
        """
        上下文管理器入口

        打开PDF文档，缓存文本和页面数据

        Returns:
            InvoiceExtractor: 当前实例
        """
        self._doc = fitz.open(self.pdf_path)
        self._pages = [self._doc[i] for i in range(len(self._doc))]
        self._text = "\n".join([page.get_text(sort="block") for page in self._pages])
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        上下文管理器出口

        关闭PDF文档，释放资源

        Args:
            exc_type: 异常类型
            exc_val: 异常值
            exc_tb: 异常追踪

        Returns:
            bool: 是否处理异常（False表示不处理）
        """
        if self._doc:
            self._doc.close()
        return False

    @classmethod
    def can_handle(cls, text: str) -> bool:
        """
        判断是否能处理该文本内容

        通过检查文本中是否包含票种关键词来判断

        Args:
            text: PDF文本内容

        Returns:
            bool: 是否能处理该票种
        """
        return any(keyword in text for keyword in cls.INVOICE_TYPE_KEYWORDS)

    @abstractmethod
    def extract_amount(self) -> float:
        """
        提取金额

        Returns:
            float: 提取的金额，失败返回0.0
        """
        pass

    @abstractmethod
    def extract_invoice_date(self) -> str:
        """
        提取开票日期

        Returns:
            str: 日期字符串，格式YYYY-MM-DD
        """
        pass

    @abstractmethod
    def extract_invoice_type(self) -> str:
        """
        提取发票类型

        Returns:
            str: 发票类型名称，如"普票"、"专票"、"火车票"等
        """
        pass

    @abstractmethod
    def extract_product_type(self) -> str:
        """
        提取商品类型/服务名称

        Returns:
            str: 商品或服务名称，无则返回空字符串
        """
        pass

    @abstractmethod
    def extract_buyer_name(self) -> str:
        """
        提取购买方名称

        Returns:
            str: 购买方名称
        """
        pass

    @abstractmethod
    def extract_seller_name(self) -> str:
        """
        提取销售方名称

        Returns:
            str: 销售方名称
        """
        pass

    @abstractmethod
    def extract_invoice_code(self) -> str:
        """
        提取发票号码

        Returns:
            str: 发票号码，无则返回空字符串
        """
        pass

    def extract_all(self) -> Dict[str, Any]:
        """
        一次性提取所有字段

        调用各字段提取方法，返回完整信息字典

        Returns:
            Dict[str, Any]: 包含所有字段的字典
                - amount: 金额
                - invoice_date: 开票日期
                - invoice_type: 发票类型
                - product_type: 商品类型
                - buyer_name: 购买方名称
                - seller_name: 销售方名称
        """
        return {
            'amount': self.extract_amount(),
            'invoice_date': self.extract_invoice_date(),
            'invoice_type': self.extract_invoice_type(),
            'product_type': self.extract_product_type(),
            'buyer_name': self.extract_buyer_name(),
            'seller_name': self.extract_seller_name(),
            'invoice_code': self.extract_invoice_code(),
        }
