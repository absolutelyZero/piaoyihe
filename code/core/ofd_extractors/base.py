#!/usr/bin/env python3
"""
OFD发票字段提取器抽象基类模块

提供所有OFD发票提取器的抽象基类，定义统一的接口和通用功能。
与PDF提取器基类结构一致，但针对OFD格式优化。
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List


class OFDExtractor(ABC):
    """
    OFD发票字段提取器抽象基类

    所有具体票种OFD提取器必须继承此类，实现各字段的提取方法。
    支持上下文管理器协议，确保OFD文档正确关闭。

    Attributes:
        INVOICE_TYPE_KEYWORDS: 类属性，用于识别票种的关键词列表
        ofd_path: OFD文件路径
        _ofd: OFD对象，在上下文管理器中打开
        _content: OFD内容数据缓存
        _text: 提取的文本内容缓存
    """

    INVOICE_TYPE_KEYWORDS: List[str] = []

    def __init__(self, ofd_path: str):
        """
        初始化提取器

        Args:
            ofd_path: OFD文件路径
        """
        self.ofd_path = ofd_path
        self._ofd = None
        self._content = None
        self._text = None

    def __enter__(self):
        """
        上下文管理器入口

        打开OFD文档，缓存内容数据

        Returns:
            OFDExtractor: 当前实例
        """
        try:
            from easyofd.ofd import OFD
            import base64

            self._ofd = OFD()
            # easyofd需要base64编码的数据
            with open(self.ofd_path, 'rb') as f:
                ofdb64 = str(base64.b64encode(f.read()), "utf-8")

            try:
                self._ofd.read(ofdb64, save_xml=False)
            except (AssertionError, Exception):
                # easyofd在解析某些带签名的OFD时会失败，尝试备用方案
                try:
                    self._ofd.read(ofdb64, save_xml=True, xml_name="temp_ofd_parse")
                except Exception:
                    # 最终备用方案：使用PyMuPDF提取文本
                    self._text = self._extract_text_with_pymupdf()
                    return self
            self._text = self._extract_all_text()

            # 调试信息
            print(f"[OFDExtractor] 成功打开OFD文件，提取文本长度: {len(self._text)}")
            if self._text:
                print(f"[OFDExtractor] 文本前100字符: {self._text[:100]}")

        except Exception as e:
            print(f"[OFDExtractor] 打开OFD文件失败: {e}")
            import traceback
            traceback.print_exc()
            self._ofd = None
            self._text = ""
        return self

    def _extract_text_with_pymupdf(self) -> str:
        """
        使用PyMuPDF提取OFD文本（备用方案）

        Returns:
            str: 提取的文本内容
        """
        texts = []
        try:
            import fitz
            doc = fitz.open(self.ofd_path)
            for page in doc:
                texts.append(page.get_text())
            doc.close()
            print(f"[OFDExtractor] PyMuPDF提取文本长度: {len(''.join(texts))}")
        except Exception as e:
            print(f"[OFDExtractor] PyMuPDF提取文本失败: {e}")
        return "\n".join(texts)

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        上下文管理器出口

        关闭OFD文档，释放资源

        Args:
            exc_type: 异常类型
            exc_val: 异常值
            exc_tb: 异常追踪

        Returns:
            bool: 是否处理异常（False表示不处理）
        """
        if self._ofd:
            try:
                self._ofd.del_data()
            except Exception:
                pass
        return False

    def _extract_all_text(self) -> str:
        """
        提取OFD中所有文本内容

        Returns:
            str: 所有页面文本的拼接
        """
        texts = []
        try:
            # easyofd的data属性包含解析后的数据
            if self._ofd and hasattr(self._ofd, 'data'):
                data = self._ofd.data
                print(f"[OFDExtractor] data类型: {type(data)}")

                if isinstance(data, dict):
                    print(f"[OFDExtractor] data键: {list(data.keys())[:10]}")  # 打印前10个键

                    if 'pages' in data:
                        pages = data['pages']
                        print(f"[OFDExtractor] 页数: {len(pages)}")

                        for page_idx, page in enumerate(pages):
                            if isinstance(page, dict) and 'texts' in page:
                                page_texts = page['texts']
                                print(f"[OFDExtractor] 第{page_idx}页文本项数: {len(page_texts)}")

                                for text_item in page_texts:
                                    if isinstance(text_item, dict) and 'text' in text_item:
                                        texts.append(text_item['text'])
                                    elif isinstance(text_item, str):
                                        texts.append(text_item)
                    else:
                        print(f"[OFDExtractor] data中没有'pages'键")
                else:
                    print(f"[OFDExtractor] data不是字典类型")
            else:
                print(f"[OFDExtractor] _ofd为None或没有data属性")
        except Exception as e:
            print(f"[OFDExtractor] 提取文本失败: {e}")
            import traceback
            traceback.print_exc()
        return "\n".join(texts)

    @classmethod
    def can_handle(cls, text: str) -> bool:
        """
        判断是否能处理该文本内容

        通过检查文本中是否包含票种关键词来判断

        Args:
            text: OFD文本内容

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

    @abstractmethod
    def extract_tax_amount(self) -> float:
        """
        提取税额

        Returns:
            float: 提取的税额，无则返回0.0
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
                - invoice_code: 发票号码
                - tax_amount: 税额
        """
        return {
            'amount': self.extract_amount(),
            'invoice_date': self.extract_invoice_date(),
            'invoice_type': self.extract_invoice_type(),
            'product_type': self.extract_product_type(),
            'buyer_name': self.extract_buyer_name(),
            'seller_name': self.extract_seller_name(),
            'invoice_code': self.extract_invoice_code(),
            'tax_amount': self.extract_tax_amount(),
        }
