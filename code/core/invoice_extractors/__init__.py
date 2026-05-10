#!/usr/bin/env python3
"""
发票字段提取器模块

该模块提供各种发票类型的字段提取功能，采用策略模式设计，
每种票种有独立的提取器实现，便于维护和扩展。
"""

from .base import InvoiceExtractor
from .factory import InvoiceExtractorFactory
from .common_invoice import CommonInvoiceExtractor
from .train_ticket import TrainTicketExtractor
from .flight_ticket import FlightTicketExtractor
from .vehicle_invoice import VehicleInvoiceExtractor
from .taxi_invoice import TaxiInvoiceExtractor
from .fixed_amount_invoice import FixedAmountInvoiceExtractor
from .toll_invoice import TollInvoiceExtractor

__all__ = [
    'InvoiceExtractor',
    'InvoiceExtractorFactory',
    'CommonInvoiceExtractor',
    'TrainTicketExtractor',
    'FlightTicketExtractor',
    'VehicleInvoiceExtractor',
    'TaxiInvoiceExtractor',
    'FixedAmountInvoiceExtractor',
    'TollInvoiceExtractor',
]
