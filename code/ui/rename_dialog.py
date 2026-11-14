#!/usr/bin/env python3
"""
批量重命名对话框模块

该模块提供批量重命名配置对话框，按发票类型分别配置文件名规则。
每种票种有自己的一套可插入字段与一条独立的规则。
"""

import os
import re
import json
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTextEdit, QGridLayout, QFrame, QMessageBox,
    QScrollArea, QWidget, QTabWidget
)
from PySide6.QtCore import Qt, Signal
from core.invoice_service import InvoiceService, normalize_rename_rules
from core.invoice_field_registry import (
    INVOICE_TYPE_KEYS,
    get_default_template,
    get_fields,
    get_type_label,
)
from ui.theme import AppTheme
from ui.tokens import (
    build_stylesheet, clear_inline_styles, numeric_font, FONT_SIZE,
    apply_numeric_text_fonts,
)


# v2：唯一色值来源是 ui.tokens；这里只保留旧变量名兼容历史 f-string QSS
_theme = AppTheme()
_T = _theme.tokens
PRIMARY_COLOR = _T["accent"]
PRIMARY_HOVER = _T["accent_hover"]
SUCCESS_COLOR = _T["success"]
WARNING_COLOR = _T["warning"]
DANGER_COLOR = _T["danger"]
BG_COLOR = _T["background"]
CARD_BG = _T["surface"]
BORDER_COLOR = _T["border"]
TEXT_PRIMARY = _T["text_primary"]
TEXT_SECONDARY = _T["text_secondary"]
TEXT_MUTED = _T["text_muted"]
HOVER_BG = _T["hover_bg"]
PRESSED_BG = _T["pressed_bg"]
SELECTED_BG = _T["selected_bg"]
SELECTED_TEXT = _T["selected_text"]

# 票种导航栏（左侧横排文字）：QTabWidget 原生 West 方向会把文字旋转 90° 竖排，
# 显示不符合阅读习惯，因此隐藏原生 tab 栏，用 QPushButton 列表自绘导航；
# 页面管理仍复用 QTabWidget（currentChanged/_migrate_editor 逻辑不变）。
# 几何取自 req/ui/02-批量重命名规则.png：左栏 215px、导航项 36px 高。
TYPE_NAV_WIDTH = 215
TYPE_NAV_BUTTON_HEIGHT = 36


