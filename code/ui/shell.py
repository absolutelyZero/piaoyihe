#!/usr/bin/env python3
"""
主窗口五段式外壳构建器

把「标题栏 → 上下文提示条 →〔左台账 ｜ 右预览+参数〕→ 输出提交条 → 状态栏」
的结构与新增状态组件集中在本模块；``MainWindow`` 只保留原有控件变量名、
信号槽与业务 handler，满足「业务逻辑零改动、功能全量保留」的约束。

设计基线：req/ui/01-主工作台-完整界面.png、req/ui/04-深色模式.png
"""

from __future__ import annotations

import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ui.tokens import (
    FONT_SIZE, FONT_WEIGHT, numeric_font, apply_numeric_text_fonts,
)
from ui.components import (
    feedback_label,
    label,
    mono_label,
    primary_button,
    secondary_button,
    set_feedback,
    status_chip,
    text_button,
    section_card,
)
from ui.file_list import FileListPanel
from ui.tokens import clear_inline_styles



# ---------------------------------------------------------------------------
# 通用图标
# ---------------------------------------------------------------------------
def tinted_icon_label(window, filename: str, size: int) -> QLabel:
    """
    把 res/icons 中固定深色的 SVG 图标改为中性灰蓝，使其在浅色与深色
    主题下都可见（图标仍复用仓库现有资源，不引入新文件或联网资源）。
    """
    from PySide6.QtCore import QByteArray
    from PySide6.QtGui import QPainter, QPixmap
    from PySide6.QtSvg import QSvgRenderer

    label = QLabel()
    label.setFixedSize(size, size)
    try:
        path = os.path.join(window.icon_dir, filename)
        with open(path, "r", encoding="utf-8") as fh:
            svg = fh.read().replace("#333", "#8A97A8")
        renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        label.setPixmap(pixmap)
    except Exception:
        return window._icon_label(filename, size)
    return label


# ---------------------------------------------------------------------------
# 单段构建
# ---------------------------------------------------------------------------
def create_ledger_column(window) -> QWidget:
    """左侧主视觉区：票据台账（9 列）+ 空态投放带 + 页脚统计 + 操作条。"""
    column = QWidget()
    box = QVBoxLayout(column)
    box.setContentsMargins(0, 0, 0, 0)
    box.setSpacing(12)

    # --- 台账卡片 ---
    window.ledger_card = section_card("ledgerCard")
    card_box = window.ledger_card.layout()
    card_box.setContentsMargins(0, 0, 0, 0)
    card_box.setSpacing(0)

    header = QFrame()
    header.setObjectName("ledgerHeader")
    header.setFixedHeight(56)
    header_box = QHBoxLayout(header)
    header_box.setContentsMargins(16, 10, 16, 10)
    header_box.setSpacing(10)

    window.file_list_label = label("票据台账", "sectionLabel")
    header_box.addWidget(window.file_list_label)
    window.ledger_count_label = status_chip("0 张")
    header_box.addWidget(window.ledger_count_label)
    header_box.addStretch(1)
    window.ledger_total_caption = label("合计", "ledgerTotalCaption")
    header_box.addWidget(window.ledger_total_caption)
    window.ledger_total_label = mono_label("¥0.00")
    window.ledger_total_label.setObjectName("ledgerTotalLabel")
    window.ledger_total_label.setFont(
        numeric_font(FONT_SIZE["title"], FONT_WEIGHT["bold"])
    )
    header_box.addWidget(window.ledger_total_label)
    window.ledger_warning_chip = status_chip("", "warning")
    window.ledger_warning_chip.setVisible(False)
    header_box.addWidget(window.ledger_warning_chip)
    header_box.addWidget(label("点击列头排序", "mutedLabel"))
    card_box.addWidget(header)

    # 文件列表组件：全部原有交互（列头排序、悬停浮窗、右键菜单、拖放）保持不变
    window.file_list = FileListPanel(
        window.pdf_handler, on_file_added=window._on_first_file_added
    )
    window.file_list.selection_changed.connect(window._on_list_selection_changed)
    window.file_list.duplicate_count_changed.connect(window._on_duplicate_count_changed)
    # 增量添加 / 拖拽排序后立即刷新台账统计（不触发预览重建）
    window.file_list.file_added.connect(lambda _path: update_status_bar(window))
    window.file_list.order_changed.connect(lambda: update_status_bar(window))
    card_box.addWidget(window.file_list, 1)

    # --- 虚线投放带 / 空态引导（仅台账为空时显示） ---
    window.drop_zone = QFrame()
    window.drop_zone.setObjectName("dropZone")
    drop_box = QVBoxLayout(window.drop_zone)
    drop_box.setContentsMargins(24, 24, 24, 24)
    drop_box.setSpacing(8)
    drop_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
    drop_icon = tinted_icon_label(window, "加_plus.svg", 28)
    drop_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
    drop_box.addWidget(drop_icon)
    drop_box.addWidget(
        label("拖入发票文件　·　支持 PDF / PNG / JPG / OFD，自动识别字段并检查重复", "statusLabel")
    )
    drop_box.addWidget(
        label("列表顺序即打印顺序　·　右键可打开 / 在文件夹中显示 / 删除 / 导出列表", "mutedLabel")
    )
    # 投放带挂在表格视口上：只覆盖九列表头下方的数据行区，表头始终可见
    window.file_list.set_empty_overlay(window.drop_zone)

    # --- 台账页脚 ---
    footer = QFrame()
    footer.setObjectName("ledgerFooter")
    footer_box = QHBoxLayout(footer)
    footer_box.setContentsMargins(16, 8, 16, 8)
    footer_box.setSpacing(10)
    window.ledger_record_label = label("共 0 条　·　当前选中 0 条　·　列表顺序打印", "footLabel")
    footer_box.addWidget(window.ledger_record_label)
    footer_box.addStretch(1)
    window.ledger_footer_total = mono_label("¥0.00")
    window.ledger_footer_total.setObjectName("ledgerTotalLabel")
    window.ledger_footer_total.setFont(
        numeric_font(FONT_SIZE["title"], FONT_WEIGHT["bold"])
    )
    footer_box.addWidget(window.ledger_footer_total)
    card_box.addWidget(footer)

    box.addWidget(window.ledger_card, 1)

    # --- 列表操作条（七个入口全部保留，纯文字 + 分组竖线） ---
    window.actions_card = window._create_actions_widget()
    window.actions_card.setObjectName("actionsCard")
    box.addWidget(window.actions_card)

    return column


