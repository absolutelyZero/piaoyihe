#!/usr/bin/env python3
"""
主题模块

该模块提供系统深色/浅色模式检测与对应的应用配色方案，
供主窗口、文件列表、对话框等 UI 组件统一使用。
"""

import sys
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication


def is_dark_mode():
    """
    检测当前系统是否处于深色模式

    功能描述:
        优先使用 Qt 6.5+ 提供的 QStyleHints.colorScheme() 接口检测；
        当该接口不可用或返回未知时，回退到读取 Windows 注册表。

    返回值:
        bool: 系统当前为深色模式时返回 True，否则返回 False
    """
    # 优先使用 Qt 6.5+ 的系统颜色方案接口
    try:
        color_scheme = QApplication.styleHints().colorScheme()
        if color_scheme == Qt.ColorScheme.Dark:
            return True
        if color_scheme == Qt.ColorScheme.Light:
            return False
    except Exception:
        # 低版本 Qt 或异常时继续走注册表回退
        pass

    # 回退方案：读取 Windows 注册表中的应用主题设置
    if sys.platform == "win32":
        try:
            import winreg
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
            ) as key:
                value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                return value == 0
        except Exception:
            pass

    return False


class AppTheme:
    """
    应用主题配色类

    功能描述:
        根据系统深色/浅色模式提供统一的配色常量，
        各 UI 组件可通过本类获取与当前主题一致的背景、文字、边框等颜色。

    参数:
        dark: 是否使用深色模式；为 None 时自动检测系统主题
    """

    def __init__(self, dark=None):
        """
        初始化主题配色

        参数:
            dark: 是否使用深色模式；为 None 时自动检测系统主题
        """
        self.dark = is_dark_mode() if dark is None else bool(dark)
        self._init_colors()

    def _init_colors(self):
        """
        初始化颜色常量

        功能描述:
            根据当前深色/浅色标志初始化所有配色值
        """
        if self.dark:
            # 深色模式配色
            self.bg = "#1E1E1E"              # 窗口背景色
            self.card_bg = "#2D2D2D"         # 卡片/输入框背景色
            self.border = "#3C3C3C"          # 边框色
            self.text_primary = "#EAEAEA"    # 主要文字色
            self.text_secondary = "#B0B0B0"  # 次要文字色
            self.text_muted = "#808080"      # 弱化文字色
            self.hover_bg = "#3A3A3A"        # 悬停背景色
            self.pressed_bg = "#444444"      # 按下背景色
            self.selected_bg = "#0D47A1"     # 选中背景色
            self.selected_text = "#FFFFFF"   # 选中文字色
            self.alt_row = "#252525"         # 表格交替行背景色
            self.scroll_area_bg = "#262626"  # 滚动区域背景色
            self.placeholder_start = "#2A2D33"  # 预览占位渐变起始色（低饱和蓝灰）
            self.placeholder_mid = "#2D2D33"    # 预览占位渐变中间色（中蓝灰）
            self.placeholder_end = "#2A2A2A"    # 预览占位渐变结束色（深灰）
            self.placeholder_border = "#1565C0" # 预览占位虚线边框色（深色模式降低亮度）
        else:
            # 浅色模式配色（与原有配色保持一致）
            self.bg = "#F5F5F5"              # 窗口背景色
            self.card_bg = "#FFFFFF"         # 卡片/输入框背景色
            self.border = "#E0E0E0"          # 边框色
            self.text_primary = "#212121"    # 主要文字色
            self.text_secondary = "#757575"  # 次要文字色
            self.text_muted = "#9E9E9E"      # 弱化文字色
            self.hover_bg = "#FAFAFA"        # 悬停背景色
            self.pressed_bg = "#F0F0F0"      # 按下背景色
            self.selected_bg = "#E3F2FD"     # 选中背景色
            self.selected_text = "#212121"   # 选中文字色
            self.alt_row = "#FAFAFA"         # 表格交替行背景色
            self.scroll_area_bg = "#FAFAFA"  # 滚动区域背景色
            self.placeholder_start = "#E3F2FD"  # 预览占位渐变起始色
            self.placeholder_mid = "#F3E5F5"    # 预览占位渐变中间色
            self.placeholder_end = "#E8F5E9"    # 预览占位渐变结束色
            self.placeholder_border = "#2196F3" # 预览占位虚线边框色
