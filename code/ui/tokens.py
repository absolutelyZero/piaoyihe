#!/usr/bin/env python3
"""
UI 设计令牌（唯一色值 / 字体 / 尺寸来源）

票易合 v2 UI 的全部配色、字体栈、圆角与间距刻度都定义在这里。
`ui/theme.py` 的 AppTheme 降级为本模块的兼容层；主窗口、台账与所有
对话框通过全局 QSS 消费同一份令牌，避免各处硬编码色值产生漂移。

设计基线见 ``req/ui/00-设计说明与设计系统.png`` 与
``req/ui/04-深色模式.png``；两套令牌的键名必须完全一致。
"""

from __future__ import annotations

import os
import sys
from typing import Dict, Iterable, Optional

__all__ = [
    "LIGHT",
    "DARK",
    "SPACING",
    "RADIUS",
    "FONT_CN_STACK",
    "FONT_MONO_STACK",
    "FONT_WEIGHT",
    "FONT_SIZE",
    "DESIGN_DISPLAY_SIZE",
    "NUMERIC_TEXT_OBJECTS",
    "NUMERIC_TEXT_SIZES",
    "NUMERIC_INPUT_OBJECTS",
    "apply_numeric_text_fonts",
    "header_font",
    "get_tokens",
    "build_stylesheet",
    "resolve_font_family",
    "register_bundled_fonts",
    "numeric_font",
    "apply_application_style",
    "clear_inline_styles",
]


# ---------------------------------------------------------------------------
# 语义色令牌（浅色 / 深色键名必须完全一致）
# ---------------------------------------------------------------------------
LIGHT: Dict[str, str] = {
    "background": "#F4F6F9",
    "surface": "#FFFFFF",
    "surface_alt": "#F8FAFC",
    "surface_sunken": "#F1F4F8",
    "border": "#E3E8EF",
    "border_strong": "#CBD5E1",
    "text_primary": "#16202E",
    "text_secondary": "#5A6B7F",
    "text_muted": "#8A97A8",
    "accent": "#1A56A8",
    "accent_hover": "#154688",
    "accent_pressed": "#103670",
    "accent_tint": "#EAF1FB",
    "accent_border": "#BFD3EE",
    "accent_text": "#FFFFFF",
    "success": "#12805C",
    "success_tint": "#E8F5EF",
    "success_border": "#A9DCC6",
    "warning": "#B7791F",
    "warning_tint": "#FEF6E7",
    "warning_border": "#F0D9A8",
    "warning_row": "#FEFBF4",
    "danger": "#C0392B",
    "danger_tint": "#FCEDEB",
    "danger_border": "#F0C4BF",
    "hover_bg": "#F4F6F9",
    "pressed_bg": "#E8EDF3",
    "selected_bg": "#EAF1FB",
    "selected_text": "#16202E",
    "alt_row": "#FAFBFD",
    "scroll_bg": "#F1F4F8",
    "placeholder_start": "#F8FAFC",
    "placeholder_mid": "#F1F4F8",
    "placeholder_end": "#EAF1FB",
    "placeholder_border": "#CBD5E1",
}

DARK: Dict[str, str] = {
    "background": "#141A23",
    "surface": "#1C2430",
    "surface_alt": "#222C3A",
    "surface_sunken": "#18202B",
    "border": "#2E3A49",
    "border_strong": "#3D4C5F",
    "text_primary": "#E6EDF5",
    "text_secondary": "#A3B1C2",
    "text_muted": "#74869A",
    "accent": "#4A86D8",
    "accent_hover": "#5E98E4",
    "accent_pressed": "#3A70BE",
    "accent_tint": "#1E3A5F",
    "accent_border": "#33598C",
    "accent_text": "#FFFFFF",
    "success": "#4CC49A",
    "success_tint": "#17382C",
    "success_border": "#2A6650",
    "warning": "#D9A441",
    "warning_tint": "#3A2E18",
    "warning_border": "#6B5427",
    "warning_row": "#2A2418",
    "danger": "#E07A6E",
    "danger_tint": "#3B2422",
    "danger_border": "#6B3733",
    "hover_bg": "#26313F",
    "pressed_bg": "#2E3A49",
    "selected_bg": "#1E3A5F",
    "selected_text": "#E6EDF5",
    "alt_row": "#202A36",
    "scroll_bg": "#18202B",
    "placeholder_start": "#222C3A",
    "placeholder_mid": "#1E2733",
    "placeholder_end": "#1A2431",
    "placeholder_border": "#3D4C5F",
}

# 间距刻度 4 / 8 / 12 / 16 / 20 / 24 / 32
SPACING = (4, 8, 12, 16, 20, 24, 32)
RADIUS = {"card": 8, "control": 6, "chip": 4}

# 设计稿（req/ui/00-设计说明与设计系统.png「05 / 字体与数字」）：
#   中文 Noto Sans SC（Regular 13 / Medium 14 / SemiBold 16 / Bold 20，行高 22，字距 0）
#   数字用 Inter，并启用 OpenType `tnum` 得到等宽数字后右对齐（见 file_list.py）。
# 设计稿 .op 源文件中数字节点的 fontFamily 正是 "Inter"，而非此前代码写的 Geist Mono。
# Geist Mono / JetBrains Mono 在目标机器上并不存在，会静默回退到 Arial（比例数字、
# 字形与设计稿不一致），这是「字体不是同一种、看起来不清晰」的根因。
# 因此把设计稿同款可变字体（Inter-VF.ttf / NotoSansSC-VF.ttf，均 SIL OFL 1.1）
# 随程序打包，启动时由 register_bundled_fonts() 注册，不再依赖系统是否安装。
FONT_CN_STACK = '"Noto Sans SC","Source Han Sans SC","Source Han Sans CN","Microsoft YaHei","PingFang SC","SimHei","DengXian",sans-serif'
FONT_MONO_STACK = '"Inter","JetBrains Mono","Consolas","Cascadia Mono","Noto Sans SC",monospace'
FONT_CN_FAMILIES = ("Noto Sans SC", "Source Han Sans SC", "Source Han Sans CN", "Microsoft YaHei", "PingFang SC", "SimHei", "DengXian")
FONT_MONO_FAMILIES = ("Inter", "JetBrains Mono", "Consolas", "Cascadia Mono", "Noto Sans SC")