def create_preview_card(window) -> QFrame:
    """右侧上半部：合并预览（空态 / 图像页 / 页码 / 缩放 / 刷新 / 实时预览状态）。"""
    card = QFrame()
    card.setObjectName("previewCard")
    box = QVBoxLayout(card)
    box.setContentsMargins(0, 0, 0, 0)
    box.setSpacing(0)

    header = QFrame()
    header.setObjectName("previewHeader")
    header.setFixedHeight(44)
    hbox = QHBoxLayout(header)
    hbox.setContentsMargins(16, 10, 16, 10)
    hbox.setSpacing(8)
    hbox.addWidget(label("合并预览", "cardTitleLabel"))
    window.preview_status_label = QLabel("")
    window.preview_status_label.setObjectName("subtitleLabel")
    # 设计稿 01：标题后不显示文件数（该信息已在台账标题与状态栏出现），
    # 仅保留属性以兼容功能矩阵测试与既有逻辑。
    window.preview_status_label.setVisible(False)
    hbox.addWidget(window.preview_status_label)
    hbox.addStretch(1)
    window.preview_page_label = label("第 1 页 / 共 0 页", "statusLabel")
    hbox.addWidget(window.preview_page_label)
    window.preview_zoom_label = mono_label("80%")
    window.preview_zoom_label.setFont(numeric_font(FONT_SIZE["body"]))
    hbox.addWidget(window.preview_zoom_label)
    window.refresh_preview_btn = text_button("刷新")
    window.refresh_preview_btn.setToolTip("手动刷新预览")
    window.refresh_preview_btn.clicked.connect(window._update_preview)
    window.refresh_preview_btn.setEnabled(False)
    hbox.addWidget(window.refresh_preview_btn)
    box.addWidget(header)

    window.preview_stack = QStackedWidget()
    window.preview_stack.setObjectName("previewStack")

    placeholder = QFrame()
    placeholder.setObjectName("previewPlaceholder")
    pbox = QVBoxLayout(placeholder)
    pbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
    pbox.setSpacing(10)
    pbox.setContentsMargins(20, 20, 20, 20)
    window.preview_placeholder_icon = tinted_icon_label(window, "笔记_notes.svg", 40)
    window.preview_placeholder_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
    pbox.addWidget(window.preview_placeholder_icon)
    window.preview_placeholder = QLabel(
        "添加发票后自动生成合并预览\n\n配置变更后自动刷新 · Ctrl + 滚轮缩放 10%–500%"
    )
    window.preview_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
    window.preview_placeholder.setObjectName("subtitleLabel")
    pbox.addWidget(window.preview_placeholder)
    window.preview_stack.addWidget(placeholder)

    window.preview_scroll = QScrollArea()
    window.preview_scroll.setObjectName("previewScroll")
    window.preview_scroll.setWidgetResizable(True)
    window.preview_container = QWidget()
    window.preview_layout = QVBoxLayout(window.preview_container)
    window.preview_layout.setSpacing(12)
    window.preview_layout.setContentsMargins(16, 16, 16, 16)
    window.preview_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    window.preview_scroll.setWidget(window.preview_container)
    window.preview_stack.addWidget(window.preview_scroll)
    window.preview_stack.setCurrentIndex(0)

    window.preview_pixmaps = []
    window.preview_scale = 0.8
    window.preview_labels = []
    window.preview_scroll.viewport().installEventFilter(window)
    box.addWidget(window.preview_stack, 1)

    footer = QFrame()
    footer.setObjectName("previewFooter")
    footer_box = QHBoxLayout(footer)
    footer_box.setContentsMargins(16, 6, 16, 6)
    footer_box.setSpacing(8)
    window.preview_summary_label = label("A4 横向　·　2 × 2　·　每页 4 张", "statusLabel")
    footer_box.addWidget(window.preview_summary_label)
    footer_box.addStretch(1)
    # 实时预览开关：设计稿位于预览卡底部右侧，以「实时预览：开」的绿色状态呈现
    window.preview_checkbox = QCheckBox("实时预览：开")
    window.preview_checkbox.setObjectName("liveCheck")
    window.preview_checkbox.setToolTip("关闭后不再渲染预览，提升性能")
    window.preview_checkbox.setChecked(True)
    window.preview_checkbox.stateChanged.connect(window._on_preview_checkbox_changed)
    window.preview_checkbox.stateChanged.connect(lambda _s: update_live_state(window))
    footer_box.addWidget(window.preview_checkbox)
    box.addWidget(footer)

    return card


