#!/usr/bin/env python3
"""
OFD发票提取器工厂模块

提供根据OFD内容自动选择合适提取器的工厂类。
与PDF工厂类结构平行，完全独立。
"""

from typing import Type, Optional, List
from .base import OFDExtractor


class OFDExtractorFactory:
    """
    OFD发票提取器工厂类

    根据OFD内容自动选择合适的提取器，管理所有提取器的注册和匹配。

    Attributes:
        _extractors: 注册的提取器类列表，按优先级排序
        _initialized: 是否已初始化
    """

    _extractors: List[Type[OFDExtractor]] = []
    _initialized: bool = False

    @classmethod
    def _initialize(cls):
        """
        延迟初始化提取器列表

        避免循环导入问题，在首次使用时加载所有提取器
        """
        if cls._initialized:
            return

        try:
            # 导入所有具体提取器
            from .extractors.train_ticket import OFDTrainTicketExtractor
            from .extractors.flight_ticket import OFDFlightTicketExtractor
            from .extractors.vehicle_invoice import OFDVehicleInvoiceExtractor
            from .extractors.taxi_invoice import OFDTaxiInvoiceExtractor
            from .extractors.fixed_amount_invoice import OFDFixedAmountInvoiceExtractor
            from .extractors.toll_invoice import OFDTollInvoiceExtractor
            from .extractors.common_invoice import OFDCommonInvoiceExtractor

            # 注册所有提取器，按优先级排序（特征明显的优先）
            cls._extractors = [
                OFDTrainTicketExtractor,      # 火车票 - 优先级高（特征明显）
                OFDFlightTicketExtractor,     # 飞机票 - 优先级高（特征明显）
                OFDVehicleInvoiceExtractor,   # 机动车发票
                OFDTaxiInvoiceExtractor,      # 出租车发票
                OFDFixedAmountInvoiceExtractor,  # 定额发票
                OFDTollInvoiceExtractor,      # 通行费发票
                OFDCommonInvoiceExtractor,    # 普通发票 - 兜底
            ]
            cls._initialized = True
            print(f"[OFDExtractorFactory] 初始化完成，注册了 {len(cls._extractors)} 个提取器")
        except ImportError as e:
            print(f"[OFDExtractorFactory] 导入提取器失败: {e}")
            import traceback
            traceback.print_exc()
            # 如果提取器尚未实现，先使用空列表
            cls._extractors = []
            cls._initialized = True

    @classmethod
    def get_extractor(cls, ofd_path: str) -> Optional[OFDExtractor]:
        """
        根据OFD路径获取合适的提取器

        打开OFD文件，读取文本内容，匹配合适的提取器

        Args:
            ofd_path: OFD文件路径

        Returns:
            Optional[OFDExtractor]: 提取器实例，无法匹配则返回None
        """
        cls._initialize()

        if not cls._extractors:
            print("[OFDExtractorFactory] 警告：没有可用的提取器")
            return None

        try:
            # 尝试使用easyofd库打开文件
            try:
                from easyofd.ofd import OFD
                import base64

                ofd = OFD()
                with open(ofd_path, 'rb') as f:
                    ofdb64 = str(base64.b64encode(f.read()), "utf-8")

                try:
                    ofd.read(ofdb64, save_xml=False)
                except (AssertionError, Exception):
                    # easyofd在解析某些带签名的OFD时会失败，尝试备用方案
                    try:
                        ofd.read(ofdb64, save_xml=True, xml_name="temp_ofd_parse")
                    except Exception:
                        # 最终备用方案：使用PyMuPDF提取文本
                        text = cls._extract_text_with_pymupdf(ofd_path)
                        ofd.del_data() if hasattr(ofd, 'del_data') else None
                        return text

                # 从easyofd数据结构中提取文本
                texts = []
                if hasattr(ofd, 'data') and isinstance(ofd.data, dict):
                    data = ofd.data
                    if 'pages' in data:
                        for page in data['pages']:
                            if isinstance(page, dict) and 'texts' in page:
                                for text_item in page['texts']:
                                    if isinstance(text_item, dict) and 'text' in text_item:
                                        texts.append(text_item['text'])
                                    elif isinstance(text_item, str):
                                        texts.append(text_item)

                text = "\n".join(texts)
                ofd.del_data()

                # 调试：打印提取到的文本前200字符
                print(f"[OFDExtractorFactory] 提取文本长度: {len(text)}, 前200字符: {text[:200]}")

            except Exception as e:
                print(f"[OFDExtractorFactory] 使用easyofd打开失败，尝试备用方法: {e}")
                import traceback
                traceback.print_exc()
                # 备用方法：尝试作为ZIP读取文本内容
                text = cls._extract_text_from_ofd(ofd_path)

            # 匹配合适的提取器
            for extractor_class in cls._extractors:
                can_handle = extractor_class.can_handle(text)
                print(f"[OFDExtractorFactory] 检查提取器 {extractor_class.__name__}: {can_handle}")
                if can_handle:
                    print(f"[OFDExtractorFactory] 匹配到提取器: {extractor_class.__name__}")
                    return extractor_class(ofd_path)

            print("[OFDExtractorFactory] 未找到匹配的提取器，使用默认提取器")
            # 返回第一个作为默认
            return cls._extractors[-1](ofd_path) if cls._extractors else None

        except Exception as e:
            print(f"[OFDExtractorFactory] 获取提取器失败: {str(e)}")
            return None

    @classmethod
    def _extract_text_with_pymupdf(cls, ofd_path: str) -> str:
        """
        使用PyMuPDF提取OFD文本（备用方案）

        Args:
            ofd_path: OFD文件路径

        Returns:
            str: 提取的文本内容
        """
        texts = []
        try:
            import fitz
            doc = fitz.open(ofd_path)
            for page in doc:
                texts.append(page.get_text())
            doc.close()
            print(f"[OFDExtractorFactory] PyMuPDF提取文本长度: {len(''.join(texts))}")
        except Exception as e:
            print(f"[OFDExtractorFactory] PyMuPDF提取文本失败: {e}")
        return "\n".join(texts)

    @classmethod
    def _extract_text_from_ofd(cls, ofd_path: str) -> str:
        """
        从OFD文件中提取文本（备用方法）

        当ofd-py库无法正常工作时，尝试直接读取OFD文件内容

        Args:
            ofd_path: OFD文件路径

        Returns:
            str: 提取的文本内容
        """
        texts = []
        try:
            import zipfile
            import xml.etree.ElementTree as ET

            with zipfile.ZipFile(ofd_path, 'r') as zf:
                # 尝试读取所有XML文件中的文本
                for name in zf.namelist():
                    if name.endswith('.xml'):
                        try:
                            content = zf.read(name).decode('utf-8')
                            # 简单提取文本内容
                            texts.append(content)
                        except Exception:
                            pass
        except Exception as e:
            print(f"[OFDExtractorFactory] 备用文本提取失败: {e}")

        return "\n".join(texts)

    @classmethod
    def register_extractor(cls, extractor_class: Type[OFDExtractor], priority: int = -1):
        """
        注册新的提取器

        支持动态注册新的票种提取器，便于扩展

        Args:
            extractor_class: 提取器类，必须继承OFDExtractor
            priority: 优先级，越小越优先，-1表示添加到末尾

        Example:
            >>> from .my_invoice import MyOFDInvoiceExtractor
            >>> OFDExtractorFactory.register_extractor(MyOFDInvoiceExtractor, priority=0)
        """
        cls._initialize()

        if not issubclass(extractor_class, OFDExtractor):
            raise ValueError("提取器类必须继承OFDExtractor")

        if priority >= 0:
            cls._extractors.insert(priority, extractor_class)
        else:
            cls._extractors.append(extractor_class)

        print(f"[OFDExtractorFactory] 注册提取器: {extractor_class.__name__}, 优先级: {priority}")

    @classmethod
    def get_registered_extractors(cls) -> List[Type[OFDExtractor]]:
        """
        获取所有已注册的提取器

        Returns:
            List[Type[OFDExtractor]]: 提取器类列表
        """
        cls._initialize()
        return cls._extractors.copy()

    @classmethod
    def unregister_extractor(cls, extractor_class: Type[OFDExtractor]):
        """
        注销提取器

        Args:
            extractor_class: 要注销的提取器类
        """
        cls._initialize()

        if extractor_class in cls._extractors:
            cls._extractors.remove(extractor_class)
            print(f"[OFDExtractorFactory] 注销提取器: {extractor_class.__name__}")