# 设计稿正文 Regular 13px / 行高 22；应用级默认字号必须与之对齐，
# 此前 apply_application_style() 用 QFont(family, 9) = 12px，未被 QSS 覆盖的控件偏小。
# FONT_BODY_PIXEL_SIZE 派生自 FONT_SIZE["base"]，定义在 FONT_SIZE 之后。

# ---------------------------------------------------------------------------
# 字重 / 字号档位（设计稿 req/ui/00「05 / 字体与数字」）
#   Regular 13 / Medium 14 / SemiBold 16 / Bold 20；行高 22，字距 0
# ---------------------------------------------------------------------------
# Qt / QSS 使用 100-900 数值字重，OpenType 命名与数值的对应关系集中定义于此，
# 禁止在 QSS 或业务代码里散落 400/500/600/700 魔法数字。
FONT_WEIGHT = {
    "regular": 400,    # Regular  → 正文、表头（常规）
    "medium": 500,     # Medium   → 次级强调（设计稿 Medium 14）
    "semibold": 600,   # SemiBold → 选中态 / 强调标签
    "bold": 700,       # Bold     → 标题、主按钮、金额合计
}

# 界面实际消费的字号档位（px）。设计稿的 20px Bold 仅存在于说明页的大标题，
# 界面中无对应控件，故不加入此表、也不生成 QSS 规则。
FONT_SIZE = {
    "micro": 10,       # 进度条百分比
    "caption": 11,     # 次级/弱化文字、表头、状态栏、版本号
    "body": 12,        # 参数值、表格数据、芯片
    "base": 13,        # 正文基线（= FONT_BODY_PIXEL_SIZE）
    "subhead": 14,     # 卡片标题、主按钮
    "title": 15,       # 品牌名、合计金额
    "heading": 16,     # 台账标题、弹窗小节标题
    "dialog": 18,      # 弹窗主标题
}
# 设计稿展示专用字号：说明页「票易合 · 财务级 UI 重构设计说明」使用 Bold 20。
# 【设计稿展示用，界面不消费】——请勿据此在 QSS 中新增 20px 规则。
DESIGN_DISPLAY_SIZE = 20
FONT_BODY_PIXEL_SIZE = FONT_SIZE["base"]
FONT_LINE_HEIGHT_BODY = 22
FONT_LETTER_SPACING = 0

# 含数字的次级文本位（状态栏票据数 / 页码 / 每页张数 / 重复计数 / 记录数 / 版本号等）。
# 设计稿 .op 源文件中数字节点 fontFamily 均为 "Inter"，中文节点为 "Noto Sans SC"；
# Qt 单个 QLabel 无法逐字符切换字体，故用 FONT_MONO_STACK（Inter 优先，中文回退
# Noto Sans SC）作为这些混排文本的字体族，使数字字形与设计稿一致。
# 注意：QSS 无法启用 OpenType tnum，需要等宽对齐的金额列由 numeric_font() 承担。
NUMERIC_TEXT_OBJECTS = (
    "statusBarLabel", "footLabel", "statusLabel", "statusChip",
    "warningChip", "successChip", "dangerChip", "mutedLabel",
    "subtitleLabel", "hintLabel", "inlineUnit", "paramCaption",
    "ledgerTotalCaption", "liveStateLabel", "typeNavTitle",
    "helpCardText",
)
# 各数字文本位的字号（px），与 QSS 中对应 objectName 的 font-size 保持一致；
# 由 apply_numeric_text_fonts() 生成带 tnum 的 QFont，避免逐控件散落 setFont。
NUMERIC_TEXT_SIZES = {
    "statusBarLabel": FONT_SIZE["caption"],
    "footLabel": FONT_SIZE["caption"],
    "statusLabel": FONT_SIZE["caption"],
    "statusChip": FONT_SIZE["body"],
    "warningChip": FONT_SIZE["caption"],
    "successChip": FONT_SIZE["body"],
    "dangerChip": FONT_SIZE["body"],
    "mutedLabel": FONT_SIZE["caption"],
    "subtitleLabel": FONT_SIZE["caption"],
    "hintLabel": FONT_SIZE["caption"],
    "inlineUnit": FONT_SIZE["caption"],
    "paramCaption": FONT_SIZE["body"],
    "ledgerTotalCaption": FONT_SIZE["body"],
    "liveStateLabel": FONT_SIZE["caption"],
    "typeNavTitle": FONT_SIZE["caption"],
    "helpCardText": FONT_SIZE["caption"],
}

# 纯数字输入控件（SpinBox / 输出路径框）：同样由 numeric_font() 提供 Inter + tnum。
# 中文下拉（modeCombo / orderCombo）与规则输入框不在此列，保持中文栈。
NUMERIC_INPUT_OBJECTS = {
    "paramSpin": FONT_SIZE["body"],
    "bareSpin": FONT_SIZE["body"],
    "pathInput": FONT_SIZE["body"],
}

# 随程序打包的设计稿同款可变字体（位于 code/res/fonts/，随 PyInstaller datas 分发）
BUNDLED_FONTS = ("Inter-VF.ttf", "NotoSansSC-VF.ttf")
_BUNDLED_FONTS_REGISTERED = False


def _detect_dark() -> bool:
    """延迟探测系统主题，避免在纯 Python 环境下强制依赖 PySide6。"""
    try:
        from ui.theme import is_dark_mode  # noqa: WPS433 (延迟导入，避免与 theme 循环)
        return bool(is_dark_mode())
    except Exception:
        return False


def get_tokens(dark: Optional[bool] = None) -> Dict[str, str]:
    """返回当前主题下的语义令牌副本。"""
    if dark is None:
        dark = _detect_dark()
    return dict(DARK if dark else LIGHT)


def resolve_font_family(preferred: Iterable[str] = FONT_CN_FAMILIES) -> str:
    """从字体栈中挑选系统实际可用的第一个字体；全部缺失时回退系统默认。"""
    try:
        # QFontDatabase 需要已存在的 QGuiApplication；无 GUI 环境直接取首选字体，
        # 避免在纯逻辑测试或打包探测阶段触发 Qt 原生崩溃。
        from PySide6.QtWidgets import QApplication

        if QApplication.instance() is None:
            return next(iter(preferred))

        from PySide6.QtGui import QFontDatabase

        available = set(QFontDatabase.families())
        for family in preferred:
            if family in available:
                return family
    except Exception:
        pass
    # 无 Qt 环境（例如单元测试）时仍返回确定值，便于断言与文档比对
    return next(iter(preferred))