# ---------------------------------------------------------------------------
# 分段控件（纸张方向 / 处理模式）：选中段蓝底白字，替代 radio 圆点与下拉框
# ---------------------------------------------------------------------------
def _segmented(window, labels):
    """构建分段控件，返回 (frame, [button, ...])。"""
    frame = QFrame()
    frame.setObjectName("segmented")
    # 设计稿实测：分段控件外框高 28px，内部实心段高 24px
    frame.setFixedHeight(28)
    box = QHBoxLayout(frame)
    box.setContentsMargins(2, 2, 2, 2)
    box.setSpacing(2)
    group = QButtonGroup(frame)
    group.setExclusive(True)
    buttons = []
    for text in labels:
        button = QPushButton(text)
        button.setObjectName("segmentButton")
        button.setCheckable(True)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        group.addButton(button)
        box.addWidget(button, 1)
        buttons.append(button)
    return frame, buttons


def update_live_state(window) -> None:
    """同步预览卡底部「实时预览：开 / 关」状态文案。"""
    try:
        enabled = window.preview_checkbox.isChecked()
        window.preview_checkbox.setText("实时预览：开" if enabled else "实时预览：关")
        window.preview_checkbox.setProperty("state", "on" if enabled else "off")
        style = window.preview_checkbox.style()
        style.unpolish(window.preview_checkbox)
        style.polish(window.preview_checkbox)
    except Exception:
        pass


def _param_row(card, title):
    """参数面板中的一行：固定宽度标签 + 控件（由调用方继续 addWidget）。

    设计稿实测（req/ui/01）：参数卡内容左缘 12px，标签列 76px + 8px 间距，
    控件列自卡片左缘 96px 起；行距 38px，控件高 28px。
    """
    row = QFrame()
    row.setObjectName("paramRow")
    row.setFixedHeight(38)
    box = QHBoxLayout(row)
    box.setContentsMargins(12, 0, 12, 0)
    box.setSpacing(8)
    caption = label(title, "paramCaption")
    caption.setFixedWidth(76)
    box.addWidget(caption)
    card.layout().addWidget(row)
    return box


def _spin(window, min_value, max_value, value, prefix="", width=64):
    spin = QSpinBox()
    spin.setRange(min_value, max_value)
    spin.setValue(value)
    if prefix:
        spin.setPrefix(prefix)
    spin.setFixedWidth(width)
    # 设计稿实测：参数卡内数字框高 26px（由 #paramSpin 统一约束）
    spin.setObjectName("paramSpin")
    spin.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
    return spin