class RenameDialog(QDialog):
    """
    批量重命名对话框类

    功能描述:
        按发票类型分别配置重命名规则。对话框左侧以标签页常驻列出 7 类票种，
        切换票种时载入该票种已保存的规则（无已存规则时显示默认模板），
        并切换为该票种的可插入字段集。

    信号:
        rule_saved: 当某票种规则保存时发出，参数为 (票种标识, 规则字符串)
        rename_executed: 当执行重命名时发出，参数为全部票种的已保存规则字典

    参数:
        parent: 父窗口
        config_file: 配置文件路径
        current_rule: 兼容旧调用，作为初始规则（仅在无已存规则时使用）
    """

    rule_saved = Signal(str, str)
    rename_executed = Signal(dict)

    # Windows文件名非法字符
    INVALID_CHARS = r'[<>:"/\\|?*]'

    def __init__(self, parent=None, config_file=None, current_rule=""):
        """
        初始化重命名对话框

        参数:
            parent: 父窗口
            config_file: 配置文件路径
            current_rule: 兼容旧调用，初始规则
        """
        super().__init__(parent)

        self.config_file = config_file
        self.current_rule = current_rule

        # 各票种已保存的规则（唯一权威来源，界面显示不等于已保存）
        self._saved_rules = normalize_rename_rules(None)
        # 当前所选票种
        self._current_type = INVOICE_TYPE_KEYS[0]
        # 字段按钮容器（重建时清空）
        self._fields_grid = None

        self._init_ui()
        self._setup_stylesheet()
        self._load_rules_from_config()
        self._select_initial_type()
        self._on_type_changed()

    def _init_ui(self):
        """
        初始化用户界面

        功能描述:
            按 ``req/ui/02-批量重命名规则.png`` 复原结构：白底圆角对话框，
            顶部标题栏（标题 + 副标题 + 变量说明 + 关闭），下方左侧 215px 票种
            导航栏（浅灰底，底部两行说明），右侧内容区自成一栏（票种标题 +
            已配置标记、文件名规则、示例结果、字段芯片、使用说明、上次执行统计），
            最底部右侧四个操作按钮。
        """
        self.setWindowTitle("批量重命名规则")
        self.setMinimumSize(1136, 686)
        self.setModal(True)

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # ========== 顶部标题栏 ==========
        header = QFrame()
        header.setObjectName("dialogHeader")
        header.setFixedHeight(59)
        header_box = QHBoxLayout(header)
        header_box.setContentsMargins(24, 14, 24, 14)
        header_box.setSpacing(12)

        title_label = QLabel("批量重命名规则")
        title_label.setObjectName("dialogTitle")
        header_box.addWidget(title_label)

        subtitle = QLabel("按发票类型分别配置　·　点击保存后生效")
        subtitle.setObjectName("mutedLabel")
        header_box.addWidget(subtitle)
        header_box.addStretch()

        self.help_btn = QPushButton("变量说明")
        self.help_btn.setObjectName("textButton")
        self.help_btn.clicked.connect(self._show_help)
        header_box.addWidget(self.help_btn)

        close_icon_btn = QPushButton("✕")
        close_icon_btn.setObjectName("textButton")
        close_icon_btn.setFixedSize(28, 28)
        close_icon_btn.setToolTip("关闭")
        close_icon_btn.clicked.connect(self.reject)
        header_box.addWidget(close_icon_btn)

        main_layout.addWidget(header)

        # ========== 主体：左导航 + 右内容 ==========
        body = QWidget()
        body_box = QHBoxLayout(body)
        body_box.setContentsMargins(0, 0, 0, 0)
        body_box.setSpacing(0)

        # ---- 左侧票种导航 ----
        nav_card = QFrame()
        nav_card.setObjectName("typeNav")
        nav_card.setFixedWidth(TYPE_NAV_WIDTH)
        nav_layout = QVBoxLayout(nav_card)
        nav_layout.setSpacing(2)
        nav_layout.setContentsMargins(16, 16, 16, 16)

        nav_title = QLabel("发票类型")
        nav_title.setObjectName("typeNavTitle")
        nav_layout.addWidget(nav_title)
        nav_layout.addSpacing(6)

        self._type_nav_buttons = {}
        for type_key in INVOICE_TYPE_KEYS:
            btn = QPushButton(get_type_label(type_key))
            btn.setObjectName("typeNavButton")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(TYPE_NAV_BUTTON_HEIGHT)
            btn.clicked.connect(lambda _=False, k=type_key: self._switch_type(k))
            self._type_nav_buttons[type_key] = btn
            nav_layout.addWidget(btn)
        nav_layout.addStretch()

        nav_note = QLabel("7 类票种 · 各自独立规则\n旧配置自动迁移")
        nav_note.setObjectName("mutedLabel")
        nav_layout.addWidget(nav_note)
        body_box.addWidget(nav_card)

        # ---- 右侧内容区 ----
        content = QWidget()
        content_box = QVBoxLayout(content)
        content_box.setSpacing(0)
        content_box.setContentsMargins(24, 22, 24, 16)
        body_box.addWidget(content, 1)

        # 页容器：tab 栏不可见，仅承载 7 个票种页
        self.type_tabs = QTabWidget()
        self.type_tabs.setObjectName("typeTabs")
        self.type_tabs.tabBar().setVisible(False)
        self._type_pages = {}
        for type_key in INVOICE_TYPE_KEYS:
            page = QWidget()
            page_layout = QVBoxLayout(page)
            page_layout.setSpacing(0)
            page_layout.setContentsMargins(0, 0, 0, 0)
            self._type_pages[type_key] = page
            self.type_tabs.addTab(page, get_type_label(type_key))
        self.type_tabs.currentChanged.connect(self._on_type_changed)
        # 同步导航按钮选中态（含程序化 setCurrentIndex，如 _select_initial_type）
        self.type_tabs.currentChanged.connect(self._sync_nav_buttons)
        content_box.addWidget(self.type_tabs, 0)
        # 编辑区（单实例，随票种标签页迁移）
        self.editor_container = QWidget()
        editor_layout = QVBoxLayout(self.editor_container)
        editor_layout.setSpacing(10)
        editor_layout.setContentsMargins(0, 0, 0, 0)

        # 票种标题 + 已配置标记
        type_head = QHBoxLayout()
        type_head.setSpacing(10)
        self.type_title_label = QLabel(get_type_label(self._current_type))
        self.type_title_label.setObjectName("dialogSectionTitle")
        type_head.addWidget(self.type_title_label)
        self.configured_chip = QLabel("已配置")
        self.configured_chip.setObjectName("successChip")
        type_head.addWidget(self.configured_chip)
        type_head.addStretch()
        editor_layout.addLayout(type_head)

        # 文件名规则标签行
        rule_head = QHBoxLayout()
        rule_head.setSpacing(10)
        rule_caption = QLabel("文件名规则")
        rule_caption.setObjectName("paramCaption")
        rule_head.addWidget(rule_caption)
        rule_hint = QLabel("切换票种前请先保存，未保存的修改会丢失")
        rule_hint.setObjectName("footLabel")
        rule_head.addWidget(rule_hint)
        rule_head.addStretch()
        editor_layout.addLayout(rule_head)

        # 规则输入框
        self.rule_input = QLineEdit()
        self.rule_input.setObjectName("ruleInput")
        self.rule_input.setPlaceholderText("请输入该票种的文件名规则，点击以下按钮可插入对应字段")
        self.rule_input.setFixedHeight(41)
        self.rule_input.textChanged.connect(self._update_example)
        editor_layout.addWidget(self.rule_input)

        # 示例结果（实时生成，不落盘）
        example_row = QHBoxLayout()
        example_row.setSpacing(10)
        example_caption = QLabel("示例结果")
        example_caption.setObjectName("paramCaption")
        example_row.addWidget(example_caption)
        self.example_label = QLabel("输入规则后在此预览文件名")
        self.example_label.setObjectName("exampleValue")
        self.example_label.setFont(numeric_font(FONT_SIZE["caption"]))
        self.example_label.setWordWrap(False)
        example_row.addWidget(self.example_label, 1)
        editor_layout.addLayout(example_row)

        # 字段芯片
        fields_label = QLabel("点击插入字段（蓝色为通用字段，灰色为本票种专属字段）")
        fields_label.setObjectName("footLabel")
        editor_layout.addWidget(fields_label)

        self._fields_grid = QGridLayout()
        self._fields_grid.setSpacing(8)
        self._fields_grid.setContentsMargins(0, 0, 0, 0)
        editor_layout.addLayout(self._fields_grid)
        # 编辑区不随窗口拉伸：剩余空间留在字段芯片下方（设计稿 02 中约 14px 后
        # 即是使用说明块），否则 QVBoxLayout 会把空余高度平摊到每一行。
        editor_layout.addStretch(1)

        # 编辑区挂到默认票种页
        self._migrate_editor()
        main_layout.addWidget(body, 1)

        # ========== 使用说明（内容列内的浅灰圆角块，设计稿 02：紧随字段芯片 14px） ==========
        help_card = QFrame()
        help_card.setObjectName("helpCard")
        help_layout = QVBoxLayout(help_card)
        help_layout.setSpacing(6)
        help_layout.setContentsMargins(16, 12, 16, 12)

        help_title = QLabel("使用说明")
        help_title.setObjectName("helpCardTitle")
        help_layout.addWidget(help_title)

        help_content = QLabel(
            "1　每种发票类型有自己的一套规则，切换左侧票种分别配置。<br>"
            "2　输入框为建议模板，点击「保存」后才用于重命名；切换票种前未保存的修改会丢失。<br>"
            "3　某票种规则留空，则该票种文件保持原文件名；字段未识别时保留 {占位符} 原文。<br>"
            "4　不能用做文件名的字符：&lt; &gt; : \" / \\ | ? *　举例：报销-{开票日期}-{商品类型}"
        )
        help_content.setObjectName("helpCardText")
        help_content.setWordWrap(True)
        help_layout.addWidget(help_content)
        help_layout.addStretch(1)
        # 设计稿 02：使用说明块固定高 135px（y 380..515），不随窗口拉伸
        help_card.setFixedHeight(135)

        content_box.addWidget(help_card)

        # ========== 统计 + 底部按钮（内容列内，设计稿 02 为上下两行） ==========
        footer = QWidget()
        footer_box = QVBoxLayout(footer)
        footer_box.setContentsMargins(0, 10, 0, 26)
        footer_box.setSpacing(10)

        # 第一行：上次执行统计（左对齐，y 525..550）
        stats_row = QHBoxLayout()
        stats_row.setSpacing(8)
        self.result_label = QLabel("上次执行　成功 4　·　失败 0　·　跳过未配置 0　·　跳过图片 0　·　跳过 OFD 0　·　未识别 0")
        self.result_label.setObjectName("footLabel")
        stats_row.addWidget(self.result_label)
        stats_row.addStretch(1)
        footer_box.addLayout(stats_row)

        # 第二行：关闭 / 清空 / 保存 / 执行重命名（右对齐，y 561..597）
        buttons_row = QHBoxLayout()
        buttons_row.setSpacing(8)
        buttons_row.addStretch(1)

        close_btn = QPushButton("关闭")
        close_btn.setObjectName("closeButton")
        close_btn.setFixedSize(76, 36)
        close_btn.clicked.connect(self.reject)
        buttons_row.addWidget(close_btn)

        self.clear_btn = QPushButton("清空")
        self.clear_btn.setObjectName("clearButton")
        self.clear_btn.setFixedSize(76, 36)
        self.clear_btn.clicked.connect(self._on_clear)
        buttons_row.addWidget(self.clear_btn)

        self.save_btn = QPushButton("保存")
        self.save_btn.setObjectName("saveButton")
        self.save_btn.setFixedSize(88, 36)
        self.save_btn.clicked.connect(self._on_save)
        buttons_row.addWidget(self.save_btn)

        self.execute_btn = QPushButton("执行重命名")
        self.execute_btn.setObjectName("executeButton")
        self.execute_btn.setFixedSize(132, 36)
        self.execute_btn.clicked.connect(self._on_execute)
        buttons_row.addWidget(self.execute_btn)

        footer_box.addLayout(buttons_row)
        content_box.addWidget(footer)
        # 设计稿 02：卡片底部留白，所有内容靠上排布；避免 QTabWidget 的
        # Expanding 策略把使用说明与按钮行推到窗口最底部。
        content_box.addStretch(1)

    
    def _setup_stylesheet(self):
        """
        设置样式表

        功能描述:
            v2 UI 统一消费 ui.tokens 生成的全局 QSS；清除历史逐控件内联样式，
            让四级按钮、字段芯片与表单控件按 objectName 取色。
        """
        self.setStyleSheet(build_stylesheet(_theme.dark))
        clear_inline_styles(self)
        apply_numeric_text_fonts(self)

    def _switch_type(self, type_key):
        """点击左侧导航按钮：切到对应票种页"""
        if type_key in INVOICE_TYPE_KEYS:
            self.type_tabs.setCurrentIndex(INVOICE_TYPE_KEYS.index(type_key))

    def _sync_nav_buttons(self, _index=None):
        """把导航按钮的选中态同步到当前票种页"""
        current = self._current_type_key()
        for key, btn in self._type_nav_buttons.items():
            btn.setChecked(key == current)

    def _current_type_key(self) -> str:
        """返回当前所选票种标识"""
        index = self.type_tabs.currentIndex()
        if 0 <= index < len(INVOICE_TYPE_KEYS):
            return INVOICE_TYPE_KEYS[index]
        return INVOICE_TYPE_KEYS[0]

    def _migrate_editor(self):
        """
        把编辑区迁移到当前票种页

        功能描述:
            编辑区只创建一个实例，切换票种时从上一页摘下再挂到当前页，
            避免 7 份编辑区各自保存状态。
        """
        page = getattr(self, '_type_pages', {}).get(self._current_type_key())
        if page is None:
            return
        layout = page.layout()
        if layout is None:
            return
        old_page = self.editor_container.parentWidget()
        if old_page is page:
            return
        if old_page is not None and old_page.layout() is not None:
            old_page.layout().removeWidget(self.editor_container)
        layout.addWidget(self.editor_container)
        self.editor_container.show()

    def _rebuild_field_buttons(self):
        """
        按当前票种的字段集重建字段芯片网格

        功能描述:
            不同票种字段数从 4 到 10 不等，3 列布局的行数会变，
            因此清空重排而不是全部创建后切换可见性。v2 用蓝/灰两级芯片
            区分通用字段与票种专属字段，插入行为保持不变。
        """
        # 清空既有按钮
        while self._fields_grid.count():
            item = self._fields_grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

        common = {"发票类型", "开票日期", "发票号码", "金额"}
        fields = get_fields(self._current_type_key())
        # 设计稿 02：单行 7 列铺开，4 枚通用字段（浅蓝底）在前、票种专属
        # 字段（浅灰底）在后，芯片 106x30、间距 10px（列距 116px）。
        self._fields_grid.setHorizontalSpacing(10)
        self._fields_grid.setVerticalSpacing(10)
        columns = 7
        for i, (display_name, _field_key) in enumerate(fields):
            row, col = divmod(i, columns)
            btn = self._make_field_chip(
                display_name,
                "fieldChip" if display_name in common else "fieldChipExtra",
            )
            self._fields_grid.addWidget(btn, row, col)
        self._fields_grid.setColumnStretch(columns, 1)

    def _make_field_chip(self, display_name, object_name):
        """创建一个字段芯片按钮（设计稿 02：106x30、圆角 6、12px）"""
        btn = QPushButton("{" + display_name + "}")
        btn.setObjectName(object_name)
        btn.setFixedHeight(30)
        btn.setFixedWidth(106)
        # 用显示名作为占位符内容
        btn.setProperty("field_name", display_name)
        btn.clicked.connect(self._on_field_button_clicked)
        return btn
    def _on_type_changed(self, _index=None):
        """
        票种切换处理

        功能描述:
            丢弃未保存的输入，载入该票种已保存的规则；
            若该票种无已保存规则，则预填默认模板（仅显示，不落盘）。
            随后重建该票种的字段按钮，并同步标题与「已配置」标记。
        """
        if self._fields_grid is None:
            return

        self._current_type = self._current_type_key()
        self._migrate_editor()

        saved = self._saved_rules.get(self._current_type, '')
        if saved:
            # 有已保存规则：显示已存规则
            self.rule_input.setText(saved)
        else:
            # 无已保存规则：预填默认模板（仅显示，不写入配置）
            self.rule_input.setText(get_default_template(self._current_type))

        # 设计稿 02：内容区首行是当前票种名 + 「已配置」绿色标记
        title_label = getattr(self, "type_title_label", None)
        if title_label is not None:
            title_label.setText(get_type_label(self._current_type))
        chip = getattr(self, "configured_chip", None)
        if chip is not None:
            chip.setVisible(bool(saved))

        self._rebuild_field_buttons()

    def _select_initial_type(self):
        """
        选择初始票种

        功能描述:
            默认选中第一个已有非空规则的票种；若全部为空，
            则选中第一类（增值税发票）。
        """
        for idx, type_key in enumerate(INVOICE_TYPE_KEYS):
            if self._saved_rules.get(type_key, ''):
                self.type_tabs.setCurrentIndex(idx)
                self._sync_nav_buttons()
                return
        self.type_tabs.setCurrentIndex(0)
        self._sync_nav_buttons()

    def _update_example(self, _text=None):
        """根据当前规则输入框内容生成示例文件名（纯展示，不参与执行）。"""
        rule = self.rule_input.text()
        if not rule:
            self.example_label.setText("规则为空时保持原文件名")
            return
        sample = {
            'invoice_type': '增值税专用发票',
            'invoice_date': '2026-11-03',
            'invoice_code': '24310000000017846321',
            'amount': 4860.0,
            'tax_amount': 437.4,
            'buyer_name': '示例科技有限公司',
            'seller_name': '示例供应商',
            'product_type': '技术服务费',
        }
        try:
            preview = self.apply_rule(rule, sample)
        except Exception:
            preview = rule
        self.example_label.setText(f"{preview}")

    # ========== 交互 ==========

    def _on_field_button_clicked(self):
        """
        字段按钮点击处理

        功能描述:
            将字段占位符插入到规则输入框的当前光标位置
        """
        sender = self.sender()
        if sender:
            field_name = sender.property("field_name")
            if field_name:
                cursor_pos = self.rule_input.cursorPosition()
                current_text = self.rule_input.text()
                placeholder = f"{{{field_name}}}"
                new_text = current_text[:cursor_pos] + placeholder + current_text[cursor_pos:]
                self.rule_input.setText(new_text)
                self.rule_input.setCursorPosition(cursor_pos + len(placeholder))
                self.rule_input.setFocus()

    def _on_save(self):
        """
        保存按钮点击处理

        功能描述:
            把当前输入框内容写为该票种的规则（只写当前所选票种）。
        """
        type_key = self._current_type_key()
        rule = self.rule_input.text().strip()

        # 更新内存中的已保存规则
        self._saved_rules[type_key] = rule

        # 写入配置文件
        if self.config_file and os.path.exists(os.path.dirname(self.config_file)):
            try:
                config = {}
                if os.path.exists(self.config_file):
                    with open(self.config_file, 'r', encoding='utf-8') as f:
                        config = json.load(f)

                rename_rules = config.get('rename_rules')
                if not isinstance(rename_rules, dict):
                    rename_rules = {}
                rename_rules[type_key] = rule
                config['rename_rules'] = rename_rules

                with open(self.config_file, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)

                self.rule_saved.emit(type_key, rule)
                QMessageBox.information(
                    self, "保存成功",
                    f"「{get_type_label(type_key)}」的重命名规则已保存！"
                )
            except Exception as e:
                QMessageBox.warning(self, "保存失败", f"保存规则失败: {str(e)}")
        else:
            self.rule_saved.emit(type_key, rule)
            QMessageBox.information(
                self, "保存成功",
                f"「{get_type_label(type_key)}」的重命名规则已保存！"
            )

    def _on_clear(self):
        """
        清空按钮点击处理

        功能描述:
            清空规则输入框的内容（不落盘）
        """
        self.rule_input.clear()
        self.rule_input.setFocus()

    def _on_execute(self):
        """
        执行按钮点击处理

        功能描述:
            按全部票种的已保存规则执行批量重命名。
            注意：只看已保存规则，界面上的预填模板不算已配置。
        """
        # 全部票种都无已保存规则 -> 中止
        if not any(rule for rule in self._saved_rules.values()):
            QMessageBox.warning(
                self, "提示",
                "还没有保存任何票种的重命名规则。\n\n"
                "请输入规则并点击「保存」，再执行重命名。\n"
                "（输入框中的模板需要点击保存后才会生效）"
            )
            return

        self.result_label.setText("已提交执行　·　成功 / 失败 / 跳过统计见主界面回执")
        self.rename_executed.emit(dict(self._saved_rules))
        self.accept()

    def _show_help(self):
        """
        显示帮助信息

        功能描述:
            按票种展示可用的占位符
        """
        type_key = self._current_type_key()
        lines = [f"「{get_type_label(type_key)}」可用的重命名字段：\n"]
        for display_name, _field_key in get_fields(type_key):
            lines.append(f"• {{{display_name}}}")

        lines.append("\n说明：")
        lines.append("1. 每种发票类型各有一套规则，切换左侧「发票类型」分别配置")
        lines.append("2. 输入框中的模板需点击「保存」后才生效")
        lines.append("3. 切换票种前请先保存，未保存的修改会丢失")
        lines.append("4. 某票种规则留空则该票种文件保持原名")
        lines.append("5. 未识别出的字段会保留占位符原文")

        QMessageBox.information(self, "变量说明", "\n".join(lines))

    # ========== 配置读写 ==========

    def _load_rules_from_config(self):
        """
        从配置文件加载各票种规则

        功能描述:
            读取 config.json 的 rename_rules；缺失时按空规则处理。
        """
        if self.config_file and os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                self._saved_rules = normalize_rename_rules(config.get('rename_rules'))
            except Exception as e:
                print(f"加载规则失败: {e}")
                self._saved_rules = normalize_rename_rules(None)
        else:
            self._saved_rules = normalize_rename_rules(None)

        # 兼容旧调用传入的 current_rule：仅在全部为空时用作 vat_invoice 初始值
        if self.current_rule and not any(self._saved_rules.values()):
            self._saved_rules['vat_invoice'] = self.current_rule

    def get_rule(self) -> str:
        """
        获取当前所选票种的规则

        返回值:
            str: 当前票种规则字符串
        """
        return self.rule_input.text().strip()

    def get_rules(self) -> dict:
        """
        获取全部票种的已保存规则

        返回值:
            dict: 票种标识 -> 规则字符串
        """
        return dict(self._saved_rules)
    
    @staticmethod
    def sanitize_filename(filename):
        """
        清理文件名，移除非法字符

        功能描述:
            委托给 InvoiceService.sanitize_filename，保持与业务层逻辑一致。

        参数:
            filename: 原始文件名

        返回值:
            str: 清理后的文件名
        """
        return InvoiceService.sanitize_filename(filename)

    @staticmethod
    def apply_rule(rule, file_info):
        """
        应用重命名规则

        功能描述:
            委托给 InvoiceService.apply_rule，保持与业务层逻辑一致。

        参数:
            rule: 规则字符串，包含占位符
            file_info: 文件信息字典，包含各字段值

        返回值:
            str: 应用规则后的文件名（不含扩展名）
        """
        return InvoiceService.apply_rule(rule, file_info)
