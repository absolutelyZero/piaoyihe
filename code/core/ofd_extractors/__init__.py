#!/usr/bin/env python3
"""
OFD发票提取器模块

提供OFD格式发票的字段提取功能
与PDF提取器模块结构平行，完全独立
"""

from .base import OFDExtractor
from .factory import OFDExtractorFactory

__all__ = ['OFDExtractor', 'OFDExtractorFactory']