def create_layout_card(window) -> QFrame:
    """
    纸张与布局参数（v3：单层表单，纸张方向改为分段控件）

    控件变量名、取值范围、默认值与信号连接全部保持与改造前一致：
    ``radio_portrait`` / ``radio_landscape`` 仍为 QRadioButton（隐藏的语义载体），
    分段按钮与之双向同步，因此配置文件读写与状态栏逻辑无需改动。
    """
    card = QFrame()
    card.setObjectName("layoutCard")
    box = QVBoxLayout(card)
    box.setContentsMargins(0, 0, 0, 0)
    box.setSpacing(0)

    # 纸张方向：隐藏 radio 承载语义 + 分段按钮承载视觉
    row = _param_row(card, "纸张方向")
    window.orientation_button_group = QButtonGroup(card)
    window.radio_portrait = QRadioButton("竖向 A4")
    window.radio_landscape = QRadioButton("横向 A4")
    window.orientation_button_group.addButton(window.radio_portrait)
    window.orientation_button_group.addButton(window.radio_landscape)
    row.addWidget(window.radio_portrait)
    row.addWidget(window.radio_landscape)
    window.radio_portrait.setVisible(False)
    window.radio_landscape.setVisible(False)

    segment, segments = _segmented(window, ["竖向 A4", "横向 A4"])
    row.addWidget(segment, 1)

    def _sync_orientation(*_):
        segments[0].setChecked(window.radio_portrait.isChecked())
        segments[1].setChecked(window.radio_landscape.isChecked())

    def _choose_orientation(landscape):
        if landscape:
            window.radio_landscape.setChecked(True)
        else:
            window.radio_portrait.setChecked(True)
        _sync_orientation()

    window.radio_portrait.setChecked(True)
    window.radio_portrait.toggled.connect(
        lambda checked: checked and window._on_config_changed()
    )
    window.radio_landscape.toggled.connect(
        lambda checked: checked and window._on_config_changed()
    )
    window.radio_portrait.toggled.connect(_sync_orientation)
    window.radio_landscape.toggled.connect(_sync_orientation)
    segments[0].clicked.connect(lambda: _choose_orientation(False))
    segments[1].clicked.connect(lambda: _choose_orientation(True))
    _sync_orientation()
    window.orientation_segments = segments

    # 行列（1–10）：设计稿两框各 100 宽（x=1102..1202 / 1208..1308）
    row = _param_row(card, "排版布局")
    window.row_spinbox = _spin(window, 1, 10, 2, "行  ", 100)
    window.col_spinbox = _spin(window, 1, 10, 2, "列  ", 100)
    row.setSpacing(6)
    row.addWidget(window.row_spinbox)
    row.addWidget(window.col_spinbox)
    row.addWidget(label("1–10", "inlineUnit"))
    row.addStretch(1)
    window.row_spinbox.valueChanged.connect(window._on_config_changed)
    window.col_spinbox.valueChanged.connect(window._on_config_changed)

    # 四边页边距（0–50 mm）：设计稿四框各 64 宽、间距 6
    row = _param_row(card, "页边距 mm")
    row.setSpacing(6)
    window.default_margins = {'top': 10, 'bottom': 10, 'left': 10, 'right': 10}
    window.margin_top_spinbox = _spin(window, 0, 50, window.default_margins['top'], "上 ", 64)
    window.margin_bottom_spinbox = _spin(window, 0, 50, window.default_margins['bottom'], "下 ", 64)
    window.margin_left_spinbox = _spin(window, 0, 50, window.default_margins['left'], "左 ", 64)
    window.margin_right_spinbox = _spin(window, 0, 50, window.default_margins['right'], "右 ", 64)
    for widget in (
        window.margin_top_spinbox, window.margin_bottom_spinbox,
        window.margin_left_spinbox, window.margin_right_spinbox,
    ):
        row.addWidget(widget)
        widget.valueChanged.connect(window._on_margin_changed)
    row.addStretch(1)

    # 裁切线：整宽复合框「☑ 显示裁切线 · 左 0 mm · 右 0 mm」
    row = _param_row(card, "裁切线")
    crop_row = QFrame()
    crop_row.setObjectName("cropRow")
    crop_box = QHBoxLayout(crop_row)
    crop_box.setContentsMargins(10, 0, 10, 0)
    crop_box.setSpacing(6)
    window.crop_mark_checkbox = QCheckBox("显示裁切线")
    window.crop_mark_checkbox.setToolTip("开启后绘制左右两侧的裁切线，便于裁剪")
    window.default_crop_mark_dist = 0
    # 设计稿：数字与单位紧贴（「左 0 mm」），单位作为后缀内嵌，避免出现大段空隙。
    # 宽度 64px 与上方「页边距」四个数字框同宽；前缀只留 1 个空格：中文栈换雅黑后
    # 「左  0 mm」（2 空格）实测 53px 而内容区仅 52px，末尾的 m 会被削掉；1 个空格
    # 后为 50px，留 2px 余量（Noto 时代同样存在 2~3px 的隐性裁切，只是不明显）。
    window.crop_mark_left_spinbox = _spin(window, 0, 50, 0, "左 ", 64)
    window.crop_mark_right_spinbox = _spin(window, 0, 50, 0, "右 ", 64)
    for _spinbox in (window.crop_mark_left_spinbox, window.crop_mark_right_spinbox):
        _spinbox.setSuffix(" mm")
        # 复合框内部的数字框去掉独立描边（设计稿为一体化复合框）
        _spinbox.setObjectName("bareSpin")
    crop_box.addWidget(window.crop_mark_checkbox)
    crop_box.addWidget(label("·", "inlineUnit"))
    crop_box.addWidget(window.crop_mark_left_spinbox)
    crop_box.addWidget(label("·", "inlineUnit"))
    crop_box.addWidget(window.crop_mark_right_spinbox)
    crop_box.addStretch(1)
    row.addWidget(crop_row, 1)
    window.crop_mark_checkbox.stateChanged.connect(window._on_config_changed)
    window.crop_mark_left_spinbox.valueChanged.connect(window._on_config_changed)
    window.crop_mark_right_spinbox.valueChanged.connect(window._on_config_changed)

    return card