def _icon_url(filename: str) -> str:
    """把 ``code/res/icons`` 下的 SVG 转成 QSS ``url(...)`` 可用的路径。"""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(base, "res", "icons", filename)
    return "url(" + path.replace(os.sep, "/") + ")"


def _fonts_dir() -> str:
    """返回随程序分发的字体目录：打包后在 _MEIPASS/res/fonts，开发时在 code/res/fonts。"""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "res", "fonts")


def register_bundled_fonts() -> int:
    """
    把设计稿同款可变字体注册进 QFontDatabase，使界面字体不再依赖系统安装情况。

    必须在 QApplication / QGuiApplication 创建之后、setStyleSheet() 之前调用；
    重复调用是幂等的。返回本次成功注册的字体数量；字体文件缺失或无 Qt 环境时
    静默返回 0，由系统字体回退链兜底，绝不影响启动。
    """
    global _BUNDLED_FONTS_REGISTERED
    if _BUNDLED_FONTS_REGISTERED:
        return 0
    try:
        # QFontDatabase / addApplicationFont 需要一个已存在的 QApplication；
        # 纯逻辑测试或未创建应用时直接跳过（且不置位标志，留待创建后再注册），
        # 避免 Qt 原生崩溃。
        from PySide6.QtWidgets import QApplication
        from PySide6.QtGui import QFontDatabase

        if QApplication.instance() is None:
            return 0
    except Exception:
        return 0
    _BUNDLED_FONTS_REGISTERED = True
    registered = 0
    fonts_dir = _fonts_dir()
    for filename in BUNDLED_FONTS:
        path = os.path.join(fonts_dir, filename)
        if not os.path.isfile(path):
            continue
        try:
            if QFontDatabase.addApplicationFont(path) >= 0:
                registered += 1
        except Exception:
            continue
    return registered


def numeric_font(pixel_size: int, weight: Optional[int] = None) -> "QFont":
    """
    返回数字展示位使用的字体：设计稿同款 Inter，并启用 OpenType ``tnum``
    得到等宽数字（金额 / 税额 / 日期 / 发票号码列内对齐、字形一致）。

    ``pixel_size`` 由调用方按列宽给出：发票号码列 20 位需落在 151px 内，
    故用 11px；金额 / 税额 / 日期 / 修改日期 / 大小列内容较短可用 12px。
    ``weight`` 可选，取自 ``FONT_WEIGHT``（合计金额 Bold 等场景）。

    字体族使用 ``setFamilies`` 提供中文回退链：混排文本中的数字走 Inter，
    中文走 Noto Sans SC，避免中文被回退到系统默认字体而产生字形漂移。
    """
    register_bundled_fonts()
    from PySide6.QtGui import QFont

    font = QFont()
    font.setFamilies(list(FONT_MONO_FAMILIES))
    font.setStyleHint(QFont.StyleHint.TypeWriter)
    font.setPixelSize(pixel_size)
    if weight is not None:
        font.setWeight(QFont.Weight(weight))
    try:
        # PySide6 6.11 起 setFeature 的第一个参数必须是 QFont.Tag；
        # 旧版本接受四字符标签字符串，做一次兼容回退。
        font.setFeature(QFont.Tag("tnum"), 1)
    except Exception:
        try:
            font.setFeature("tnum", 1)  # type: ignore[arg-type]
        except Exception:
            pass
    return font


def header_font(bold: bool = False) -> "QFont":
    """
    表头字体唯一来源（QTableWidgetItem 的 FontRole）。

    设计稿 req/ui/01：表头 11px / 次级灰 / 常规字重，仅「金额」列主色加粗。
    以前 QSS 的 ``QHeaderView::section { font-weight: 500 }`` 与
    ``file_list.py`` 的 ``setBold()`` 同时指定字重，构成双来源；现在 QSS 不再
    声明表头字体，全部由此函数用 FONT_WEIGHT / FONT_SIZE 常量生成。
    """
    from PySide6.QtGui import QFont

    register_bundled_fonts()
    font = QFont()
    font.setFamilies(list(FONT_CN_FAMILIES))
    font.setPixelSize(FONT_SIZE["caption"])
    font.setWeight(QFont.Weight(FONT_WEIGHT["bold"] if bold else FONT_WEIGHT["regular"]))
    return font


