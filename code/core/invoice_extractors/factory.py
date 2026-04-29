#!/usr/bin/env python3
"""
发票提取器工厂模块

提供根据PDF内容自动选择合适提取器的工厂类。
采用工厂模式，便于管理和扩展各种票种提取器。
"""

from typing import Type, Optional, List
import fitz
from .base import InvoiceExtractor


class InvoiceExtractorFactory:
    """
    发票提取器工厂类

    根据PDF内容自动选择合适的提取器，管理所有提取器的注册和匹配。

    Attributes:
        _extractors: 注册的提取器类列表，按优先级排序
    """

    _extractors: List[Type[InvoiceExtractor]] = []
    _initialized: bool = False

    @classmethod
    def _initialize(cls):
        """
        延迟初始化提取器列表

        避免循环导入问题，在首次使用时加载所有提取器
        """
        if cls._initialized:
            return

        # 导入所有具体提取器
        from .train_ticket import TrainTicketExtractor
        from .flight_ticket import FlightTicketExtractor
        from .vehicle_invoice import VehicleInvoiceExtractor
        from .taxi_invoice import TaxiInvoiceExtractor
        from .fixed_amount_invoice import FixedAmountInvoiceExtractor
        from .toll_invoice import TollInvoiceExtractor
        from .common_invoice import CommonInvoiceExtractor

        # 注册所有提取器，按优先级排序（特征明显的优先）
        cls._extractors = [
            TrainTicketExtractor,      # 火车票 - 优先级高（特征明显）
            FlightTicketExtractor,     # 飞机票 - 优先级高（特征明显）
            VehicleInvoiceExtractor,   # 机动车发票
            TaxiInvoiceExtractor,      # 出租车发票
            FixedAmountInvoiceExtractor,  # 定额发票
            TollInvoiceExtractor,      # 通行费发票
            CommonInvoiceExtractor,    # 普通发票 - 兜底
        ]
        cls._initialized = True

    @classmethod
    def get_extractor(cls, pdf_path: str) -> Optional[InvoiceExtractor]:
        """
        根据PDF路径获取合适的提取器

        打开PDF文件，读取文本内容，匹配合适的提取器

        Args:
            pdf_path: PDF文件路径

        Returns:
            Optional[InvoiceExtractor]: 提取器实例，无法匹配则返回None
        """
        cls._initialize()

        try:
            with fitz.open(pdf_path) as doc:
                text = "\n".join([page.get_text(sort="block") for page in doc])

                for extractor_class in cls._extractors:
                    if extractor_class.can_handle(text):
                        return extractor_class(pdf_path)

        except Exception as e:
            print(f"获取提取器失败: {str(e)}")

        return None

    @classmethod
    def register_extractor(cls, extractor_class: Type[InvoiceExtractor], priority: int = -1):
        """
        注册新的提取器

        支持动态注册新的票种提取器，便于扩展

        Args:
            extractor_class: 提取器类，必须继承InvoiceExtractor
            priority: 优先级，越小越优先，-1表示添加到末尾

        Example:
            >>> from .my_invoice import MyInvoiceExtractor
            >>> InvoiceExtractorFactory.register_extractor(MyInvoiceExtractor, priority=0)
        """
        cls._initialize()

        if priority >= 0:
            cls._extractors.insert(priority, extractor_class)
        else:
            cls._extractors.append(extractor_class)

    @classmethod
    def get_registered_extractors(cls) -> List[Type[InvoiceExtractor]]:
        """
        获取所有已注册的提取器

        Returns:
            List[Type[InvoiceExtractor]]: 提取器类列表
        """
        cls._initialize()
        return cls._extractors.copy()