def create_mode_order_card(window) -> QFrame:
    """处理模式（分段控件）与打印顺序（下拉框），控件名与信号保持不变。"""
    card = QFrame()
    card.setObjectName("modeOrderCard")
    box = QVBoxLayout(card)
    box.setContentsMargins(0, 0, 0, 0)
    box.setSpacing(0)

    row = _param_row(card, "处理模式")
    window.mode_combo = QComboBox()
    window.mode_combo.addItems(["普通", "图像"])
    window.mode_combo.setToolTip("普通模式保留PDF矢量信息，图像模式转换为图片")
    row.addWidget(window.mode_combo)
    window.mode_combo.setVisible(False)

    segment, segments = _segmented(window, ["普通 · 保留矢量", "图像 · 高精度"])
    row.addWidget(segment, 1)

    def _sync_mode(*_):
        index = window.mode_combo.currentIndex()
        segments[0].setChecked(index == 0)
        segments[1].setChecked(index == 1)

    window.mode_combo.currentIndexChanged.connect(window._on_config_changed)
    window.mode_combo.currentIndexChanged.connect(_sync_mode)
    segments[0].clicked.connect(lambda: window.mode_combo.setCurrentIndex(0) or _sync_mode())
    segments[1].clicked.connect(lambda: window.mode_combo.setCurrentIndex(1) or _sync_mode())
    _sync_mode()
    window.mode_segments = segments

    row = _param_row(card, "打印顺序")
    window.order_combo = QComboBox()
    window.order_combo.setObjectName("paramCombo")
    window.order_combo.addItems(["列表顺序", "开票日期", "开票金额"])
    window.order_combo.setToolTip("选择发票的打印顺序")
    row.addWidget(window.order_combo, 1)
    window.order_combo.currentIndexChanged.connect(window._on_config_changed)

    return card