def build_stylesheet(dark: Optional[bool] = None) -> str:
    """由令牌生成应用级 QSS（同时覆盖主窗口、对话框与所有子控件）。"""
    # 尽早注册打包字体，保证 QSS 中的 Inter / Noto Sans SC 能解析到设计稿同款字形；
    # 幂等且无 Qt 环境时静默跳过，不影响纯逻辑调用。
    register_bundled_fonts()
    t = get_tokens(dark)
    cn = FONT_CN_STACK
    mono = FONT_MONO_STACK
    W = FONT_WEIGHT
    S = FONT_SIZE
    numeric_selectors = ", ".join("QLabel#" + name for name in NUMERIC_TEXT_OBJECTS)
    check_mark = _icon_url("勾选_check-white.svg")
    chevron = _icon_url("箭头下_chevron-light.svg")

    return f"""
/* ===== 票易合 v2 · 财务级 UI 全局样式（由 ui/tokens.py 生成） ===== */
/* 应用级默认字体由 apply_application_style() 的 app.setFont() 唯一提供
   （Noto Sans SC / 13px / Regular）。此处刻意不声明 font-*：
   Qt QSS 一旦声明字体就会覆盖子控件的 setFont()，导致数字位无法启用 tnum。 */
QMainWindow, QWidget#centralWidget, QDialog {{
    background-color: {t['background']};
    color: {t['text_primary']};
}}
/* 设计稿 02/03：对话框本体是纯白卡片（#FFFFFF），不是页面底色 */
QDialog {{
    background-color: {t['surface']};
}}

/* ---- 结构容器 ---- */
QFrame#card, QFrame#ledgerCard, QFrame#previewCard, QFrame#settingsCard,
QFrame#actionsCard, QFrame#fileListCard,
QFrame#titleBar, QFrame#statusBar {{
    background-color: {t['surface']};
    border: 1px solid {t['border']};
    border-radius: {RADIUS['card']}px;
}}
/* 参数分组在「排版与输出参数」卡内直接铺排，不再嵌套卡片边框 */
QFrame#layoutCard, QFrame#modeOrderCard, QFrame#paramRow,
QFrame#ledgerHeader, QFrame#previewHeader, QFrame#cardHeader,
QFrame#cardFooter,
QFrame#segmentRow, QFrame#pillRow {{
    background: transparent;
    border: none;
    border-radius: 0px;
}}
/* 设计稿：台账页脚为 #F8FAFC 底色 + 上描边，紧贴卡片底部 */
QFrame#ledgerFooter {{
    background-color: {t['surface_alt']};
    border: none;
    border-top: 1px solid {t['border']};
    border-bottom-left-radius: {RADIUS['card']}px;
    border-bottom-right-radius: {RADIUS['card']}px;
}}
/* 设计稿：预览卡底部信息条自带 #F8FAFC 底色与上描边（占 18px 高） */
QFrame#previewFooter {{
    background-color: {t['surface_alt']};
    border: none;
    border-top: 1px solid {t['border']};
    border-bottom-left-radius: {RADIUS['card']}px;
    border-bottom-right-radius: {RADIUS['card']}px;
}}
/* 深色/浅色分段控件外框：设计稿外框是极浅的 #F1F4F8 发丝线（不是 border_strong） */
QFrame#segmented {{
    background-color: {t['surface']};
    border: 1px solid {t['surface_sunken']};
    border-radius: {RADIUS['control']}px;
}}
QLineEdit#plainInput, QFrame#cropRow {{
    background-color: {t['surface']};
    border: 1px solid {t['border_strong']};
    border-radius: {RADIUS['control']}px;
}}
/* 参数卡内的一体化控件：设计稿实测高 28px（含 1px 边） */
QFrame#cropRow {{
    min-height: 26px;
    max-height: 26px;
}}
QComboBox#paramCombo {{
    min-height: 26px;
    max-height: 26px;
    font-size: {S['body']}px;
}}
/* 裁切线复合框内的数字框：无独立描边，融入整宽复合框 */
QSpinBox#bareSpin {{
    background: transparent;
    border: none;
    padding: 0px 2px;
    min-height: 24px;
    font-size: {S['body']}px;
    color: {t['text_primary']};
}}
QSpinBox#bareSpin:focus {{ background: transparent; border: none; }}
QFrame#contextBar {{
    background-color: {t['accent_tint']};
    border: none;
    border-radius: 0px;
}}
QFrame#outputBar, QFrame#titleBar, QFrame#statusBar {{
    border-radius: 0px;
    border-left: none;
    border-right: none;
    border-top: none;
}}
QFrame#titleBar {{ border-bottom: 1px solid {t['border']}; }}
QFrame#outputBar {{ border-top: 1px solid {t['border']}; }}
QFrame#statusBar {{
    background-color: {t['surface_alt']};
    border-top: 1px solid {t['border']};
    border-bottom: none;
}}
QFrame#vSeparator {{
    background-color: {t['border_strong']};
    border: none;
    min-width: 1px;
    max-width: 1px;
}}
QFrame#dropZone {{
    background-color: {t['surface_alt']};
    border: 1px dashed {t['border_strong']};
    border-radius: {RADIUS['control']}px;
}}
QFrame#previewPlaceholder {{
    /* 设计稿：预览画布为下沉灰（#F1F4F8），虚线框只是其中的引导边界 */
    background-color: {t['surface_sunken']};
    border: 1px dashed {t['placeholder_border']};
    border-radius: {RADIUS['card']}px;
}}

/* ---- 文本 ---- */
/* 同上：QLabel 通用规则不声明 font-*，默认字体继承 app.setFont()。
   各 objectName 规则显式给出字号/字重；纯数字位数与字重由 numeric_font() 提供。 */
QLabel {{
    color: {t['text_primary']};
    background: transparent;
    border: none;
}}
QLabel#titleLabel {{ font-size: {S['heading']}px; font-weight: {W['bold']}; }}
QLabel#contextLabel {{ font-size: {S['base']}px; color: {t['text_primary']}; }}
QLabel#sectionLabel {{ font-size: {S['heading']}px; font-weight: {W['bold']}; }}
/* 设计稿：「合并预览」「排版与输出参数」为 14px/700（ink 高 13px），比台账标题小一档 */
QLabel#cardTitleLabel {{ font-size: {S['subhead']}px; font-weight: {W['bold']}; }}
QLabel#brandTitle {{ font-size: {S['title']}px; font-weight: {W['bold']}; }}
QLabel#subtitleLabel, QLabel#hintLabel, QLabel#statusLabel {{
    font-size: {S['caption']}px;
    color: {t['text_secondary']};
}}
QLabel#mutedLabel {{ font-size: {S['caption']}px; color: {t['text_muted']}; }}
/* 设计稿：含数字的次级文本位统一到 Inter + tnum。
   Qt QSS 无法启用 OpenType tnum，且 QSS 一旦声明 font-family 就会覆盖
   setFont()；因此这些控件刻意不在此处声明 font-*，字体由
   apply_numeric_text_fonts() 统一用 numeric_font() 设置（中文经字体栈回退
   Noto Sans SC）。此规则仅作为文档锚点，保留为空声明。 */
{numeric_selectors} {{
    /* font: 由 numeric_font() 单一来源提供 */
}}
/* 使用帮助 / 更新弹窗中的二维码与说明文字（替代历史内联 font-size） */
QLabel#qrcodeHint {{ font-family: {cn}; font-size: {S['base']}px; color: {t['text_secondary']}; }}
QLabel#qrcodePlaceholder {{
    font-family: {cn};
    font-size: {S['body']}px; color: {t['text_secondary']};
    border: 1px solid {t['border']}; border-radius: {RADIUS['chip']}px;
    background-color: {t['surface']};
}}
QFrame#hSeparator {{ background-color: {t['border']}; border: none; }}
QTextEdit#helpText {{ font-family: {cn}; font-size: {S['base']}px; }}
/* 字体（Inter + tnum）由 components.numeric_label() 的 setFont() 提供 */
QLabel#versionLabel {{
    color: {t['accent']};
    background-color: {t['accent_tint']};
    border: 1px solid {t['accent_border']};
    border-radius: {RADIUS['chip']}px;
    padding: 3px 8px;
}}
QLabel#monoLabel {{ background: transparent; border: none; /* 字体由 numeric_font() 提供 */ }}
QLabel#ledgerTotalLabel {{
    /* 字体（Inter + tnum + 15px/Bold）由 numeric_font() 提供，QSS 只管颜色与几何 */
    color: {t['text_primary']};
    min-height: 24px;
    max-height: 24px;
}}
QLabel#ledgerTotalCaption {{ font-size: {S['body']}px; color: {t['text_secondary']}; }}
QLabel#liveStateLabel {{ font-size: {S['caption']}px; font-weight: {W['semibold']}; color: {t['success']}; }}
QLabel#liveStateLabel[state="off"] {{ color: {t['text_muted']}; }}
QLabel#statusBarLabel {{ font-size: {S['caption']}px; color: {t['text_muted']}; }}
QLabel#footLabel {{ font-size: {S['caption']}px; color: {t['text_secondary']}; }}
QLabel#paramCaption {{ font-size: {S['body']}px; color: {t['text_secondary']}; }}
QLabel#inlineUnit {{ font-size: {S['caption']}px; color: {t['text_muted']}; }}
/* 预览卡底部的实时预览开关：仅显示文字与状态色，不绘制方框 */
QCheckBox#liveCheck {{
    background: transparent;
    border: none;
    color: {t['text_muted']};
    font-size: {S['caption']}px;
    font-weight: {W['semibold']};
    padding: 0px;
    spacing: 0px;
}}
QCheckBox#liveCheck:checked {{ color: {t['success']}; }}
QCheckBox#liveCheck::indicator {{ width: 0px; height: 0px; border: none; background: transparent; }}
/* 设计稿的计数 chip：极浅中性底（#F4F6F9）、次级灰字、无描边、12px 常规字 */
QLabel#statusChip, QLabel#warningChip, QLabel#successChip, QLabel#dangerChip {{
    font-size: {S['body']}px;
    font-weight: {W['regular']};
    border-radius: {RADIUS['chip']}px;
    padding: 1px 12px;
    border: none;
    background-color: {t['hover_bg']};
    color: {t['text_secondary']};
    min-height: 20px;
    max-height: 20px;
}}
QLabel#warningChip {{
    background-color: {t['warning_tint']};
    color: {t['warning']};
    /* 设计稿：警告 chip 带 1px 浅琥珀描边（#F0D9A8）、内边距更紧、字号 11px，
       使其总宽约 103px（含前置警示符号），比计数 chip 更紧凑。 */
    border: 1px solid {t['warning_border']};
    font-size: {S['caption']}px;
    padding: 1px 8px;
    min-height: 20px;
    max-height: 20px;
}}
QLabel#successChip {{
    background-color: {t['success_tint']};
    color: {t['success']};
}}
QLabel#dangerChip {{
    background-color: {t['danger_tint']};
    border-color: {t['danger_border']};
    color: {t['danger']};
}}

/* ---- 四级按钮 ---- */
QPushButton {{
    background-color: {t['surface']};
    color: {t['text_primary']};
    border: 1px solid {t['border_strong']};
    border-radius: {RADIUS['control']}px;
    padding: 5px 12px;
    min-height: 28px;
    font-family: {cn};
    font-size: {S['base']}px;
}}
QPushButton:hover {{ background-color: {t['hover_bg']}; border-color: {t['accent']}; }}
QPushButton:pressed {{ background-color: {t['pressed_bg']}; }}
QPushButton:disabled {{ color: {t['text_muted']}; background-color: {t['surface_alt']}; border-color: {t['border']}; }}
QPushButton#primaryButton {{
    background-color: {t['accent']};
    color: {t['accent_text']};
    border: 1px solid {t['accent']};
    font-size: {S['subhead']}px;
    font-weight: {W['bold']};
    padding: 0px 26px;
    min-height: 38px;
    max-height: 38px;
}}
QPushButton#actionButton {{
    background-color: {t['surface']};
    color: {t['text_primary']};
    border: 1px solid {t['border_strong']};
    font-size: {S['base']}px;
    padding: 0px 14px;
    /* 设计稿按钮总高 30px：QSS 的 min/max-height 是内容高度，需扣掉 1px 边框 */
    min-height: 28px;
    max-height: 28px;
}}
QPushButton#actionButton:hover {{ background-color: {t['hover_bg']}; border-color: {t['accent']}; }}
QPushButton#actionAccent {{
    background-color: {t['accent_tint']};
    color: {t['accent']};
    border: 1px solid {t['accent_border']};
    font-size: {S['base']}px;
    font-weight: {W['semibold']};
    padding: 0px 14px;
    /* 设计稿：主操作按钮比同级按钮更宽（实测总宽 92px） */
    padding: 0px 19px;
    min-height: 28px;
    max-height: 28px;
}}
QPushButton#actionAccent:hover {{ background-color: {t['accent']}; color: {t['accent_text']}; }}
QPushButton#actionDanger {{
    background-color: {t['danger_tint']};
    color: {t['danger']};
    border: 1px solid {t['danger_border']};
    font-size: {S['base']}px;
    padding: 0px 14px;
    min-height: 30px;
    max-height: 30px;
}}
QPushButton#actionDanger:hover {{ background-color: {t['danger']}; color: {t['accent_text']}; }}
/* 参数卡内的分段控件（纸张方向 / 处理模式） */
QPushButton#segmentButton {{
    background-color: transparent;
    color: {t['text_secondary']};
    border: none;
    border-radius: 5px;
    font-size: {S['body']}px;
    padding: 0px 10px;
    min-height: 24px;
    max-height: 24px;
}}
QPushButton#segmentButton:hover {{ background-color: {t['hover_bg']}; }}
QPushButton#segmentButton:checked {{
    background-color: {t['accent']};
    color: {t['accent_text']};
    font-weight: {W['bold']};
}}
QPushButton#primaryButton:hover {{ background-color: {t['accent_hover']}; border-color: {t['accent_hover']}; }}
QPushButton#primaryButton:pressed {{ background-color: {t['accent_pressed']}; }}
QPushButton#primaryButton:disabled {{
    background-color: {t['surface_alt']};
    color: {t['text_muted']};
    border-color: {t['border']};
}}
QPushButton#secondaryButton {{
    background-color: {t['surface']};
    color: {t['text_primary']};
    border: 1px solid {t['border_strong']};
    font-size: {S['base']}px;
    padding: 0px 12px;
    min-height: 26px;
    max-height: 34px;
}}
QPushButton#textButton {{
    background-color: transparent;
    color: {t['accent']};
    border: none;
    font-size: {S['body']}px;
    padding: 4px 8px;
    min-height: 24px;
}}
QPushButton#textButton:hover {{ background-color: {t['accent_tint']}; }}
/* 操作条中的「删除选中」按设计稿为白底灰边；「清空全部」用 [tone=danger] 呈现浅红 */
QPushButton#dangerButton {{
    background-color: {t['surface']};
    color: {t['text_primary']};
    border: 1px solid {t['border_strong']};
    font-size: {S['base']}px;
    padding: 0px 14px;
    min-height: 28px;
    max-height: 28px;
}}
QPushButton#dangerButton:hover {{ background-color: {t['hover_bg']}; border-color: {t['danger']}; color: {t['danger']}; }}
QPushButton#dangerButton[tone="danger"] {{
    background-color: {t['danger_tint']};
    color: {t['danger']};
    border: 1px solid {t['danger_border']};
}}
QPushButton#dangerButton[tone="danger"]:hover {{ background-color: {t['danger']}; color: {t['accent_text']}; }}
QPushButton#iconButton {{
    background-color: {t['surface']};
    color: {t['text_primary']};
    border: 1px solid {t['border_strong']};
}}
QPushButton#feedbackButton {{
    background-color: {t['accent_tint']};
    color: {t['accent']};
    border: 1px solid {t['accent_border']};
    font-weight: {W['bold']};
}}

/* ---- 表单控件（统一 28-36px 高 / 6px 圆角 / 1px 描边） ---- */
/* 通用表单规则不声明 font-family：中文默认由 app.setFont() 提供，
   纯数字输入位（QSpinBox / 路径框）由 apply_numeric_text_fonts() 用
   numeric_font() 覆盖为 Inter + tnum。声明 font-family 会覆盖 setFont()。 */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
    background-color: {t['surface']};
    color: {t['text_primary']};
    border: 1px solid {t['border_strong']};
    border-radius: {RADIUS['control']}px;
    padding: 0px 8px;
    min-height: 34px;
    font-size: {S['base']}px;
    selection-background-color: {t['selected_bg']};
    selection-color: {t['selected_text']};
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {t['accent']};
}}
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled {{
    background-color: {t['surface_alt']};
    color: {t['text_muted']};
}}
/* 设计稿：输出路径框为浅灰底（surface_alt）+ 1px 描边，等宽字体 */
/* 路径框字体（Inter + tnum / 12px）由 apply_numeric_text_fonts() 的 setFont() 提供 */
QLineEdit#pathInput {{
    font-size: {S['body']}px;
    background-color: {t['surface_alt']};
    border: 1px solid {t['border_strong']};
    border-radius: {RADIUS['control']}px;
}}
QLineEdit#ruleInput {{ font-family: {cn}; /* 规则含中文占位符，必须中文栈 */ }}
/* 参数卡内的数字框：设计稿实测控件高 28px、字号 12px */
QSpinBox#paramSpin {{
    font-size: {S['body']}px;
    padding: 0px 6px;
    min-height: 26px;
    max-height: 26px;
}}
QTextEdit {{
    background-color: {t['surface']};
    color: {t['text_primary']};
    border: 1px solid {t['border']};
    border-radius: {RADIUS['card']}px;
    padding: 12px;
    font-family: {cn};
    font-size: {S['base']}px;
}}
QFrame#dialogHeader, QFrame#dialogFooter {{
    background-color: {t['surface']};
    border: 1px solid {t['border']};
    border-radius: {RADIUS['card']}px;
}}
/* 设计稿 02：对话框顶栏是白底 + 1px 底边（不是独立圆角卡片） */
QFrame#dialogHeader {{
    border: none;
    border-bottom: 1px solid {t['border']};
    border-radius: 0px;
}}
QLabel#dialogTitle {{ font-size: {S['dialog']}px; font-weight: {W['bold']}; color: {t['text_primary']}; }}
QLabel#dialogSectionTitle {{ font-size: {S['heading']}px; font-weight: {W['bold']}; color: {t['text_primary']}; }}
QLabel#exampleValue {{ color: {t['success']}; /* 字体由 numeric_font() 提供 */ }}
/* 设计稿 02：使用说明是浅灰圆角块（不是白卡） */
QFrame#helpCard {{
    background-color: {t['surface_alt']};
    border: 1px solid {t['border']};
    border-radius: {RADIUS['control']}px;
}}
QLabel#helpCardTitle {{ font-size: {S['body']}px; font-weight: {W['bold']}; color: {t['text_primary']}; }}
QLabel#helpCardText {{ font-size: {S['caption']}px; color: {t['text_secondary']}; }}
QComboBox::drop-down {{ border: none; width: 18px; }}
/* 设计稿：下拉框右端有一枚 chevron 箭头（QSS 覆盖后默认箭头不再绘制，需显式指定） */
QComboBox::down-arrow {{ image: {chevron}; width: 12px; height: 12px; }}
QComboBox QAbstractItemView {{
    background-color: {t['surface']};
    color: {t['text_primary']};
    border: 1px solid {t['border']};
    selection-background-color: {t['selected_bg']};
}}
QSpinBox::up-button, QSpinBox::down-button {{ width: 0px; border: none; }}
QCheckBox, QRadioButton {{
    color: {t['text_primary']};
    font-family: {cn};
    font-size: {S['base']}px;
    spacing: 7px;
    background: transparent;
}}
QCheckBox::indicator, QRadioButton::indicator {{
    width: 14px; height: 14px;
    border: 1px solid {t['border_strong']};
    background-color: {t['surface']};
}}
QRadioButton::indicator {{ border-radius: 7px; }}
QCheckBox::indicator {{ border-radius: 3px; }}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
    background-color: {t['accent']};
    border-color: {t['accent']};
}}
/* 设计稿：复选选中态为蓝底白色对勾，而非纯蓝方块 */
QCheckBox::indicator:checked {{ image: {check_mark}; }}
QCheckBox::indicator:hover, QRadioButton::indicator:hover {{ border-color: {t['accent']}; }}
/* 参数卡底部的勾选胶囊（一式两份 / 合并后打开 / 合并后打印） */
QCheckBox#pillCheck {{
    background-color: {t['surface']};
    border: 1px solid {t['border_strong']};
    border-radius: {RADIUS['control']}px;
    padding: 0px 10px;
    /* 24 + 上下各 1px 边框 = 设计稿实测的 26px 胶囊高度 */
    min-height: 24px;
    max-height: 24px;
    font-size: {S['body']}px;
}}
QCheckBox#pillCheck:checked {{
    background-color: {t['accent_tint']};
    border-color: {t['accent_border']};
    color: {t['accent']};
    font-weight: {W['semibold']};
}}
QCheckBox#pillCheck:disabled {{ color: {t['text_muted']}; background-color: {t['surface_alt']}; }}

/* ---- 台账表格（9 列，交替行色，等宽数字由代码设置） ---- */
QTableWidget, QTableView {{
    background-color: {t['surface']};
    color: {t['text_primary']};
    border: none;
    gridline-color: {t['border']};
    alternate-background-color: {t['alt_row']};
    font-family: {cn};
    font-size: {S['body']}px;
    outline: none;
}}
/* 设计稿台账无网格线、无行分隔线，仅靠交替行底色区分。
   注意：这里不能写 border 属性——只要 ::item 里出现 border（哪怕 none/0 或透明），
   Qt 就会接管单元格绘制并丢弃 item 的 BackgroundRole，重复行的淡琥珀底色随之消失。 */
/* 注意：这里只能写 padding/margin，不能出现任何 border 声明。
   一旦出现 border，Qt 会接管单元格绘制并丢弃 BackgroundRole，
   重复行的淡琥珀底色就会消失。 */
/* 内边距 4px：设计稿发票号码列固定 151px，Inter+tnum 11px 的 20 位数字实测
   宽 140px；6px 内边距时可用仅 139px 会触发省略号，收紧到 4px 后可用 143px。
   注意：此处只能写 padding/margin，不能出现任何 border 声明。
   一旦出现 border，Qt 会接管单元格绘制并丢弃 BackgroundRole，
   重复行的淡琥珀底色就会消失。 */
QTableWidget::item {{ padding: 0px 4px; }}
QTableWidget::item:selected {{
    background-color: {t['selected_bg']};
    color: {t['selected_text']};
}}
QHeaderView {{ background-color: {t['surface_alt']}; }}
/* 表头文字颜色由 file_list.py 逐列设置（「金额」列为主色），此处不写 color 以免覆盖；
   设计稿表头与数据区之间没有分隔线，只有底色差异。 */
QHeaderView::section {{
    background-color: {t['surface_alt']};
    border: none;
    padding: 0px 6px;
    min-height: 34px;
    /* 表头字体（字号/字体族/字重）由 file_list.py::_apply_header_colors()
       通过 tokens.header_font() 单一来源设置；此处只管底色与尺寸，
       避免 QSS 与 setFont() 互相覆盖。 */
}}
QTableCornerButton::section {{ background-color: {t['surface_alt']}; border: none; }}

/* ---- 预览与进度 ---- */
QScrollArea {{ background-color: {t['scroll_bg']}; border: none; }}
QSplitter::handle {{ background-color: transparent; }}
/* 设计稿 01：左右两栏之间是 14px 的页面底色留白（#F4F6F9），不是一条描边色带 */
QSplitter::handle:horizontal {{ width: 16px; }}
QProgressBar {{
    background-color: {t['surface_alt']};
    border: none;
    border-radius: 3px;
    height: 6px;
    max-height: 6px;
    text-align: center;
    color: {t['text_secondary']};
    font-size: {S['micro']}px;
}}
QProgressBar::chunk {{ background-color: {t['accent']}; border-radius: 3px; }}
QProgressBar#feedbackBar {{ height: 8px; }}
QProgressBar#inlineProgress {{ height: 4px; max-height: 4px; border-radius: 2px; }}
QProgressBar#inlineProgress::chunk {{ border-radius: 2px; }}
/* 预览画布区：设计稿为浅灰底（surface_sunken），A4 页面在其中居中 */
QStackedWidget#previewStack {{ background-color: {t['surface_sunken']}; border: none; }}
QScrollArea#previewScroll {{ background-color: {t['surface_sunken']}; }}
QScrollArea#previewScroll > QWidget > QWidget {{ background-color: {t['surface_sunken']}; }}
QLabel#feedbackLabel {{
    background: transparent;
    color: {t['text_secondary']};
    border: none;
    padding: 1px 0px;
    font-size: {S['body']}px;
}}
QLabel#feedbackLabel[state="success"] {{
    background-color: {t['success_tint']}; color: {t['success']};
    border: 1px solid {t['success_border']};
    border-radius: {RADIUS['chip']}px;
    padding: 3px 8px;
}}
QLabel#feedbackLabel[state="warning"] {{
    background-color: {t['warning_tint']}; color: {t['warning']};
    border: 1px solid {t['warning_border']};
    border-radius: {RADIUS['chip']}px;
    padding: 3px 8px;
}}
QLabel#feedbackLabel[state="danger"] {{
    background-color: {t['danger_tint']}; color: {t['danger']};
    border: 1px solid {t['danger_border']};
    border-radius: {RADIUS['chip']}px;
    padding: 3px 8px;
}}

/* ---- 菜单与弹窗 ---- */
QMenu {{
    background-color: {t['surface']};
    color: {t['text_primary']};
    border: 1px solid {t['border']};
    border-radius: {RADIUS['control']}px;
    padding: 6px;
}}
QMenu::item {{ padding: 7px 20px; border-radius: {RADIUS['chip']}px; }}
QMenu::item:selected {{ background-color: {t['selected_bg']}; color: {t['selected_text']}; }}
QMenu::separator {{ height: 1px; background-color: {t['border']}; margin: 6px 4px; }}
QMenu::item#dangerAction {{ color: {t['danger']}; }}
QLabel#dangerMenuLabel {{
    color: {t['danger']};
    font-size: {S['body']}px;
    font-weight: {W['semibold']};
    background: transparent;
    border: none;
}}
QTabWidget::pane {{ border: 1px solid {t['border']}; background-color: {t['surface']}; }}
QTabBar::tab {{
    background-color: {t['surface_alt']};
    color: {t['text_secondary']};
    padding: 7px 14px;
    border: 1px solid {t['border']};
}}
QTabBar::tab:selected {{ background-color: {t['surface']}; color: {t['accent']}; }}
/* 设计稿 02：字段芯片 30px 高、12px 字；蓝色通用、灰色专属 */
QPushButton#fieldChip {{
    background-color: {t['accent_tint']};
    color: {t['accent']};
    border: 1px solid {t['accent_border']};
    border-radius: {RADIUS['control']}px;
    font-size: {S['body']}px;
    padding: 0px 12px;
    min-height: 30px;
    max-height: 30px;
}}
QPushButton#fieldChipExtra {{
    background-color: {t['surface_alt']};
    color: {t['text_secondary']};
    border: 1px solid {t['border']};
    border-radius: {RADIUS['control']}px;
    font-size: {S['body']}px;
    padding: 0px 12px;
    min-height: 30px;
    max-height: 30px;
}}
QMessageBox {{ background-color: {t['surface']}; }}

/* ---- 批量重命名对话框（设计稿 02）---- */
QFrame#typeNav {{
    background-color: {t['surface_alt']};
    border: none;
    border-right: 1px solid {t['border']};
    border-radius: 0px;
}}
QLabel#typeNavTitle {{ font-size: {S['caption']}px; color: {t['text_muted']}; }}
QPushButton#typeNavButton {{
    background-color: transparent;
    color: {t['text_primary']};
    border: none;
    border-radius: {RADIUS['control']}px;
    text-align: left;
    font-size: {S['base']}px;
    padding: 0px 12px;
}}
QPushButton#typeNavButton:hover {{ background-color: {t['hover_bg']}; }}
QPushButton#typeNavButton:checked {{
    background-color: {t['accent_tint']};
    color: {t['accent']};
    font-weight: {W['semibold']};
}}
QPushButton#helpButton, QPushButton#closeButton {{
    background-color: {t['surface']};
    color: {t['text_primary']};
    border: 1px solid {t['border_strong']};
}}
/* 设计稿 02：保存为白底主色描边按钮，只有「执行重命名」是主色实心 */
QPushButton#saveButton {{
    background-color: {t['surface']};
    color: {t['accent']};
    border: 1px solid {t['accent']};
    font-weight: {W['regular']};
}}
QPushButton#executeButton {{
    background-color: {t['accent']};
    color: {t['accent_text']};
    border: 1px solid {t['accent']};
    font-weight: {W['semibold']};
}}
QPushButton#executeButton:hover {{ background-color: {t['accent_hover']}; }}
QPushButton#clearButton {{
    background-color: {t['danger_tint']};
    color: {t['danger']};
    border: 1px solid {t['danger_border']};
}}
"""


