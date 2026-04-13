#!/usr/bin/env python3
"""
主窗口界面模块

该模块提供应用程序的主窗口界面，包括文件管理、布局选择、
PDF合并、结果预览和打印等功能
"""

import os
import sys
import json
import tempfile
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                                QLabel, QPushButton, QLineEdit, QCheckBox, 
                                QComboBox, QGroupBox, QRadioButton, QButtonGroup,
                                QFileDialog, QMessageBox, QDialog, QScrollArea,
                                QSizePolicy, QFrame, QProgressBar, QSplitter,
                                QTextEdit, QStackedWidget, QGridLayout)
from PySide6.QtCore import Qt, QUrl, QTimer, QSize
from PySide6.QtGui import QGuiApplication, QDesktopServices, QCursor, QPixmap, QPainter, QImage
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from ui.file_list import FileListPanel
from core.pdf_handler import PDFHandler
from core.update_checker import UpdateChecker, show_update_dialog


CONFIG_FILE = os.path.join(os.path.dirname(__file__), '../config.json')
VERSION_FILE = os.path.join(os.path.dirname(__file__), '../version.json')

# ============================================================================
# 配色方案 - 统一的样式常量
# ============================================================================
PRIMARY_COLOR = "#2196F3"      # 主色调 - 蓝色
PRIMARY_HOVER = "#1976D2"      # 主色悬停
SUCCESS_COLOR = "#4CAF50"      # 成功色 - 绿色
WARNING_COLOR = "#FF9800"      # 警告色 - 橙色
DANGER_COLOR = "#F44336"       # 危险色 - 红色
BG_COLOR = "#F5F5F5"           # 背景色 - 浅灰
CARD_BG = "#FFFFFF"            # 卡片背景 - 白色
BORDER_COLOR = "#E0E0E0"       # 边框色
TEXT_PRIMARY = "#212121"       # 主要文字
TEXT_SECONDARY = "#757575"     # 次要文字
TEXT_MUTED = "#9E9E9E"         # 弱化文字
SHADOW_COLOR = "rgba(0, 0, 0, 0.08)"  # 阴影色