def create_settings_column(window) -> QWidget:
    """右侧下半部：合并预览 + 单层排版参数面板 + 输出选项胶囊。"""
    column = QWidget()
    box = QVBoxLayout(column)
    box.setContentsMargins(0, 0, 0, 0)
    box.setSpacing(12)

    window.preview_card = create_preview_card(window)
    # 设计稿实测：预览卡 318px、参数卡 342px（含 12px 间距）
    box.addWidget(window.preview_card, 318)

    window.settings_card = section_card("settingsCard")
    sbox = window.settings_card.layout()
    sbox.setContentsMargins(0, 0, 0, 0)
    sbox.setSpacing(0)

    header = QFrame()
    header.setObjectName("cardHeader")
    header.setFixedHeight(44)
    header_box = QHBoxLayout(header)
    header_box.setContentsMargins(16, 10, 16, 10)
    header_box.addWidget(label("排版与输出参数", "cardTitleLabel"))
    header_box.addStretch(1)
    header_box.addWidget(label("修改即保存", "mutedLabel"))
    sbox.addWidget(header)

    # 设计稿实测：卡头底部（486）与首个参数行（约 494）之间留少量呼吸间距
    sbox.addSpacing(5)

    # 原有控件创建方法直接复用：所有变量名、取值范围与信号连接保持不变
    window.layout_card = window._create_layout_widget()
    window.layout_card.setObjectName("layoutCard")
    # 设计稿实测：纸张方向 / 排版布局 / 页边距 / 裁切线 共 4 行，每行 38px
    window.layout_card.setFixedHeight(152)
    sbox.addWidget(window.layout_card)

    window.mode_order_card = window._create_mode_order_widget()
    window.mode_order_card.setObjectName("modeOrderCard")
    # 处理模式 / 打印顺序 共 2 行，每行 38px
    window.mode_order_card.setFixedHeight(76)
    sbox.addWidget(window.mode_order_card)

    # 输出选项胶囊（设计稿位于参数卡底部）：一式两份 / 合并后打开 / 合并后打印
    # 设计稿实测：打印顺序行底 722 → 胶囊 727..753，卡片底部余 32px 留白
    sbox.addSpacing(4)
    pill_row = QFrame()
    pill_row.setObjectName("pillRow")
    pill_row.setFixedHeight(26)
    pill_box = QHBoxLayout(pill_row)
    pill_box.setContentsMargins(12, 0, 12, 0)
    pill_box.setSpacing(6)

    window.duplicate_copy_checkbox = QCheckBox("一式两份")
    window.duplicate_copy_checkbox.setObjectName("pillCheck")
    window.duplicate_copy_checkbox.setToolTip("合并时生成两份相同的文件")
    window.duplicate_copy_checkbox.stateChanged.connect(window._on_duplicate_copy_changed)
    pill_box.addWidget(window.duplicate_copy_checkbox)

    window.print_checkbox = QCheckBox("合并后打开")
    window.print_checkbox.setObjectName("pillCheck")
    window.print_checkbox.setToolTip("合并后打开输出文件")
    window.print_checkbox.stateChanged.connect(lambda _s: _sync_pill_style(window.print_checkbox))
    pill_box.addWidget(window.print_checkbox)

    window.print_after_checkbox = QCheckBox("合并后打印")
    window.print_after_checkbox.setObjectName("pillCheck")
    window.print_after_checkbox.setToolTip("合并后直接调用系统打印")
    window.print_after_checkbox.stateChanged.connect(
        lambda _s: _sync_pill_style(window.print_after_checkbox)
    )
    pill_box.addWidget(window.print_after_checkbox)
    pill_box.addStretch(1)
    sbox.addWidget(pill_row)

    for pill in (
        window.duplicate_copy_checkbox,
        window.print_checkbox,
        window.print_after_checkbox,
    ):
        _sync_pill_style(pill)

    # 设计稿实测：胶囊行底（753）到卡片下描边（785）留 32px 收尾留白
    sbox.addSpacing(28)

    box.addWidget(window.settings_card, 342)
    return column


def _sync_pill_style(checkbox) -> None:
    """勾选胶囊的选中态由全局 QSS 的 :checked 处理，这里仅刷新样式。"""
    try:
        style = checkbox.style()
        style.unpolish(checkbox)
        style.polish(checkbox)
    except Exception:
        pass