def apply_application_style(app, dark: Optional[bool] = None) -> None:
    """
    注册打包字体、注入全局 QSS，并把应用默认字体设为设计稿正文（供 main.py 调用）。

    顺序至关重要：必须先注册 Inter / Noto Sans SC 两个可变字体，再 setStyleSheet，
    否则 QSS 里的字体名会回退到系统里另一个字形的字体（此前 Geist Mono 回退 Arial）。
    """
    # 幂等；缺字体文件/无 GUI 环境时静默跳过，由系统字体栈兜底。
    register_bundled_fonts()

    try:
        app.setStyleSheet(build_stylesheet(dark))
    except Exception:
        # 无 Qt 环境时静默跳过，保证纯逻辑测试仍可导入本模块
        return

    try:
        from PySide6.QtGui import QFont, QFontDatabase

        available = set(QFontDatabase.families())
        # 只在字体确实存在时覆盖应用字体；否则保留 Qt 默认字体，
        # 让 Windows 的字体回退/字体链接负责显示中文，避免强制不存在的字体导致方框。
        for family in FONT_CN_FAMILIES:
            if family in available:
                base_font = QFont(family)
                # 设计稿正文 Regular 13px（此前 QFont(family, 9) = 12px 偏小、发虚）；
                # 显式 400 避免可变字体被解析到 Thin 实例。
                base_font.setPixelSize(FONT_BODY_PIXEL_SIZE)
                base_font.setWeight(QFont.Weight.Normal)
                app.setFont(base_font)
                break
    except Exception:
        pass


