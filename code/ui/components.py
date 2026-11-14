#!/usr/bin/env python3
"""
可复用 UI 组件工厂

所有控件只设置 objectName，具体配色/尺寸由 ``ui.tokens.build_stylesheet()``
生成的全局 QSS 统一提供。四级按钮层级与状态组件在此集中定义，避免主窗口、
台账与弹窗各自复制样式代码。
"""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout


def _button(text: str, object_name: str, parent=None) -> QPushButton:
    btn = QPushButton(text, parent)
    btn.setObjectName(object_name)
    return btn


def primary_button(text: str, parent=None) -> QPushButton:
    """主按钮：每个界面区域至多一个（当前仅「合并 PDF」）。"""
    return _button(text, "primaryButton", parent)


def secondary_button(text: str, parent=None) -> QPushButton:
    """次按钮：普通操作。"""
    return _button(text, "secondaryButton", parent)


def text_button(text: str, parent=None) -> QPushButton:
    """文字按钮：低权重操作（刷新、帮助、检查更新）。"""
    return _button(text, "textButton", parent)


def danger_button(text: str, parent=None) -> QPushButton:
    """危险按钮：删除、清空等破坏性操作。"""
    return _button(text, "dangerButton", parent)


def section_card(object_name: str = "card", layout: str = "vertical", parent=None) -> QFrame:
    """创建一张卡片容器并返回，调用方通过 ``card.layout()`` 添加内容。"""
    card = QFrame(parent)
    card.setObjectName(object_name)
    card.setFrameShape(QFrame.Shape.StyledPanel)
    if layout == "horizontal":
        box = QHBoxLayout(card)
    else:
        box = QVBoxLayout(card)
    box.setContentsMargins(12, 12, 12, 12)
    box.setSpacing(8)
    return card


def label(text: str, object_name: str = "", parent=None) -> QLabel:
    """创建文本标签，objectName 决定全局 QSS 中的字号与颜色。"""
    lbl = QLabel(text, parent)
    if object_name:
        lbl.setObjectName(object_name)
    return lbl


def status_chip(text: str, kind: str = "info", parent=None) -> QLabel:
    """状态标签：info / success / warning / danger 四种语义。"""
    mapping = {
        "info": "statusChip",
        "success": "successChip",
        "warning": "warningChip",
        "danger": "dangerChip",
    }
    return label(text, mapping.get(kind, "statusChip"), parent)


def feedback_label(parent=None) -> QLabel:
    """加载 / 空 / 错误 / 成功共用的回执标签。"""
    lbl = label("", "feedbackLabel", parent)
    lbl.setProperty("state", "info")
    lbl.setVisible(False)
    return lbl


def set_feedback(lbl: QLabel, text: str, state: str = "info") -> None:
    """更新回执文案与语义状态，并强制 Qt 重新应用属性选择器样式。"""
    lbl.setText(text)
    lbl.setProperty("state", state)
    lbl.setVisible(bool(text))
    style = lbl.style()
    style.unpolish(lbl)
    style.polish(lbl)
    lbl.update()


def mono_label(text: str, parent=None) -> QLabel:
    """等宽数字标签（金额、合计、发票号码）。"""
    return label(text, "monoLabel", parent)


def numeric_label(
    text: str,
    object_name: str = "numericLabel",
    pixel_size: int = 12,
    weight=None,
    parent=None,
) -> QLabel:
    """
    纯数字 / 金额展示位标签。

    字体（Inter + OpenType ``tnum`` 等宽数字）由 ``ui.tokens.numeric_font()``
    通过 ``setFont()`` 单一来源设置；QSS 中对应 objectName 只负责颜色与几何，
    不声明任何 font-*，否则 Qt QSS 会覆盖 setFont() 导致 tnum 失效。

    参数:
        object_name: 供 QSS 绑定颜色/尺寸的 objectName
        pixel_size: 字号（px），取 ``tokens.FONT_SIZE`` 档位
        weight: 字重，取 ``tokens.FONT_WEIGHT`` 档位；None 表示常规
    """
    from ui.tokens import numeric_font

    lbl = label(text, object_name, parent)
    lbl.setFont(numeric_font(pixel_size, weight))
    return lbl