def create_output_bar(window) -> QFrame:
    """
    输出提交条（设计稿单行三段式）：
    「输出文件」+ 路径框 + 浏览 ｜ 行内回执与其下细进度条 ｜ 打开文件 + 合并 PDF。
    """
    bar = QFrame()
    bar.setObjectName("outputBar")
    bar.setFixedHeight(74)
    box = QHBoxLayout(bar)
    box.setContentsMargins(16, 16, 16, 16)
    box.setSpacing(10)

    box.addWidget(label("输出文件", "statusLabel"))
    window.path_edit = QLineEdit()
    window.path_edit.setObjectName("pathInput")
    window.path_edit.setPlaceholderText("选择合并后 PDF 的保存位置...")
    window.path_edit.setFixedWidth(418)
    window.path_edit.setFixedHeight(34)
    box.addWidget(window.path_edit)

    window.select_path_btn = secondary_button("浏览")
    window.select_path_btn.setToolTip("选择保存位置")
    window.select_path_btn.setFixedSize(62, 34)
    window.select_path_btn.clicked.connect(window._on_select_path)
    box.addWidget(window.select_path_btn)

    # 打印入口在参数卡的「合并后打印」勾选，输出条不再单独放打印按钮
    window.print_btn = secondary_button("打印")
    window.print_btn.setToolTip("生成临时合并文件并调用系统打印")
    window.print_btn.clicked.connect(window._on_print)
    window.print_btn.setVisible(False)
    box.addWidget(window.print_btn)

    # 回执与进度条同列堆叠，垂直居中对齐主按钮
    inline = QWidget()
    inline_box = QVBoxLayout(inline)
    inline_box.setContentsMargins(0, 0, 0, 0)
    inline_box.setSpacing(4)
    window.feedback_label = feedback_label()
    window.feedback_label.setFixedHeight(18)
    inline_box.addWidget(window.feedback_label)
    window.progress_bar = QProgressBar()
    window.progress_bar.setObjectName("inlineProgress")
    window.progress_bar.setRange(0, 100)
    window.progress_bar.setValue(0)
    window.progress_bar.setTextVisible(False)
    window.progress_bar.setFixedHeight(4)
    window.progress_bar.setVisible(False)
    inline_box.addWidget(window.progress_bar)
    box.addWidget(inline, 1)

    window.open_output_btn = secondary_button("打开文件")
    window.open_output_btn.setToolTip("打开上次合并输出的 PDF")
    window.open_output_btn.setFixedSize(86, 34)
    window.open_output_btn.clicked.connect(window._on_open_output)
    box.addWidget(window.open_output_btn)

    window.merge_btn = primary_button("合并 PDF")
    window.merge_btn.setToolTip("按当前布局合并全部发票并保存")
    window.merge_btn.setFixedSize(152, 40)
    window.merge_btn.clicked.connect(window._on_merge_all)
    box.addWidget(window.merge_btn)

    return bar


def create_status_bar(window) -> QFrame:
    """状态栏：唯一承载全局状态与入口的区段。

    左侧为常驻运行状态（就绪 / 模式 / 布局摘要 / 文件数量），右侧依次为
    一次性回执的临时消息位、配置保存状态、使用帮助入口与版本号；版本号
    本身即「检查更新」入口，不再另设按钮。
    """
    bar = QFrame()
    bar.setObjectName("statusBar")
    bar.setFixedHeight(32)
    box = QHBoxLayout(bar)
    box.setContentsMargins(10, 4, 10, 4)
    box.setSpacing(10)

    window.status_left_label = label("就绪", "statusBarLabel")
    box.addWidget(window.status_left_label)
    box.addStretch(1)

    # 临时消息位：合并 / 导入等一次性回执，空闲时留空，不重复常驻信息
    window.context_status_label = label("", "statusBarLabel")
    box.addWidget(window.context_status_label)

    window.status_right_label = label("配置自动保存", "statusBarLabel")
    box.addWidget(window.status_right_label)

    window.feedback_button = text_button("使用帮助")
    window.feedback_button.setToolTip("使用帮助与反馈")
    window.feedback_button.clicked.connect(window._on_feedback)
    box.addWidget(window.feedback_button)

    try:
        version = window._get_version()
    except Exception:
        version = ""
    window.version_label = QLabel(f"票易合 {version}")
    window.version_label.setObjectName("versionLabel")
    window.version_label.setFont(numeric_font(FONT_SIZE["caption"]))
    window.version_label.setToolTip("点击检查更新")
    window.version_label.setCursor(Qt.CursorShape.PointingHandCursor)
    window.version_label.mousePressEvent = lambda event: window._on_version_click()
    box.addWidget(window.version_label)

    # 行高统一由 tokens.py 的状态栏作用域规则给出（QSS 的 min/max-height 会压过
    # setFixedHeight，代码里再钉一次没有意义，只会让人误以为生效）。
    return bar


