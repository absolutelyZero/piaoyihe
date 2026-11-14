#!/usr/bin/env python3
"""
主题模块

提供系统深色/浅色模式检测与对应的应用配色方案。
自 v2 UI 起，所有色值统一来自 :mod:`ui.tokens`；``AppTheme`` 保留原有属性名，
作为旧代码（main_frame / file_list / rename_dialog）的兼容层，避免一次性改动
全部引用点。新代码应直接使用 ``ui.tokens.get_tokens()``。
"""

import sys
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from ui.tokens import get_tokens


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
    应用主题配色类（兼容层）

    功能描述:
        根据系统深色/浅色模式，从 ui.tokens 的语义令牌映射出旧版属性名，
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
            把语义令牌映射到旧版属性名；两套主题共用同一份映射逻辑，
            保证深浅切换只改变色值、不改变任何结构或语义。
        """
        t = get_tokens(self.dark)

        # 旧版属性名（保持兼容）
        self.bg = t["background"]
        self.card_bg = t["surface"]
        self.border = t["border"]
        self.text_primary = t["text_primary"]
        self.text_secondary = t["text_secondary"]
        self.text_muted = t["text_muted"]
        self.hover_bg = t["hover_bg"]
        self.pressed_bg = t["pressed_bg"]
        self.selected_bg = t["selected_bg"]
        self.selected_text = t["selected_text"]
        self.alt_row = t["alt_row"]
        self.scroll_area_bg = t["surface_sunken"]
        self.placeholder_start = t["placeholder_start"]
        self.placeholder_mid = t["placeholder_mid"]
        self.placeholder_end = t["placeholder_end"]
        self.placeholder_border = t["placeholder_border"]

        # v2 语义别名（供新代码直接取用）
        self.accent = t["accent"]
        self.accent_tint = t["accent_tint"]
        self.success = t["success"]
        self.warning = t["warning"]
        self.danger = t["danger"]
        self.surface_alt = t["surface_alt"]
        self.tokens = t