def apply_numeric_text_fonts(root) -> int:
    """
    给控件树中 ``NUMERIC_TEXT_OBJECTS`` 列出的文本位统一设置 Inter + tnum 字体。

    设计稿的数字节点 fontFamily 为 Inter；Qt QSS 不支持 OpenType ``tnum``，
    且 QSS 声明 font-family 会覆盖 ``setFont()``，因此这些控件在 QSS 中
    不声明字体族，改由此函数集中设置（含中文回退族），保证：
      - 数字字形 = Inter、启用 tnum（等宽数字）
      - 中文 = Noto Sans SC（经 setFamilies 回退链）
      - 字号 = QSS 中各 objectName 的 font-size（NUMERIC_TEXT_SIZES 与之对齐）

    必须在窗口/对话框构建完成、且已 setStyleSheet() 之后调用。返回处理数量。
    """
    try:
        from PySide6.QtWidgets import QWidget
    except Exception:
        return 0
    if not isinstance(root, QWidget):
        return 0

    fonts = {name: numeric_font(size) for name, size in NUMERIC_TEXT_SIZES.items()}
    fonts.update(
        {name: numeric_font(size) for name, size in NUMERIC_INPUT_OBJECTS.items()}
    )
    applied = 0
    for widget in root.findChildren(QWidget):
        font = fonts.get(widget.objectName())
        if font is not None:
            widget.setFont(font)
            applied += 1
    return applied


def clear_inline_styles(root, keep_object_names: Iterable[str] = ()) -> int:
    """
    清除控件树上遗留的逐控件 setStyleSheet，使全局 QSS 生效。

    返回被清除的控件数量。``keep_object_names`` 中的 objectName 保留内联样式，
    用于处理少数需要特殊绘制的控件。
    """
    try:
        from PySide6.QtWidgets import QWidget
    except Exception:
        return 0

    keep = set(keep_object_names)
    cleared = 0
    if not isinstance(root, QWidget):
        return cleared
    for widget in root.findChildren(QWidget):
        if widget.objectName() in keep:
            continue
        if widget.styleSheet():
            widget.setStyleSheet("")
            cleared += 1
    return cleared
