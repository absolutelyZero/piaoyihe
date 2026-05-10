#!/usr/bin/env python3
"""
批量重命名对话框模块

该模块提供批量重命名配置对话框，允许用户根据发票字段自定义文件名规则
支持字段：发票类型、商品类型、开票日期、买方名字、销方名字、金额
"""

import os
import re
import json
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTextEdit, QGridLayout, QFrame, QMessageBox,
    QScrollArea, QWidget
)
from PySide6.QtCore import Qt, Signal


# 配色方案 - 与主界面保持一致
PRIMARY_COLOR = "#2196F3"
PRIMARY_HOVER = "#1976D2"
SUCCESS_COLOR = "#4CAF50"
WARNING_COLOR = "#FF9800"
DANGER_COLOR = "#F44336"
BG_COLOR = "#F5F5F5"
CARD_BG = "#FFFFFF"
BORDER_COLOR = "#E0E0E0"
TEXT_PRIMARY = "#212121"
TEXT_SECONDARY = "#757575"
TEXT_MUTED = "#9E9E9E"


class RenameDialog(QDialog):
    """
    批量重命名对话框类
    
    功能描述:
        提供批量重命名规则配置界面，支持字段占位符插入、规则保存和执行
    
    信号:
        rule_saved: 当规则保存时发出，参数为规则字符串
        rename_executed: 当执行重命名时发出，参数为规则字符串
    
    参数:
        parent: 父窗口
        config_file: 配置文件路径
        current_rule: 当前规则字符串
    """
    
    rule_saved = Signal(str)
    rename_executed = Signal(str)
    
    # 可用字段定义
    AVAILABLE_FIELDS = [
        ("发票类型", "发票类型"),
        ("商品类型", "商品类型"),
        ("开票日期", "开票日期"),
        ("买方名字", "买方名字"),
        ("销方名字", "销方名字"),
        ("金额", "金额"),
    ]
    
    # Windows文件名非法字符
    INVALID_CHARS = r'[<>:"/\\|?*]'
    
    def __init__(self, parent=None, config_file=None, current_rule=""):
        """
        初始化重命名对话框
        
        参数:
            parent: 父窗口
            config_file: 配置文件路径
            current_rule: 当前规则字符串
        """
        super().__init__(parent)
        
        self.config_file = config_file
        self.current_rule = current_rule
        
        self._init_ui()
        self._setup_stylesheet()
        self._load_rule_from_config()
    
    def _init_ui(self):
        """
        初始化用户界面
        
        功能描述:
            创建对话框的所有UI控件和布局
        """
        self.setWindowTitle("批量重命名设置")
        self.setMinimumSize(600, 500)
        self.setModal(True)
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # ========== 标题区域 ==========
        title_layout = QHBoxLayout()
        
        title_label = QLabel("📋 请设置重命名文件的规则")
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
        
        # 规则输入框
        self.rule_input = QLineEdit()
        self.rule_input.setObjectName("ruleInput")
        self.rule_input.setPlaceholderText("请输入文件名规则，点击以下按钮，可插入发票中的相关字段信息")
        self.rule_input.setText(self.current_rule)
        self.rule_input.setMinimumHeight(36)
        input_layout.addWidget(self.rule_input)
        
        # 字段按钮网格
        fields_label = QLabel("点击插入字段：")
        fields_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")
        input_layout.addWidget(fields_label)
        
        fields_grid = QGridLayout()
        fields_grid.setSpacing(8)
        
        for i, (field_name, field_key) in enumerate(self.AVAILABLE_FIELDS):
            row = i // 3
            col = i % 3
            btn = QPushButton(field_name)
            btn.setObjectName("fieldButton")
            btn.setProperty("field_key", field_key)
            btn.clicked.connect(self._on_field_button_clicked)
            fields_grid.addWidget(btn, row, col)
        
        input_layout.addLayout(fields_grid)
        
        # 操作按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        
        self.save_btn = QPushButton("💾 保存")
        self.save_btn.setObjectName("saveButton")
        self.save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(self.save_btn)
        
        self.clear_btn = QPushButton("🗑️ 清空")
        self.clear_btn.setObjectName("clearButton")
        self.clear_btn.clicked.connect(self._on_clear)
        btn_layout.addWidget(self.clear_btn)
        
        btn_layout.addStretch()
        
        self.execute_btn = QPushButton("▶️ 执行重命名")
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
            "1. 默认不会修改文件名，如果要改，就修改上面的内容。<br>"
            "2. 在你设置的文件名内容中间插入上面预置的模板，会使用发票中的内容替换。<br>"
            "3. 如果不需要改文件名，就保持为空，或者保持默认内容就行。<br>"
            "4. 如果发票中没有识别出你选定的模板内容，则会保留相应的模板内容。<br>"
            "5. 举例：张三10月份报销-[开票日期]-[商品类型]<br>"
            "6. 不能用作文件名的字符：&lt; &gt; : \" / \\ | ? *"
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
                background-color: #FAFAFA;
                border-color: #BDBDBD;
            }}
            
            QPushButton:pressed {{
                background-color: #F0F0F0;
            }}
            
            QPushButton#fieldButton {{
                background-color: #E3F2FD;
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
    
    def _on_field_button_clicked(self):
        """
        字段按钮点击处理
        
        功能描述:
            将字段占位符插入到规则输入框的当前光标位置
        """
        sender = self.sender()
        if sender:
            field_key = sender.property("field_key")
            if field_key:
                # 在光标位置插入占位符
                cursor_pos = self.rule_input.cursorPosition()
                current_text = self.rule_input.text()
                placeholder = f"{{{field_key}}}"
                new_text = current_text[:cursor_pos] + placeholder + current_text[cursor_pos:]
                self.rule_input.setText(new_text)
                # 移动光标到插入内容之后
                self.rule_input.setCursorPosition(cursor_pos + len(placeholder))
                self.rule_input.setFocus()
    
    def _on_save(self):
        """
        保存按钮点击处理
        
        功能描述:
            保存当前规则到配置文件
        """
        rule = self.rule_input.text().strip()
        
        # 保存到配置文件
        if self.config_file and os.path.exists(os.path.dirname(self.config_file)):
            try:
                config = {}
                if os.path.exists(self.config_file):
                    with open(self.config_file, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                
                config['rename_rule'] = rule
                
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)
                
                self.rule_saved.emit(rule)
                QMessageBox.information(self, "保存成功", "重命名规则已保存！")
            except Exception as e:
                QMessageBox.warning(self, "保存失败", f"保存规则失败: {str(e)}")
        else:
            self.rule_saved.emit(rule)
            QMessageBox.information(self, "保存成功", "重命名规则已保存！")
    
    def _on_clear(self):
        """
        清空按钮点击处理
        
        功能描述:
            清空规则输入框的内容
        """
        self.rule_input.clear()
        self.rule_input.setFocus()
    
    def _on_execute(self):
        """
        执行按钮点击处理
        
        功能描述:
            执行批量重命名操作
        """
        rule = self.rule_input.text().strip()
        
        if not rule:
            QMessageBox.warning(self, "提示", "请输入重命名规则")
            return
        
        # 发出执行信号
        self.rename_executed.emit(rule)
        
        # 关闭对话框
        self.accept()
    
    def _show_help(self):
        """
        显示帮助信息
        
        功能描述:
            显示详细的使用说明
        """
        help_text = (
            "批量重命名功能使用说明：\n\n"
            "1. 在输入框中输入文件名规则\n"
            "2. 点击字段按钮插入占位符（如 {开票日期}）\n"
            "3. 占位符会被替换为对应的发票信息\n"
            "4. 点击保存可保存规则供下次使用\n"
            "5. 点击执行开始批量重命名\n\n"
            "可用字段：\n"
            "• {发票类型} - 发票类型（普票、专票等）\n"
            "• {商品类型} - 商品或服务名称\n"
            "• {开票日期} - 开票日期（YYYY-MM-DD）\n"
            "• {买方名字} - 购买方名称\n"
            "• {销方名字} - 销售方名称\n"
            "• {金额} - 发票金额\n\n"
            "示例：\n"
            "• 张三报销-{开票日期}-{商品类型}\n"
            "• {销方名字}_{开票日期}_{金额}元"
        )
        QMessageBox.information(self, "变量说明", help_text)
    
    def _load_rule_from_config(self):
        """
        从配置文件加载规则
        
        功能描述:
            加载之前保存的重命名规则
        """
        if self.config_file and os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                rule = config.get('rename_rule', '')
                if rule:
                    self.rule_input.setText(rule)
            except Exception as e:
                print(f"加载规则失败: {e}")
    
    def get_rule(self):
        """
        获取当前规则
        
        返回值:
            str: 当前规则字符串
        """
        return self.rule_input.text().strip()
    
    @staticmethod
    def sanitize_filename(filename):
        """
        清理文件名，移除非法字符
        
        参数:
            filename: 原始文件名
            
        返回值:
            str: 清理后的文件名
        """
        # 替换Windows文件名非法字符
        sanitized = re.sub(RenameDialog.INVALID_CHARS, '_', filename)
        # 移除首尾空格和点
        sanitized = sanitized.strip('. ')
        # 如果文件名为空，返回默认值
        if not sanitized:
            sanitized = "未命名"
        return sanitized
    
    @staticmethod
    def apply_rule(rule, file_info):
        """
        应用重命名规则
        
        参数:
            rule: 规则字符串，包含占位符
            file_info: 文件信息字典，包含各字段值
            
        返回值:
            str: 应用规则后的文件名（不含扩展名）
        """
        if not rule:
            return None
        
        result = rule
        
        # 定义字段映射
        field_mapping = {
            '发票类型': 'invoice_type',
            '商品类型': 'product_type',
            '开票日期': 'invoice_date',
            '买方名字': 'buyer_name',
            '销方名字': 'seller_name',
            '金额': 'amount',
        }
        
        # 替换所有占位符
        for field_name, field_key in field_mapping.items():
            placeholder = f"{{{field_name}}}"
            if placeholder in result:
                value = file_info.get(field_key, '')
                # 格式化金额
                if field_key == 'amount' and isinstance(value, (int, float)):
                    value = f"{value:.2f}"
                result = result.replace(placeholder, str(value))
        
        # 清理文件名
        result = RenameDialog.sanitize_filename(result)
        
        return result
