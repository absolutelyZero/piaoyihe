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
    QScrollArea, QWidget, QComboBox
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


# 配色方案 - 与主界面保持一致，并根据系统主题自动适配深色/浅色模式
_theme = AppTheme()
PRIMARY_COLOR = "#2196F3"
PRIMARY_HOVER = "#1976D2"
SUCCESS_COLOR = "#4CAF50"
WARNING_COLOR = "#FF9800"
DANGER_COLOR = "#F44336"
BG_COLOR = _theme.bg
CARD_BG = _theme.card_bg
BORDER_COLOR = _theme.border
TEXT_PRIMARY = _theme.text_primary
TEXT_SECONDARY = _theme.text_secondary
TEXT_MUTED = _theme.text_muted
HOVER_BG = _theme.hover_bg
PRESSED_BG = _theme.pressed_bg
SELECTED_BG = _theme.selected_bg
SELECTED_TEXT = _theme.selected_text


class RenameDialog(QDialog):
    """
    批量重命名对话框类

    功能描述:
        按发票类型分别配置重命名规则。对话框内提供票种下拉，
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
            创建对话框的所有UI控件和布局
        """
        self.setWindowTitle("批量重命名设置")
        self.setMinimumSize(640, 560)
        self.setModal(True)

        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # ========== 标题区域 ==========
        title_layout = QHBoxLayout()

        title_label = QLabel("📋 请按发票类型设置重命名规则")
        title_label.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {TEXT_PRIMARY};")
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        # 使用说明按钮
        help_btn = QPushButton("变量说明")
        help_btn.setObjectName("helpButton")
        help_btn.setFixedWidth(80)
        help_btn.clicked.connect(self._show_help)
        title_layout.addWidget(help_btn)

        main_layout.addLayout(title_layout)

        # ========== 规则输入区域 ==========
        input_card = QFrame()
        input_card.setObjectName("card")
        input_card.setFrameShape(QFrame.Shape.StyledPanel)

        input_layout = QVBoxLayout(input_card)
        input_layout.setSpacing(12)
        input_layout.setContentsMargins(16, 16, 16, 16)

        # 票种选择
        type_layout = QHBoxLayout()
        type_label = QLabel("发票类型：")
        type_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")
        type_layout.addWidget(type_label)

        self.type_combo = QComboBox()
        self.type_combo.setObjectName("typeCombo")
        for type_key in INVOICE_TYPE_KEYS:
            self.type_combo.addItem(get_type_label(type_key), type_key)
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        type_layout.addWidget(self.type_combo, 1)

        input_layout.addLayout(type_layout)

        # 规则输入框
        self.rule_input = QLineEdit()
        self.rule_input.setObjectName("ruleInput")
        self.rule_input.setPlaceholderText("请输入该票种的文件名规则，点击以下按钮可插入对应字段")
        self.rule_input.setMinimumHeight(36)
        input_layout.addWidget(self.rule_input)

        # 字段按钮网格
        fields_label = QLabel("点击插入字段：")
        fields_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")
        input_layout.addWidget(fields_label)

        self._fields_grid = QGridLayout()
        self._fields_grid.setSpacing(8)
        input_layout.addLayout(self._fields_grid)
        
        # 操作按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        
        self.save_btn = QPushButton("保存")
        self.save_btn.setObjectName("saveButton")
        self.save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(self.save_btn)
        
        self.clear_btn = QPushButton("清空")
        self.clear_btn.setObjectName("clearButton")
        self.clear_btn.clicked.connect(self._on_clear)
        btn_layout.addWidget(self.clear_btn)
        
        btn_layout.addStretch()
        
        self.execute_btn = QPushButton("▶ 执行重命名")
        self.execute_btn.setObjectName("executeButton")
        self.execute_btn.clicked.connect(self._on_execute)
        btn_layout.addWidget(self.execute_btn)
        
        input_layout.addLayout(btn_layout)
        
        main_layout.addWidget(input_card)
        
        # ========== 使用说明区域 ==========
        help_card = QFrame()
        help_card.setObjectName("card")
        help_card.setFrameShape(QFrame.Shape.StyledPanel)
        
        help_layout = QVBoxLayout(help_card)
        help_layout.setSpacing(8)
        help_layout.setContentsMargins(16, 16, 16, 16)
        
        help_title = QLabel("📖 使用说明")
        help_title.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {TEXT_PRIMARY};")
        help_layout.addWidget(help_title)
        
        help_content = QLabel(
            "1. 每种发票类型有自己的一套规则，切换上方「发票类型」分别配置。<br>"
            "2. 输入框中的内容是建议模板，<b>点击「保存」后才会用于重命名</b>。<br>"
            "3. 切换票种前请先保存，未保存的修改会丢失。<br>"
            "4. 某个票种规则留空，则该票种的文件保持原文件名不变。<br>"
            "5. 如果发票中没有识别出你选定的字段，会保留该字段的模板文字（如 {商品类型}）。<br>"
            "6. 举例（增值税发票）：报销-{开票日期}-{商品类型}；举例（火车票）：{车次}-{出发站}到{到达站}<br>"
            "7. 不能用作文件名的字符：&lt; &gt; : \" / \\ | ? *"
        )
        help_content.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px; line-height: 1.6;")
        help_content.setWordWrap(True)
        help_layout.addWidget(help_content)
        
        main_layout.addWidget(help_card)
        
        # 添加弹性空间
        main_layout.addStretch()
        
        # 底部关闭按钮
        close_layout = QHBoxLayout()
        close_layout.addStretch()
        
        close_btn = QPushButton("关闭")
        close_btn.setObjectName("closeButton")
        close_btn.clicked.connect(self.reject)
        close_layout.addWidget(close_btn)
        
        main_layout.addLayout(close_layout)
    
    def _setup_stylesheet(self):
        """
        设置样式表
        
        功能描述:
            配置对话框的样式，与主界面保持一致
        """
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {BG_COLOR};
            }}
            
            QFrame#card {{
                background-color: {CARD_BG};
                border-radius: 8px;
                border: 1px solid {BORDER_COLOR};
            }}
            
            QLabel {{
                color: {TEXT_PRIMARY};
            }}
            
            QLineEdit {{
                padding: 8px 12px;
                border-radius: 6px;
                border: 1px solid {BORDER_COLOR};
                background-color: {CARD_BG};
                font-size: 13px;
                color: {TEXT_PRIMARY};
            }}
            
            QLineEdit:focus {{
                border-color: {PRIMARY_COLOR};
            }}
            
            QPushButton {{
                padding: 8px 16px;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 500;
                border: 1px solid {BORDER_COLOR};
                background-color: {CARD_BG};
                color: {TEXT_PRIMARY};
            }}
            
            QPushButton:hover {{
                background-color: {HOVER_BG};
                border-color: {TEXT_MUTED};
            }}
            
            QPushButton:pressed {{
                background-color: {PRESSED_BG};
            }}
            
            QPushButton#fieldButton {{
                background-color: {SELECTED_BG};
                border-color: {PRIMARY_COLOR};
                color: {PRIMARY_COLOR};
                padding: 6px 12px;
            }}
            
            QPushButton#fieldButton:hover {{
                background-color: {PRIMARY_COLOR};
                color: white;
            }}
            
            QPushButton#saveButton {{
                background-color: {SUCCESS_COLOR};
                color: white;
                border: none;
            }}
            
            QPushButton#saveButton:hover {{
                background-color: #388E3C;
            }}
            
            QPushButton#clearButton {{
                background-color: {DANGER_COLOR};
                color: white;
                border: none;
            }}
            
            QPushButton#clearButton:hover {{
                background-color: #D32F2F;
            }}
            
            QPushButton#executeButton {{
                background-color: {PRIMARY_COLOR};
                color: white;
                border: none;
                font-weight: bold;
                padding: 10px 24px;
            }}
            
            QPushButton#executeButton:hover {{
                background-color: {PRIMARY_HOVER};
            }}
            
            QPushButton#helpButton {{
                background-color: transparent;
                border: 1px solid {BORDER_COLOR};
                color: {TEXT_SECONDARY};
                font-size: 12px;
            }}
            
            QPushButton#helpButton:hover {{
                border-color: {PRIMARY_COLOR};
                color: {PRIMARY_COLOR};
            }}
            
            QPushButton#closeButton {{
                background-color: {CARD_BG};
                border: 1px solid {BORDER_COLOR};
                color: {TEXT_SECONDARY};
                padding: 8px 24px;
            }}
            
            QPushButton#closeButton:hover {{
                border-color: {PRIMARY_COLOR};
                color: {PRIMARY_COLOR};
            }}
        """)
    
    # ========== 票种与字段集 ==========

    def _current_type_key(self) -> str:
        """返回当前所选票种标识"""
        key = self.type_combo.currentData()
        return key if key in INVOICE_TYPE_KEYS else INVOICE_TYPE_KEYS[0]

    def _rebuild_field_buttons(self):
        """
        按当前票种的字段集重建字段按钮网格

        功能描述:
            不同票种字段数从 4 到 10 不等，3 列布局的行数会变，
            因此清空重排而不是全部创建后切换可见性。
        """
        # 清空既有按钮
        while self._fields_grid.count():
            item = self._fields_grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

        fields = get_fields(self._current_type_key())
        for i, (display_name, _field_key) in enumerate(fields):
            row, col = divmod(i, 3)
            btn = QPushButton(display_name)
            btn.setObjectName("fieldButton")
            # 用显示名作为占位符内容
            btn.setProperty("field_name", display_name)
            btn.clicked.connect(self._on_field_button_clicked)
            self._fields_grid.addWidget(btn, row, col)

    def _on_type_changed(self):
        """
        票种切换处理

        功能描述:
            丢弃未保存的输入，载入该票种已保存的规则；
            若该票种无已保存规则，则预填默认模板（仅显示，不落盘）。
            随后重建该票种的字段按钮。
        """
        if self._fields_grid is None:
            return

        self._current_type = self._current_type_key()

        saved = self._saved_rules.get(self._current_type, '')
        if saved:
            # 有已保存规则：显示已存规则
            self.rule_input.setText(saved)
        else:
            # 无已保存规则：预填默认模板（仅显示，不写入配置）
            self.rule_input.setText(get_default_template(self._current_type))

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
                self.type_combo.setCurrentIndex(idx)
                return
        self.type_combo.setCurrentIndex(0)

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
        lines.append("1. 每种发票类型各有一套规则，切换「发票类型」分别配置")
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