class MainWindow(QMainWindow):
    """
    主窗口类
    
    功能描述:
        应用程序主窗口，提供PDF文件管理、布局选择、合并预览和打印功能
    
    参数:
        无
    """
    
    def __init__(self):
        """
        初始化主窗口
        
        功能描述:
            创建主窗口界面，初始化各个控件和布局
        """
        super().__init__()
        
        self.pdf_handler = PDFHandler()
        self.remote_version = None
        self.preview_pixmap = None
        self.preview_timer = None  # 用于延迟更新预览的定时器
        
        self._init_ui()
        self._init_drag_drop()
        self._load_config()
        self._update_stats()
        self._update_button_states()
        self._check_update_status()
    
    def _init_ui(self):
        """
        初始化用户界面
        
        功能描述:
            创建所有UI控件并设置布局
        """
        self.setWindowTitle("票易合 - 发票合并工具")
        self.setMinimumSize(1400, 800)
        
        # 设置全局样式表
        self._setup_stylesheet()
        
        central_widget = QWidget()
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # 顶部拖放提示区域
        top_widget = self._create_top_widget()
        main_layout.addWidget(top_widget)
        
        # 中间主要内容区域（文件列表 + 预览）
        middle_widget = self._create_middle_widget()
        main_layout.addWidget(middle_widget, 1)
        
        # 选项设置区域
        options_widget = self._create_options_widget()
        main_layout.addWidget(options_widget)
        
        # 操作按钮区域
        actions_widget = self._create_actions_widget()
        main_layout.addWidget(actions_widget)
        
        # 底部区域（保存路径 + 版本号）
        bottom_widget = self._create_bottom_widget()
        main_layout.addWidget(bottom_widget)
    
    def _setup_stylesheet(self):
        """
        设置全局样式表
        
        功能描述:
            配置应用程序的全局样式，包括卡片、按钮、输入框等控件的样式
        """
        self.setStyleSheet(f"""
            /* 全局样式 */
            QMainWindow {{
                background-color: {BG_COLOR};
            }}
            
            QWidget#centralWidget {{
                background-color: {BG_COLOR};
            }}
            
            /* 卡片样式 */
            QFrame#card {{
                background-color: {CARD_BG};
                border-radius: 8px;
                border: 1px solid {BORDER_COLOR};
            }}
            
            /* 标签样式 */
            QLabel {{
                color: {TEXT_PRIMARY};
                font-size: 13px;
            }}
            
            QLabel#titleLabel {{
                font-size: 16px;
                font-weight: bold;
                color: {TEXT_PRIMARY};
            }}
            
            QLabel#subtitleLabel {{
                font-size: 12px;
                color: {TEXT_SECONDARY};
            }}
            
            QLabel#hintLabel {{
                font-size: 14px;
                color: {TEXT_SECONDARY};
            }}
            
            /* 按钮基础样式 */
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
            
            QPushButton:disabled {{
                background-color: #EEEEEE;
                color: {TEXT_MUTED};
                border-color: {BORDER_COLOR};
            }}
            
            /* 主要按钮样式 */
            QPushButton#primaryButton {{
                background-color: {PRIMARY_COLOR};
                color: white;
                border: none;
                font-weight: bold;
                padding: 10px 24px;
            }}
            
            QPushButton#primaryButton:hover {{
                background-color: {PRIMARY_HOVER};
            }}
            
            QPushButton#primaryButton:pressed {{
                background-color: #1565C0;
            }}
            
            QPushButton#primaryButton:disabled {{
                background-color: #BBDEFB;
                color: white;
            }}
            
            /* 危险按钮样式 */
            QPushButton#dangerButton {{
                background-color: {DANGER_COLOR};
                color: white;
                border: none;
            }}
            
            QPushButton#dangerButton:hover {{
                background-color: #D32F2F;
            }}
            
            QPushButton#dangerButton:pressed {{
                background-color: #C62828;
            }}
            
            /* 成功按钮样式 */
            QPushButton#successButton {{
                background-color: {SUCCESS_COLOR};
                color: white;
                border: none;
            }}
            
            QPushButton#successButton:hover {{
                background-color: #388E3C;
            }}
            
            /* 图标按钮样式 */
            QPushButton#iconButton {{
                padding: 6px 12px;
                border-radius: 4px;
            }}
            
            /* 输入框样式 */
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
            
            QLineEdit:disabled {{
                background-color: #FAFAFA;
                color: {TEXT_MUTED};
            }}
            
            /* 下拉框样式 */
            QComboBox {{
                padding: 8px 12px;
                border-radius: 6px;
                border: 1px solid {BORDER_COLOR};
                background-color: {CARD_BG};
                font-size: 13px;
                color: {TEXT_PRIMARY};
                min-width: 120px;
            }}
            
            QComboBox:hover {{
                border-color: #BDBDBD;
            }}
            
            QComboBox:focus {{
                border-color: {PRIMARY_COLOR};
            }}
            
            QComboBox::drop-down {{
                border: none;
                width: 24px;
            }}
            
            QComboBox::down-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 6px solid {TEXT_SECONDARY};
                width: 0;
                height: 0;
            }}
            
            QComboBox QAbstractItemView {{
                border: 1px solid {BORDER_COLOR};
                border-radius: 6px;
                background-color: {CARD_BG};
                selection-background-color: #E3F2FD;
                selection-color: {TEXT_PRIMARY};
            }}
            
            /* 单选按钮样式 */
            QRadioButton {{
                font-size: 13px;
                color: {TEXT_PRIMARY};
                spacing: 6px;
            }}
            
            QRadioButton::indicator {{
                width: 16px;
                height: 16px;
                border-radius: 8px;
                border: 2px solid {TEXT_MUTED};
                background-color: {CARD_BG};
            }}
            
            QRadioButton::indicator:checked {{
                border-color: {PRIMARY_COLOR};
                background-color: {PRIMARY_COLOR};
            }}
            
            QRadioButton::indicator:hover {{
                border-color: {PRIMARY_COLOR};
            }}
            
            /* 复选框样式 */
            QCheckBox {{
                font-size: 13px;
                color: {TEXT_PRIMARY};
                spacing: 6px;
            }}
            
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border-radius: 3px;
                border: 2px solid {TEXT_MUTED};
                background-color: {CARD_BG};
            }}
            
            QCheckBox::indicator:checked {{
                border-color: {PRIMARY_COLOR};
                background-color: {PRIMARY_COLOR};
            }}
            
            QCheckBox::indicator:hover {{
                border-color: {PRIMARY_COLOR};
            }}
            
            /* 分组框样式 */
            QGroupBox {{
                font-size: 13px;
                font-weight: bold;
                color: {TEXT_PRIMARY};
                border: 1px solid {BORDER_COLOR};
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: {CARD_BG};
            }}
            
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px;
                color: {TEXT_SECONDARY};
                font-weight: normal;
            }}
            
            /* 滚动区域样式 */
            QScrollArea {{
                border: 1px solid {BORDER_COLOR};
                border-radius: 8px;
                background-color: #FAFAFA;
            }}
            
            /* 分割器样式 */
            QSplitter::handle {{
                background-color: {BORDER_COLOR};
            }}
            
            QSplitter::handle:horizontal {{
                width: 2px;
            }}
            
            /* 反馈按钮特殊样式 */
            QPushButton#feedbackButton {{
                background-color: {PRIMARY_COLOR};
                color: white;
                border: none;
                border-radius: 15px;
                font-weight: bold;
                font-size: 14px;
            }}
            
            QPushButton#feedbackButton:hover {{
                background-color: {PRIMARY_HOVER};
            }}
        """)
    
    def _create_top_widget(self):
        """
        创建顶部区域控件
        
        功能描述:
            创建拖放提示标签，使用卡片式背景设计
        
        返回值:
            QWidget: 顶部区域控件
        """
        # 创建卡片容器
        card = QFrame()
        card.setObjectName("card")
        card.setFrameShape(QFrame.Shape.StyledPanel)
        
        layout = QHBoxLayout(card)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)
        
        # 图标标签
        icon_label = QLabel("📄")
        icon_label.setStyleSheet("font-size: 20px; background: transparent; border: none;")
        layout.addWidget(icon_label)
        
        # 主提示文本
        self.drop_label = QLabel("拖入PDF文件到下方列表，或使用右侧预览区域查看合并效果")
        self.drop_label.setObjectName("titleLabel")
        self.drop_label.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {TEXT_PRIMARY}; background: transparent; border: none;")
        layout.addWidget(self.drop_label)
        layout.addStretch()
        
        # 反馈按钮
        self.feedback_button = QPushButton("?")
        self.feedback_button.setObjectName("feedbackButton")
        self.feedback_button.setFixedSize(30, 30)
        self.feedback_button.setToolTip("反馈问题")
        self.feedback_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.feedback_button.clicked.connect(self._on_feedback)
        layout.addWidget(self.feedback_button)
        
        return card
    
    def _create_middle_widget(self):
        """
        创建中间主要内容区域
        
        功能描述:
            创建包含文件列表和预览区域的分割器，使用卡片式布局
        
        返回值:
            QWidget: 中间区域控件
        """
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        
        # 使用分割器实现可调整大小的左右布局
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(2)
        
        # 左侧：文件列表卡片
        file_list_card = QFrame()
        file_list_card.setObjectName("card")
        file_list_card.setFrameShape(QFrame.Shape.StyledPanel)
        
        file_list_layout = QVBoxLayout(file_list_card)
        file_list_layout.setContentsMargins(16, 16, 16, 16)
        file_list_layout.setSpacing(12)
        
        # 文件列表标题
        file_list_header = QHBoxLayout()
        file_list_icon = QLabel("📁")
        file_list_icon.setStyleSheet("font-size: 16px; background: transparent; border: none;")
        file_list_header.addWidget(file_list_icon)
        
        file_list_label = QLabel("文件列表")
        file_list_label.setObjectName("titleLabel")
        file_list_label.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {TEXT_PRIMARY}; background: transparent; border: none;")
        file_list_header.addWidget(file_list_label)
        file_list_header.addStretch()
        file_list_layout.addLayout(file_list_header)
        
        # 文件列表组件
        self.file_list = FileListPanel(self.pdf_handler, on_file_added=self._on_first_file_added)
        self.file_list.selection_changed.connect(self._on_list_selection_changed)
        self.file_list.setStyleSheet(f"background-color: {CARD_BG}; border: none;")
        file_list_layout.addWidget(self.file_list)
        
        splitter.addWidget(file_list_card)
        
        # 右侧：预览区域卡片
        preview_card = QFrame()
        preview_card.setObjectName("card")
        preview_card.setFrameShape(QFrame.Shape.StyledPanel)
        
        preview_layout = QVBoxLayout(preview_card)
        preview_layout.setContentsMargins(16, 16, 16, 16)
        preview_layout.setSpacing(12)
        
        # 预览区域标题栏
        preview_header = QHBoxLayout()
        preview_icon = QLabel("👁")
        preview_icon.setStyleSheet("font-size: 16px; background: transparent; border: none;")
        preview_header.addWidget(preview_icon)
        
        preview_label = QLabel("合并预览")
        preview_label.setObjectName("titleLabel")
        preview_label.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {TEXT_PRIMARY}; background: transparent; border: none;")
        preview_header.addWidget(preview_label)
        
        self.preview_status_label = QLabel("(添加文件后自动更新)")
        self.preview_status_label.setObjectName("subtitleLabel")
        self.preview_status_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px; background: transparent; border: none;")
        preview_header.addWidget(self.preview_status_label)
        preview_header.addStretch()
        
        # 刷新预览按钮
        self.refresh_preview_btn = QPushButton("🔄 刷新")
        self.refresh_preview_btn.setObjectName("iconButton")
        self.refresh_preview_btn.setToolTip("手动刷新预览")
        self.refresh_preview_btn.clicked.connect(self._update_preview)
        self.refresh_preview_btn.setEnabled(False)
        preview_header.addWidget(self.refresh_preview_btn)
        
        preview_layout.addLayout(preview_header)
        
        # 预览内容区域
        self.preview_stack = QStackedWidget()
        
        # 页面1：提示信息（使用渐变色背景）
        placeholder_container = QFrame()
        placeholder_container.setObjectName("card")
        placeholder_container.setStyleSheet(f"""
            QFrame#card {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #E3F2FD,
                    stop:0.5 #F3E5F5,
                    stop:1 #E8F5E9);
                border: 2px dashed {PRIMARY_COLOR};
                border-radius: 12px;
            }}
        """)
        
        placeholder_layout = QVBoxLayout(placeholder_container)
        
        self.preview_placeholder = QLabel("📄\n\n添加PDF文件后，此处将显示合并后的预览效果\n\n支持实时预览，调整选项后自动更新")
        self.preview_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_placeholder.setStyleSheet(f"""
            color: {TEXT_SECONDARY};
            font-size: 14px;
            background: transparent;
            border: none;
        """)
        placeholder_layout.addWidget(self.preview_placeholder)
        
        self.preview_stack.addWidget(placeholder_container)
        
        # 页面2：图片预览
        self.preview_scroll = QScrollArea()
        self.preview_scroll.setWidgetResizable(True)
        self.preview_scroll.setStyleSheet(f"""
            QScrollArea {{
                background-color: #FAFAFA;
                border: 1px solid {BORDER_COLOR};
                border-radius: 8px;
            }}
        """)
        
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet("background-color: transparent; border: none;")
        self.preview_scroll.setWidget(self.preview_label)
        
        self.preview_stack.addWidget(self.preview_scroll)
        
        preview_layout.addWidget(self.preview_stack)
        
        splitter.addWidget(preview_card)
        
        # 设置分割器比例（左:右 = 4:6）
        splitter.setSizes([560, 840])
        
        layout.addWidget(splitter)
        
        return widget
    
    def _create_options_widget(self):
        """
        创建选项设置区域
        
        功能描述:
            创建包含布局选择、模式选择、打印顺序等选项的卡片式布局
        
        返回值:
            QWidget: 选项设置区域控件
        """
        # 创建卡片容器
        card = QFrame()
        card.setObjectName("card")
        card.setFrameShape(QFrame.Shape.StyledPanel)
        
        layout = QHBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(24)
        
        # 布局选择区域（使用卡片式按钮组）
        layout_container = QVBoxLayout()
        layout_container.setSpacing(10)
        
        layout_header = QHBoxLayout()
        layout_icon = QLabel("🎨")
        layout_icon.setStyleSheet("font-size: 14px; background: transparent; border: none;")
        layout_header.addWidget(layout_icon)
        
        layout_title = QLabel("布局选择")
        layout_title.setObjectName("titleLabel")
        layout_title.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {TEXT_PRIMARY}; background: transparent; border: none;")
        layout_header.addWidget(layout_title)
        layout_header.addStretch()
        layout_container.addLayout(layout_header)
        
        # 布局按钮组（横向排列）
        layout_buttons = QHBoxLayout()
        layout_buttons.setSpacing(8)
        
        self.layout_button_group = QButtonGroup(self)
        
        # 创建布局选择按钮
        layout_options = [
            ("竖向 1x2", "1×2"),
            ("竖向 1x3", "1×3"),
            ("竖向 2x4", "2×4"),
            ("横向 2x2", "2×2")
        ]
        
        for i, (full_name, short_name) in enumerate(layout_options):
            radio = QRadioButton(short_name)
            radio.setToolTip(full_name)
            radio.setMinimumWidth(50)
            radio.setStyleSheet(f"""
                QRadioButton {{
                    font-size: 13px;
                    font-weight: 500;
                    padding: 4px 8px;
                }}
                QRadioButton::indicator {{
                    width: 0px;
                    height: 0px;
                }}
                QRadioButton::checked {{
                    color: {PRIMARY_COLOR};
                    font-weight: bold;
                }}
            """)
            self.layout_button_group.addButton(radio)
            layout_buttons.addWidget(radio)
            
            # 存储引用
            if i == 0:
                self.radio_1x2 = radio
            elif i == 1:
                self.radio_1x3 = radio
            elif i == 2:
                self.radio_2x4 = radio
            else:
                self.radio_2x2 = radio
        
        # 默认选中横向 2x2
        self.radio_2x2.setChecked(True)
        
        # 连接布局变更信号
        self.radio_1x2.toggled.connect(self._on_config_changed)
        self.radio_1x3.toggled.connect(self._on_config_changed)
        self.radio_2x4.toggled.connect(self._on_config_changed)
        self.radio_2x2.toggled.connect(self._on_config_changed)
        
        layout_container.addLayout(layout_buttons)
        layout.addLayout(layout_container)
        
        # 添加分隔线
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.Shape.VLine)
        separator1.setStyleSheet(f"color: {BORDER_COLOR};")
        separator1.setFixedWidth(1)
        layout.addWidget(separator1)
        
        # 模式选择区域
        mode_container = QVBoxLayout()
        mode_container.setSpacing(10)
        
        mode_header = QHBoxLayout()
        mode_icon = QLabel("⚙")
        mode_icon.setStyleSheet("font-size: 14px; background: transparent; border: none;")
        mode_header.addWidget(mode_icon)
        
        mode_title = QLabel("处理模式")
        mode_title.setObjectName("titleLabel")
        mode_title.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {TEXT_PRIMARY}; background: transparent; border: none;")
        mode_header.addWidget(mode_title)
        mode_header.addStretch()
        mode_container.addLayout(mode_header)
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["普通", "图像"])
        self.mode_combo.setToolTip("普通模式保留PDF矢量信息，图像模式转换为图片（兼容性更好）")
        self.mode_combo.currentIndexChanged.connect(self._on_config_changed)
        mode_container.addWidget(self.mode_combo)
        mode_container.addStretch()
        
        layout.addLayout(mode_container)
        
        # 添加分隔线
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.Shape.VLine)
        separator2.setStyleSheet(f"color: {BORDER_COLOR};")
        separator2.setFixedWidth(1)
        layout.addWidget(separator2)
        
        # 打印顺序选择区域
        order_container = QVBoxLayout()
        order_container.setSpacing(10)
        
        order_header = QHBoxLayout()
        order_icon = QLabel("📋")
        order_icon.setStyleSheet("font-size: 14px; background: transparent; border: none;")
        order_header.addWidget(order_icon)
        
        order_title = QLabel("排序方式")
        order_title.setObjectName("titleLabel")
        order_title.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {TEXT_PRIMARY}; background: transparent; border: none;")
        order_header.addWidget(order_title)
        order_header.addStretch()
        order_container.addLayout(order_header)
        
        self.order_combo = QComboBox()
        self.order_combo.addItems(["列表顺序", "开票日期(从先到后)", "开票金额(从小到大)"])
        self.order_combo.setToolTip("选择发票的排序方式")
        self.order_combo.currentIndexChanged.connect(self._on_config_changed)
        order_container.addWidget(self.order_combo)
        order_container.addStretch()
        
        layout.addLayout(order_container)
        layout.addStretch()
        
        return card
    
    def _create_actions_widget(self):
        """
        创建操作按钮区域
        
        功能描述:
            创建包含添加文件、删除、移动、合并、打印等操作按钮的卡片式布局
        
        返回值:
            QWidget: 操作按钮区域控件
        """
        # 创建卡片容器
        card = QFrame()
        card.setObjectName("card")
        card.setFrameShape(QFrame.Shape.StyledPanel)
        
        layout = QHBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)
        
        # 文件操作组
        file_ops_layout = QHBoxLayout()
        file_ops_layout.setSpacing(8)
        
        file_ops_icon = QLabel("📂")
        file_ops_icon.setStyleSheet("font-size: 14px; background: transparent; border: none;")
        file_ops_layout.addWidget(file_ops_icon)
        
        # 添加文件按钮
        self.add_file_btn = QPushButton("➕ 添加")
        self.add_file_btn.setObjectName("iconButton")
        self.add_file_btn.setToolTip("添加PDF文件到列表")
        self.add_file_btn.clicked.connect(self._on_add_file)
        file_ops_layout.addWidget(self.add_file_btn)
        
        # 删除选中按钮
        self.del_btn = QPushButton("🗑️ 删除")
        self.del_btn.setObjectName("iconButton")
        self.del_btn.setToolTip("删除选中的文件")
        self.del_btn.clicked.connect(self._on_del)
        file_ops_layout.addWidget(self.del_btn)
        
        # 删除所有按钮（危险操作）
        self.del_all_btn = QPushButton("❌ 清空")
        self.del_all_btn.setObjectName("dangerButton")
        self.del_all_btn.setToolTip("清空所有文件")
        self.del_all_btn.clicked.connect(self._on_del_all)
        file_ops_layout.addWidget(self.del_all_btn)
        
        layout.addLayout(file_ops_layout)
        
        # 添加分隔线
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.Shape.VLine)
        separator1.setStyleSheet(f"color: {BORDER_COLOR};")
        separator1.setFixedWidth(1)
        layout.addWidget(separator1)
        
        # 排序操作组
        sort_ops_layout = QHBoxLayout()
        sort_ops_layout.setSpacing(8)
        
        sort_ops_icon = QLabel("🔃")
        sort_ops_icon.setStyleSheet("font-size: 14px; background: transparent; border: none;")
        sort_ops_layout.addWidget(sort_ops_icon)
        
        # 上移按钮
        self.move_up_btn = QPushButton("⬆️ 上移")
        self.move_up_btn.setObjectName("iconButton")
        self.move_up_btn.setToolTip("将选中的文件上移一位")
        self.move_up_btn.clicked.connect(self._on_move_up)
        sort_ops_layout.addWidget(self.move_up_btn)
        
        # 下移按钮
        self.move_down_btn = QPushButton("⬇️ 下移")
        self.move_down_btn.setObjectName("iconButton")
        self.move_down_btn.setToolTip("将选中的文件下移一位")
        self.move_down_btn.clicked.connect(self._on_move_down)
        sort_ops_layout.addWidget(self.move_down_btn)
        
        layout.addLayout(sort_ops_layout)
        
        # 添加分隔线
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.Shape.VLine)
        separator2.setStyleSheet(f"color: {BORDER_COLOR};")
        separator2.setFixedWidth(1)
        layout.addWidget(separator2)
        
        # 主要操作组
        main_ops_layout = QHBoxLayout()
        main_ops_layout.setSpacing(12)
        
        main_ops_icon = QLabel("⚡")
        main_ops_icon.setStyleSheet("font-size: 14px; background: transparent; border: none;")
        main_ops_layout.addWidget(main_ops_icon)
        
        # 合并按钮（主要操作）
        self.merge_btn = QPushButton("🔀 合并PDF")
        self.merge_btn.setObjectName("primaryButton")
        self.merge_btn.setToolTip("合并所有文件并保存")
        self.merge_btn.setMinimumWidth(120)
        self.merge_btn.clicked.connect(self._on_merge_all)
        main_ops_layout.addWidget(self.merge_btn)
        
        # 打印复选框
        self.print_checkbox = QCheckBox("🖨️ 合并后打印")
        self.print_checkbox.setToolTip("合并后自动打印")
        self.print_checkbox.setStyleSheet(f"font-size: 13px; color: {TEXT_PRIMARY};")
        main_ops_layout.addWidget(self.print_checkbox)
        
        layout.addLayout(main_ops_layout)
        layout.addStretch()
        
        return card
    
    def _create_bottom_widget(self):
        """
        创建底部区域控件
        
        功能描述:
            创建保存路径输入框、选择按钮和版本号标签，使用卡片式布局
        
        返回值:
            QWidget: 底部区域控件
        """
        # 创建卡片容器
        card = QFrame()
        card.setObjectName("card")
        card.setFrameShape(QFrame.Shape.StyledPanel)
        
        layout = QHBoxLayout(card)
        layout.setContentsMargins(20, 14, 20, 14)
        layout.setSpacing(12)
        
        # 保存路径标签
        path_icon = QLabel("💾")
        path_icon.setStyleSheet("font-size: 14px; background: transparent; border: none;")
        layout.addWidget(path_icon)
        
        path_label = QLabel("保存路径:")
        path_label.setObjectName("titleLabel")
        path_label.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {TEXT_PRIMARY}; background: transparent; border: none;")
        layout.addWidget(path_label)
        
        # 保存路径输入框
        self.path_edit = QLineEdit()
        self.path_edit.setObjectName("pathInput")
        self.path_edit.setPlaceholderText("选择合并后的PDF保存位置...")
        self.path_edit.setMinimumWidth(400)
        layout.addWidget(self.path_edit, 1)
        
        # 选择路径按钮
        self.select_path_btn = QPushButton("📂 浏览...")
        self.select_path_btn.setObjectName("iconButton")
        self.select_path_btn.setToolTip("选择保存位置")
        self.select_path_btn.clicked.connect(self._on_select_path)
        layout.addWidget(self.select_path_btn)
        
        # 添加弹性空间
        layout.addSpacing(30)
        
        # 版本号标签（可点击检查更新）
        version_icon = QLabel("🏷")
        version_icon.setStyleSheet("font-size: 12px; background: transparent; border: none;")
        layout.addWidget(version_icon)
        
        self.version_label = QLabel(self._get_version())
        self.version_label.setObjectName("versionLabel")
        self.version_label.setStyleSheet(f"""
            color: {TEXT_SECONDARY};
            font-size: 12px;
            padding: 4px 8px;
            border-radius: 4px;
            background: transparent;
            border: none;
        """)
        self.version_label.setToolTip("点击检查更新")
        self.version_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.version_label.mousePressEvent = lambda event: self._on_version_click()
        layout.addWidget(self.version_label)
        
        return card
    
    def _init_drag_drop(self):
        """
        初始化拖放功能
        
        功能描述:
            启用主窗口的拖放功能
        """
        self.setAcceptDrops(True)
    
    def _get_current_layout(self):
        """
        获取当前选中的布局类型
        
        功能描述:
            根据单选按钮的状态返回对应的布局字符串
        
        返回值:
            str: 布局类型字符串（"竖向 1x2"、"竖向 1x3"、"竖向 2x4"、"横向 2x2"）
        """
        if self.radio_1x2.isChecked():
            return "竖向 1x2"
        elif self.radio_1x3.isChecked():
            return "竖向 1x3"
        elif self.radio_2x4.isChecked():
            return "竖向 2x4"
        else:
            return "横向 2x2"
    
    def _get_version(self):
        """
        获取当前版本号
        
        功能描述:
            从version.json文件中读取当前版本号
        
        返回值:
            str: 版本号字符串（如"v0.0.3"）
        """
        try:
            if os.path.exists(VERSION_FILE):
                with open(VERSION_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    version = data.get('version', '0.0.0')
                    return f"v{version}"
            return "v0.0.0"
        except Exception as e:
            print(f"读取版本号失败: {e}")
            return "v0.0.0"
    
    def _get_current_sort_by(self):
        """
        获取当前选中的排序方式
        
        功能描述:
            根据排序下拉框的当前选项返回对应的排序字段
        
        返回值:
            str: 排序字段（"name"、"date"、"size"）
        """
        sort_text = self.order_combo.currentText()
        sort_map = {
            "列表顺序": "list",
            "开票日期(从先到后)": "date",
            "开票金额(从小到大)": "amount"
        }
        return sort_map.get(sort_text, "list")
    
    def _on_config_changed(self):
        """
        配置改变时的处理
        
        功能描述:
            当用户修改布局、排序等配置时，延迟更新预览
        """
        # 延迟更新预览，避免频繁操作
        if self.preview_timer:
            self.preview_timer.stop()
        self.preview_timer = QTimer(self)
        self.preview_timer.setSingleShot(True)
        self.preview_timer.timeout.connect(self._update_preview)
        self.preview_timer.start(500)  # 500ms 延迟
        
        # 保存配置
        self._save_config()
    
    def _update_preview(self):
        """
        更新预览图像
        
        功能描述:
            生成并显示合并后的PDF预览图像，使用临时文件进行预览，不影响正式合并
            预览只显示前2页内容以提高性能
        """
        files = self.file_list.get_all_files()
        
        if not files:
            # 没有文件时显示占位符
            self.preview_stack.setCurrentIndex(0)
            self.preview_status_label.setText("(添加文件后自动更新)")
            self.refresh_preview_btn.setEnabled(False)
            return
        
        # 显示加载状态
        self.preview_status_label.setText("正在生成预览...")
        self.refresh_preview_btn.setEnabled(False)
        QGuiApplication.processEvents()
        
        try:
            # 生成预览图像
            pixmap = self._generate_preview_image()
            
            if pixmap and not pixmap.isNull():
                self.preview_pixmap = pixmap
                self.preview_label.setPixmap(pixmap)
                self.preview_stack.setCurrentIndex(1)
                self.preview_status_label.setText(f"(预览全部页面，共{len(files)}个文件)")
            else:
                self.preview_status_label.setText("(预览生成失败)")
                
        except Exception as e:
            print(f"预览生成失败: {str(e)}")
            self.preview_status_label.setText("(预览生成失败)")
        
        self.refresh_preview_btn.setEnabled(True)
    
    def _generate_preview_image(self):
        """
        生成预览图像
        
        功能描述:
            使用PDFHandler合并全部PDF页面作为预览图像，使用临时文件存储预览结果
            预览图像会被缩放以适应预览区域，保持A4宽高比
        
        返回值:
            QPixmap: 生成的预览图像，如果失败则返回None
        """
        files = self.file_list.get_all_files()
        if not files:
            return None
        
        # 创建临时文件用于预览
        temp_fd = None
        temp_path = None
        
        try:
            # 获取当前配置
            layout = self._get_current_layout()
            mode = self.mode_combo.currentText()
            sort_by = self._get_current_sort_by()
            
            # 根据排序方式获取文件列表（全部文件）
            if sort_by == 'list':
                files_to_preview = files
            else:
                files_to_preview = self.file_list.get_sorted_files(sort_by)
            
            # 创建临时文件
            temp_fd, temp_path = tempfile.mkstemp(suffix='.pdf')
            os.close(temp_fd)
            
            # 调用PDFHandler合并PDF（全部页面）
            mode_str = "图像" if mode == 1 else "普通"
            result = self.pdf_handler.merge_pdfs(
                files_to_preview, 
                temp_path, 
                layout, 
                mode_str
            )
            
            if result and os.path.exists(temp_path):
                # 使用PyMuPDF将PDF转换为图像
                import fitz
                doc = fitz.open(temp_path)
                
                if len(doc) > 0:
                    # 获取第一页作为预览
                    page = doc[0]
                    # 使用较低分辨率以提高性能，但保持A4比例
                    mat = fitz.Matrix(1.2, 1.2)  # 缩放比例
                    pix = page.get_pixmap(matrix=mat)
                    
                    # 转换为QPixmap
                    img_data = pix.tobytes("png")
                    pixmap = QPixmap()
                    pixmap.loadFromData(img_data)
                    
                    # 缩放以适应预览区域，保持A4比例（宽度约595pt，高度约842pt）
                    # 预览区域宽度约650px，按A4比例计算高度
                    preview_width = 650
                    preview_height = int(preview_width * 842 / 595)  # A4比例
                    if pixmap.width() > preview_width or pixmap.height() > preview_height:
                        pixmap = pixmap.scaled(
                            preview_width, 
                            preview_height,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation
                        )
                    
                    doc.close()
                    
                    # 清理临时文件
                    try:
                        os.unlink(temp_path)
                    except:
                        pass
                    
                    return pixmap
                
                doc.close()
            
            # 清理临时文件
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except:
                    pass
            
            return None
            
        except Exception as e:
            print(f"生成预览图像失败: {str(e)}")
            # 清理临时文件
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except:
                    pass
            return None
    
    def _on_del(self):
        """
        删除选中的文件
        
        功能描述:
            从文件列表中删除当前选中的文件
        """
        self.file_list.delete_selected()
        self._update_stats()
        self._update_button_states()
        self._update_preview()
        self._save_config()
    
    def _on_del_all(self):
        """
        删除所有文件
        
        功能描述:
            清空文件列表中的所有文件
        """
        self.file_list.clear_all()
        self._update_stats()
        self._update_button_states()
        self._update_preview()
        self._save_config()
    
    def _on_add_file(self):
        """
        添加文件按钮点击处理
        
        功能描述:
            打开文件对话框让用户选择PDF文件
        """
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "选择PDF文件",
            "",
            "PDF文件 (*.pdf)"
        )
        
        if files:
            for file_path in files:
                self.file_list.add_file(file_path)
            self._update_stats()
            self._update_button_states()
    
    def _on_merge_all(self):
        """
        合并所有文件
        
        功能描述:
            将所有PDF文件按照选定的布局合并成一个文件
        """
        files = self.file_list.get_all_files()
        if not files:
            QMessageBox.warning(self, "警告", "请先添加PDF文件")
            return
        
        # 获取输出路径
        output_path = self.path_edit.text().strip()
        if not output_path:
            QMessageBox.warning(self, "警告", "请选择输出路径")
            return
        
        # 确保输出目录存在
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法创建输出目录: {str(e)}")
                return
        
        # 获取布局配置
        layout_type = self._get_current_layout()
        mode = self.mode_combo.currentText()
        
        try:
            # 显示进度
            self.merge_btn.setEnabled(False)
            self.merge_btn.setText("合并中...")
            QGuiApplication.processEvents()
            
            # 执行合并
            result = self.pdf_handler.merge_pdfs(
                files,
                output_path,
                layout=layout_type,
                mode=mode
            )
            
            if result:
                QMessageBox.information(self, "成功", f"PDF合并完成！\n保存至: {output_path}")
                
                # 如果勾选了打印选项，则打开打印
                if self.print_checkbox.isChecked():
                    self._on_print()
            else:
                QMessageBox.warning(self, "警告", "合并失败，请检查文件")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"合并失败: {str(e)}")
        finally:
            self.merge_btn.setEnabled(True)
            self.merge_btn.setText("🔀 合并PDF")
    
    def _update_progress(self, value):
        """
        更新进度条
        
        参数:
            value (int): 进度值（0-100）
        """
        self.progress_bar.setValue(value)
    
    def _on_select_path(self):
        """
        选择输出路径
        
        功能描述:
            打开保存对话框让用户选择输出文件路径
        """
        current_path = self.path_edit.text().strip()
        default_dir = os.path.dirname(current_path) if current_path else ""
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "选择保存位置",
            default_dir,
            "PDF文件 (*.pdf)"
        )
        
        if file_path:
            # 确保文件扩展名为.pdf
            if not file_path.lower().endswith('.pdf'):
                file_path += '.pdf'
            self.path_edit.setText(file_path)
            self._save_config()
    
    def _on_print(self):
        """
        打印功能
        
        功能描述:
            打开系统打印对话框打印当前预览的PDF
        """
        files = self.file_list.get_files()
        if not files:
            QMessageBox.warning(self, "警告", "请先添加PDF文件")
            return
        
        try:
            # 创建临时合并文件用于打印
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                tmp_path = tmp.name
            
            layout_type = self._get_current_layout()
            sort_by = self._get_current_sort_by()
            
            self.pdf_handler.merge_pdfs(
                files,
                tmp_path,
                layout=layout_type,
                sort_by=sort_by
            )
            
            # 使用系统默认程序打开打印对话框
            QDesktopServices.openUrl(QUrl.fromLocalFile(tmp_path))
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"打印失败: {str(e)}")
    
    def _on_move_up(self):
        """
        上移选中的文件
        
        功能描述:
            将当前选中的文件在列表中向上移动一位
        """
        self.file_list.move_up()
        self._update_preview()
        self._save_config()
    
    def _on_move_down(self):
        """
        下移选中的文件
        
        功能描述:
            将当前选中的文件在列表中向下移动一位
        """
        self.file_list.move_down()
        self._update_preview()
        self._save_config()
    
    def _on_feedback(self):
        """
        打开反馈对话框
        
        功能描述:
            显示用户反馈对话框，收集用户意见和建议
        """
        dialog = FeedbackDialog(self)
        dialog.exec()
    
    def _on_version_click(self):
        """
        版本号点击处理
        
        功能描述:
            点击版本号时检查更新
        """
        self._check_update_status(force_check=True)
    
    def _on_first_file_added(self, file_path):
        """
        第一个文件添加时的处理
        
        功能描述:
            当第一个文件被添加到列表时，自动设置默认输出路径
        
        参数:
            file_path: 第一个添加的文件路径
        """
        # 使用第一个文件的目录作为默认输出目录
        default_dir = os.path.dirname(file_path)
        default_name = "output.pdf"
        default_path = os.path.join(default_dir, default_name)
        
        # 设置输出路径
        self.path_edit.setText(default_path)
    
    def _on_list_selection_changed(self):
        """
        列表选择改变时的处理
        
        功能描述:
            当文件列表的选择状态改变时，更新按钮状态
        """
        self._update_button_states()
    
    def dragEnterEvent(self, event):
        """
        拖放进入事件
        
        参数:
            event: 拖放事件对象
        """
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dragMoveEvent(self, event):
        """
        拖放移动事件
        
        参数:
            event: 拖放事件对象
        """
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event):
        """
        拖放放下事件
        
        功能描述:
            处理用户拖放文件到窗口的操作
        
        参数:
            event: 拖放事件对象
        """
        urls = event.mimeData().urls()
        files = []
        
        for url in urls:
            file_path = url.toLocalFile()
            if file_path.lower().endswith('.pdf'):
                files.append(file_path)
            elif os.path.isdir(file_path):
                # 如果是目录，递归查找PDF文件
                for root, dirs, filenames in os.walk(file_path):
                    for filename in filenames:
                        if filename.lower().endswith('.pdf'):
                            files.append(os.path.join(root, filename))
        
        if files:
            for file_path in files:
                self.file_list.add_file(file_path)
            self._update_stats()
            self._update_button_states()
        
        event.acceptProposedAction()
    
    def _update_stats(self):
        """
        更新统计信息
        
        功能描述:
            更新界面统计信息，触发预览更新
        """
        files = self.file_list.get_all_files()
        file_count = len(files)
        
        # 更新预览区域状态
        if file_count > 0:
            self.preview_status_label.setText(f"({file_count} 个文件)")
            self.refresh_preview_btn.setEnabled(True)
            # 延迟更新预览
            if self.preview_timer:
                self.preview_timer.stop()
            self.preview_timer = QTimer(self)
            self.preview_timer.setSingleShot(True)
            self.preview_timer.timeout.connect(self._update_preview)
            self.preview_timer.start(500)
        else:
            self.preview_status_label.setText("(添加文件后自动更新)")
            self.refresh_preview_btn.setEnabled(False)
            self.preview_stack.setCurrentIndex(0)
    
    def _update_button_states(self):
        """
        更新按钮状态
        
        功能描述:
            根据当前文件列表状态启用或禁用相关按钮
        """
        files = self.file_list.get_all_files()
        has_files = len(files) > 0
        has_selection = len(self.file_list.get_selected_files()) > 0
        
        # 更新按钮状态
        self.del_btn.setEnabled(has_selection)
        self.del_all_btn.setEnabled(has_files)
        self.move_up_btn.setEnabled(has_selection)
        self.move_down_btn.setEnabled(has_selection)
        self.merge_btn.setEnabled(has_files)
    
    def _load_config(self):
        """
        加载配置
        
        功能描述:
            从配置文件加载用户设置
        """
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # 加载布局设置
                layout = config.get('layout', '竖向 1x2')
                if layout == '竖向 1x2':
                    self.radio_1x2.setChecked(True)
                elif layout == '竖向 1x3':
                    self.radio_1x3.setChecked(True)
                elif layout == '竖向 2x4':
                    self.radio_2x4.setChecked(True)
                else:
                    self.radio_2x2.setChecked(True)
                
                # 加载排序设置
                sort_by = config.get('order', 0)
                if 0 <= sort_by < self.order_combo.count():
                    self.order_combo.setCurrentIndex(sort_by)
                
                # 加载输出路径
                output_path = config.get('output_path', '')
                if output_path:
                    self.path_edit.setText(output_path)
                
                # 加载版本号
                version = config.get('version', '1.0.0')
                self.version_label.setText(f"v{version}")
                
        except Exception as e:
            print(f"加载配置失败: {e}")
    
    def _save_config(self):
        """
        保存配置
        
        功能描述:
            将当前用户设置保存到配置文件（增量更新，保留ignored_version）
        """
        try:
            # 读取现有配置
            config = {}
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            
            # 更新配置
            config['layout'] = self._get_current_layout()
            config['sort_by'] = self._get_current_sort_by()
            config['output_path'] = self.path_edit.text().strip()
            
            # 确保配置目录存在
            config_dir = os.path.dirname(CONFIG_FILE)
            if config_dir and not os.path.exists(config_dir):
                os.makedirs(config_dir)
            
            # 保存配置
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"保存配置失败: {e}")
    
    def _check_update_status(self, force_check=False):
        """
        检查更新状态
        
        功能描述:
            检查是否有新版本可用
        
        参数:
            force_check (bool): 是否强制检查，默认为False
        """
        try:
            # 创建更新检查器，传入必需的参数
            checker = UpdateChecker(
                local_version_file=VERSION_FILE,
                remote_version_url="https://static-mp-3141b5af-f962-41dd-a6cd-4a4a7aecff39.next.bspapp.com/pyh/version.json",
                config_file=CONFIG_FILE
            )
            
            # 检查是否有更新
            has_update, remote_version = checker.check_for_updates(ignore_ignored_version=force_check)
            
            if has_update:
                # 显示更新对话框
                qrcode_url = "https://static-mp-3141b5af-f962-41dd-a6cd-4a4a7aecff39.next.bspapp.com/pyh/updatelog.png"
                show_update_dialog(self, qrcode_url, CONFIG_FILE, remote_version)
            else:
                if force_check:
                    QMessageBox.information(self, "检查更新", "当前已是最新版本")
                    
        except Exception as e:
            print(f"检查更新失败: {e}")
            if force_check:
                QMessageBox.warning(self, "检查更新", f"检查更新失败: {str(e)}")
    
    def _is_version_newer(self, remote_version, current_version):
        """
        比较版本号
        
        功能描述:
            比较两个版本号，判断远程版本是否较新
        
        参数:
            remote_version (str): 远程版本号
            current_version (str): 当前版本号
        
        返回值:
            bool: 远程版本是否较新
        """
        try:
            remote_parts = [int(x) for x in remote_version.split('.')]
            current_parts = [int(x) for x in current_version.split('.')]
            
            # 补齐版本号位数
            while len(remote_parts) < len(current_parts):
                remote_parts.append(0)
            while len(current_parts) < len(remote_parts):
                current_parts.append(0)
            
            # 比较版本号
            for i in range(len(remote_parts)):
                if remote_parts[i] > current_parts[i]:
                    return True
                elif remote_parts[i] < current_parts[i]:
                    return False
            
            return False
        except:
            return False
    
    def closeEvent(self, event):
        """
        窗口关闭事件
        
        功能描述:
            窗口关闭时保存配置
        
        参数:
            event: 关闭事件对象
        """
        self._save_config()
        event.accept()