# ---------------------------------------------------------------------------
# 状态更新（供 MainWindow 的 handler 调用）
# ---------------------------------------------------------------------------
def update_status_bar(window) -> None:
    """汇总当前模式、布局、文件数量与合计金额，刷新三处统计与状态栏。"""
    # 外壳尚未装配完成时由信号提前触发，直接跳过（装配结束后会再刷新一次）
    if not hasattr(window, "status_left_label"):
        return
    try:
        # get_all_files() 返回路径列表；统计金额需直接读 records（file_info 字典）
        records = list(window.file_list.files)
        count = len(records)
        total = sum(float(f.get("amount", 0.0) or 0.0) for f in records)
    except Exception:
        count, total = 0, 0.0

    try:
        mode = window.mode_combo.currentText()
        rows = window.row_spinbox.value()
        cols = window.col_spinbox.value()
        orientation = "横向" if window.radio_landscape.isChecked() else "竖向"
        layout_text = f"{orientation} {rows} × {cols}"
        per_page = rows * cols
    except Exception:
        mode, layout_text, per_page = "普通", "2 × 2", 4

    money = f"¥{total:,.2f}"
    window.ledger_count_label.setText(f"{count} 张")
    window.ledger_total_label.setText(money)
    window.ledger_footer_total.setText(money)

    selected = window.file_list.get_selected_file() is not None
    window.ledger_record_label.setText(
        f"共 {count} 条　·　当前选中 {1 if selected else 0} 条　·　列表顺序打印"
    )

    # 台账为空时投放带铺满表头以下的列表区（九列表头保持可见）；有文件后让位给数据行
    try:
        window.file_list.sync_empty_overlay()
    except Exception:
        pass

    window.status_left_label.setText(
        f"就绪　|　{mode}模式　|　{layout_text}　|　{count} 张票据"
    )
    try:
        window.preview_summary_label.setText(
            f"A4 {orientation}　·　{rows} × {cols}　·　每页 {per_page} 张"
        )
        window.preview_page_label.setText(f"第 1 页 / 共 {max(1, (count + per_page - 1) // per_page)} 页")
    except Exception:
        pass


def update_duplicate_chip(window, count: int) -> None:
    """重复发票：琥珀状态标签 + 计数，替代旧版整行涂色与标题文字拼接。"""
    rows = getattr(window.file_list, "duplicate_row_count", 0)
    if count > 0:
        # 设计稿：琥珀 chip 前置警示三角图标 + 「重复 N 组 / M 张」
        window.ledger_warning_chip.setText(f"⚠ 重复 {count} 组 / {rows} 张")
        window.ledger_warning_chip.setVisible(True)
    else:
        window.ledger_warning_chip.setVisible(False)
        window.ledger_warning_chip.setText("")


def show_feedback(window, text: str, state: str = "info") -> None:
    """统一回执：info / success / warning / danger。"""
    set_feedback(window.feedback_label, text, state)
    try:
        window.context_status_label.setText(text or "")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# 外壳装配
# ---------------------------------------------------------------------------
def build_shell(window) -> None:
    """构建三段式主窗口；保持 MainWindow 原有属性与信号槽不变。"""
    central = QWidget()
    central.setObjectName("centralWidget")
    window.setCentralWidget(central)

    root = QVBoxLayout(central)
    root.setContentsMargins(0, 0, 0, 0)
    root.setSpacing(0)

    window.content_splitter = QSplitter(Qt.Orientation.Horizontal)
    window.content_splitter.setObjectName("contentSplitter")
    window.content_splitter.setHandleWidth(16)
    window.ledger_column = create_ledger_column(window)
    window.settings_column = create_settings_column(window)
    window.content_splitter.addWidget(window.ledger_column)
    window.content_splitter.addWidget(window.settings_column)
    window.content_splitter.setChildrenCollapsible(False)
    # 设计稿 01：15px 外边距 + 左列 976 + 14px 间隔 + 右列 418 + 15px 外边距
    window.content_splitter.setSizes([976, 418])
    window.content_splitter.setStretchFactor(0, 1)
    window.content_splitter.setStretchFactor(1, 0)

    content_wrap = QWidget()
    content_wrap.setObjectName("contentWrap")
    wrap_box = QHBoxLayout(content_wrap)
    wrap_box.setContentsMargins(15, 14, 15, 14)
    wrap_box.setSpacing(0)
    wrap_box.addWidget(window.content_splitter)
    root.addWidget(content_wrap, 1)

    window.output_bar = create_output_bar(window)
    root.addWidget(window.output_bar)

    window.status_bar = create_status_bar(window)
    root.addWidget(window.status_bar)

    # 统一移除历史逐控件 setStyleSheet，让全局 QSS 生效
    clear_inline_styles(window)
    # 含数字的次级文本位统一 Inter + tnum（QSS 无法启用 OpenType 特性）
    apply_numeric_text_fonts(window)
    update_status_bar(window)