class FeedbackDialog(QDialog):
    """
    反馈对话框类
    
    功能描述:
        提供用户反馈功能，收集用户意见和建议
    
    参数:
        parent (QWidget): 父窗口
    """
    
    def __init__(self, parent=None):
        """
        初始化反馈对话框
        
        参数:
            parent (QWidget): 父窗口
        """
        super().__init__(parent)
        
        self.setWindowTitle("用户反馈")
        self.setMinimumSize(500, 400)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题
        title = QLabel("您的反馈对我们很重要")
        title.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #212121;
        """)
        layout.addWidget(title)
        
        # 说明文字
        desc = QLabel("请描述您遇到的问题或提出改进建议，我们会认真阅读每一条反馈。")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #757575;")
        layout.addWidget(desc)
        
        # 反馈类型
        type_layout = QHBoxLayout()
        type_label = QLabel("反馈类型:")
        type_layout.addWidget(type_label)
        
        self.type_combo = QComboBox()
        self.type_combo.addItems(["功能建议", "问题反馈", "其他"])
        type_layout.addWidget(self.type_combo)
        type_layout.addStretch()
        layout.addLayout(type_layout)
        
        # 反馈内容
        content_label = QLabel("反馈内容:")
        layout.addWidget(content_label)
        
        self.content_edit = QTextEdit()
        self.content_edit.setPlaceholderText("请输入您的反馈内容...")
        self.content_edit.setMinimumHeight(150)
        layout.addWidget(self.content_edit)
        
        # 联系邮箱（可选）
        email_label = QLabel("联系邮箱（可选）:")
        layout.addWidget(email_label)
        
        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText("请输入您的邮箱，方便我们回复您")
        layout.addWidget(self.email_edit)
        
        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)
        
        self.submit_btn = QPushButton("提交反馈")
        self.submit_btn.setObjectName("primaryButton")
        self.submit_btn.clicked.connect(self._on_submit)
        btn_layout.addWidget(self.submit_btn)
        
        layout.addLayout(btn_layout)
        
        # 设置样式
        self._setup_stylesheet()
    
    def _setup_stylesheet(self):
        """
        设置对话框样式表
        """
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {BG_COLOR};
            }}
            QLabel {{
                color: {TEXT_PRIMARY};
                font-size: 14px;
            }}
            QComboBox {{
                padding: 8px 12px;
                border: 1px solid {BORDER_COLOR};
                border-radius: 6px;
                background-color: {CARD_BG};
                min-width: 120px;
            }}
            QComboBox:hover {{
                border-color: {PRIMARY_COLOR};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 24px;
            }}
            QTextEdit {{
                padding: 12px;
                border: 1px solid {BORDER_COLOR};
                border-radius: 6px;
                background-color: {CARD_BG};
                font-size: 14px;
            }}
            QTextEdit:focus {{
                border-color: {PRIMARY_COLOR};
            }}
            QLineEdit {{
                padding: 10px 12px;
                border: 1px solid {BORDER_COLOR};
                border-radius: 6px;
                background-color: {CARD_BG};
                font-size: 14px;
            }}
            QLineEdit:focus {{
                border-color: {PRIMARY_COLOR};
            }}
            QPushButton {{
                padding: 10px 20px;
                border: 1px solid {BORDER_COLOR};
                border-radius: 6px;
                background-color: {CARD_BG};
                color: {TEXT_PRIMARY};
                font-size: 14px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {BG_COLOR};
            }}
            QPushButton#primaryButton {{
                background-color: {PRIMARY_COLOR};
                color: white;
                border: none;
            }}
            QPushButton#primaryButton:hover {{
                background-color: {PRIMARY_HOVER};
            }}
        """)
    
    def _on_submit(self):
        """
        提交反馈
        
        功能描述:
            处理用户提交反馈的操作
        """
        content = self.content_edit.toPlainText().strip()
        if not content:
            QMessageBox.warning(self, "提示", "请输入反馈内容")
            return
        
        feedback_type = self.type_combo.currentText()
        email = self.email_edit.text().strip()
        
        # 这里可以添加实际的反馈提交逻辑
        # 例如发送到服务器或保存到本地文件
        
        QMessageBox.information(self, "感谢", "感谢您的反馈！我们会认真考虑您的建议。")
        self.accept()
