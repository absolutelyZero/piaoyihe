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
                                QTextEdit, QStackedWidget, QGridLayout, QSpinBox)
from PySide6.QtCore import Qt, QUrl, QTimer, QSize
from PySide6.QtGui import QGuiApplication, QDesktopServices, QCursor, QPixmap, QPainter, QImage, QIcon
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from ui.file_list import FileListPanel
from ui.rename_dialog import RenameDialog
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
        
        # 确保窗口状态正常（解决PyInstaller打包后窗口最小化问题）
        self.setWindowState(Qt.WindowState.WindowActive)
    
    def _init_ui(self):
        """
        初始化用户界面
        
        功能描述:
            创建所有UI控件并设置布局
            采用左右分栏布局：左侧功能区（垂直排列），右侧预览区
        """
        self.setWindowTitle("票易合 - 发票合并工具")
        self.setMinimumSize(1400, 800)
        
        # 设置窗口图标
        # 支持开发环境和 PyInstaller 打包后的环境
        if getattr(sys, 'frozen', False):
            # PyInstaller 打包后的环境
            base_path = sys._MEIPASS
        else:
            # 开发环境
            base_path = os.path.dirname(os.path.dirname(__file__))
        
        icon_path = os.path.join(base_path, 'res', 'logo3.ico')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        # 设置图标目录
        self.icon_dir = os.path.join(base_path, 'res', 'icons')
        
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
        
        # 主要内容区域 - 使用水平分割器分为左右两列
        content_splitter = QSplitter(Qt.Orientation.Horizontal)
        content_splitter.setHandleWidth(2)
        
        # 左侧：功能区（垂直排列所有控件）
        left_widget = self._create_left_functional_area()
        content_splitter.addWidget(left_widget)
        
        # 右侧：预览区
        right_widget = self._create_right_preview_area()
        content_splitter.addWidget(right_widget)
        
        # 设置分割器比例（左:右 = 6:4）
        content_splitter.setSizes([840, 560])
        
        main_layout.addWidget(content_splitter, 1)
    
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
                image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMCIgaGVpZ2h0PSIxMCIgdmlld0JveD0iMCAwIDEwIDEwIiBmaWxsPSJ3aGl0ZSI+PGNpcmNsZSBjeD0iNSIgY3k9IjUiIHI9IjMiLz48L3N2Zz4=);
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
                image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMCIgaGVpZ2h0PSIxMCIgdmlld0JveD0iMCAwIDEwIDEwIiBmaWxsPSJub25lIiBzdHJva2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjIiPjxwYXRoIGQ9Ik0yIDVsMiAyIDQtNCIvPjwvc3ZnPg==);
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
            
            /* 反馈按钮特殊样式 - 问号图标样式 */
            QPushButton#feedbackButton {{
                background-color: transparent;
                color: {TEXT_SECONDARY};
                border: 1px solid {BORDER_COLOR};
                border-radius: 15px;
                font-weight: bold;
                font-size: 16px;
                padding: 0px;
            }}
            
            QPushButton#feedbackButton:hover {{
                background-color: {BG_COLOR};
                border-color: {PRIMARY_COLOR};
                color: {PRIMARY_COLOR};
            }}
        """)
    
    def _icon_path(self, filename):
        """
        获取图标文件完整路径

        功能描述:
            根据图标文件名返回完整路径

        参数:
            filename: 图标文件名

        返回值:
            str: 图标文件完整路径
        """
        return os.path.join(self.icon_dir, filename)

    def _icon_pixmap(self, filename, size=16):
        """
        加载SVG图标为QPixmap

        功能描述:
            加载指定SVG图标并缩放到指定尺寸

        参数:
            filename: 图标文件名
            size: 图标尺寸（像素），默认16

        返回值:
            QPixmap: 图标像素图，加载失败则返回空QPixmap
        """
        pixmap = QPixmap(self._icon_path(filename))
        if not pixmap.isNull():
            pixmap = pixmap.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        return pixmap

    def _icon_label(self, filename, size=16):
        """
        创建带SVG图标的QLabel

        功能描述:
            创建QLabel并设置SVG图标

        参数:
            filename: 图标文件名
            size: 图标尺寸（像素），默认16

        返回值:
            QLabel: 带有图标的标签
        """
        label = QLabel()
        pixmap = self._icon_pixmap(filename, size)
        if not pixmap.isNull():
            label.setPixmap(pixmap)
        return label

    def _set_btn_icon(self, button, filename, text, icon_size=16):
        """
        为QPushButton设置SVG图标

        功能描述:
            设置按钮的图标和文本（去掉emoji）

        参数:
            button: QPushButton实例
            filename: 图标文件名
            text: 按钮文本（不含emoji）
            icon_size: 图标尺寸（像素），默认16
        """
        icon = QIcon(self._icon_path(filename))
        button.setIcon(icon)
        button.setIconSize(QSize(icon_size, icon_size))
        button.setText(text)

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
        icon_label = self._icon_label("笔记_notes.svg", 20)
        layout.addWidget(icon_label)
        
        # 主提示文本
        self.drop_label = QLabel("拖入PDF文件到下方列表，右侧预览区域可查看合并效果")
        self.drop_label.setObjectName("titleLabel")
        self.drop_label.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {TEXT_PRIMARY}; background: transparent; border: none;")
        layout.addWidget(self.drop_label)
        layout.addStretch()
        
        # 版本号标签
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
        
        # 反馈按钮
        self.feedback_button = QPushButton("?")
        self.feedback_button.setObjectName("feedbackButton")
        self.feedback_button.setFixedSize(30, 30)
        self.feedback_button.setToolTip("使用帮助")
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
        file_list_icon = self._icon_label("文件夹-开_folder-open.svg", 16)
        file_list_header.addWidget(file_list_icon)
        
        self.file_list_label = QLabel("文件列表")
        self.file_list_label.setObjectName("titleLabel")
        self.file_list_label.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {TEXT_PRIMARY}; background: transparent; border: none;")
        file_list_header.addWidget(self.file_list_label)
        file_list_header.addStretch()
        file_list_layout.addLayout(file_list_header)

        # 文件列表组件
        self.file_list = FileListPanel(self.pdf_handler, on_file_added=self._on_first_file_added)
        self.file_list.selection_changed.connect(self._on_list_selection_changed)
        self.file_list.duplicate_count_changed.connect(self._on_duplicate_count_changed)
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
        preview_icon = self._icon_label("预览-打开_preview-open.svg", 16)
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
        self.refresh_preview_btn = QPushButton("刷新")
        self.refresh_preview_btn.setObjectName("iconButton")
        self.refresh_preview_btn.setToolTip("手动刷新预览")
        self.refresh_preview_btn.clicked.connect(self._update_preview)
        self.refresh_preview_btn.setEnabled(False)
        self._set_btn_icon(self.refresh_preview_btn, "刷新_refresh.svg", "刷新")
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
        placeholder_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder_layout.setSpacing(12)

        self.preview_placeholder_icon = self._icon_label("笔记_notes.svg", 48)
        self.preview_placeholder_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder_layout.addWidget(self.preview_placeholder_icon)

        self.preview_placeholder = QLabel("添加PDF文件后，此处将显示合并后的预览效果\n\n支持实时预览，调整选项后自动更新")
        self.preview_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_placeholder.setStyleSheet(f"""
            color: {TEXT_SECONDARY};
            font-size: 14px;
            background: transparent;
            border: none;
        """)
        placeholder_layout.addWidget(self.preview_placeholder)
        
        self.preview_stack.addWidget(placeholder_container)
        
        # 页面2：图片预览（支持滚轮缩放和多页面）
        self.preview_scroll = QScrollArea()
        self.preview_scroll.setWidgetResizable(True)
        self.preview_scroll.setStyleSheet(f"""
            QScrollArea {{
                background-color: #FAFAFA;
                border: 1px solid {BORDER_COLOR};
                border-radius: 8px;
            }}
        """)
        
        # 创建预览容器（垂直布局，支持多页面）
        self.preview_container = QWidget()
        self.preview_container.setStyleSheet("background-color: transparent;")
        self.preview_layout = QVBoxLayout(self.preview_container)
        self.preview_layout.setSpacing(20)
        self.preview_layout.setContentsMargins(20, 20, 20, 20)
        self.preview_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.preview_scroll.setWidget(self.preview_container)
        
        # 初始化预览相关变量
        self.preview_pixmaps = []  # 存储所有页面的pixmap
        self.preview_scale = 0.8   # 当前缩放比例
        self.preview_labels = []   # 存储所有预览标签
        
        # 启用鼠标滚轮事件
        self.preview_scroll.viewport().installEventFilter(self)
        
        self.preview_stack.addWidget(self.preview_scroll)
        
        preview_layout.addWidget(self.preview_stack)
        
        splitter.addWidget(preview_card)
        
        # 设置分割器比例（左:右 = 5:5，文件列表更宽）
        splitter.setSizes([700, 700])
        
        layout.addWidget(splitter)
        
        return widget
    
    def _create_options_widget(self):
        """
        创建选项设置区域
        
        功能描述:
            创建包含布局选择、模式选择、排序方式等选项的单行水平布局
        
        返回值:
            QWidget: 选项设置区域控件
        """
        # 创建卡片容器
        card = QFrame()
        card.setObjectName("card")
        card.setFrameShape(QFrame.Shape.StyledPanel)
        
        layout = QHBoxLayout(card)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)
        
        # ========== 方向选择区域 ==========
        orientation_container = QHBoxLayout()
        orientation_container.setSpacing(8)
        
        # orientation_icon = self._icon_label("布局2_layout-two.svg", 14)
        # orientation_container.addWidget(orientation_icon)
        
        orientation_title = QLabel("布局:")
        orientation_title.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {TEXT_PRIMARY}; background: transparent; border: none;")
        orientation_container.addWidget(orientation_title)
        
        # 方向按钮组
        self.orientation_button_group = QButtonGroup(self)
        
        self.radio_portrait = QRadioButton("竖向")
        self.radio_portrait.setToolTip("A4纸竖向排列")
        self.radio_portrait.setMinimumWidth(50)
        self.radio_portrait.setStyleSheet(f"""
            QRadioButton {{
                font-size: 11px;
                font-weight: 500;
                spacing: 3px;
            }}
            QRadioButton::indicator {{
                width: 12px;
                height: 12px;
                border-radius: 6px;
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
            QRadioButton:checked {{
                color: {PRIMARY_COLOR};
                font-weight: bold;
            }}
        """)
        self.orientation_button_group.addButton(self.radio_portrait)
        orientation_container.addWidget(self.radio_portrait)
        
        self.radio_landscape = QRadioButton("横向")
        self.radio_landscape.setToolTip("A4纸横向排列")
        self.radio_landscape.setMinimumWidth(50)
        self.radio_landscape.setStyleSheet(f"""
            QRadioButton {{
                font-size: 11px;
                font-weight: 500;
                spacing: 3px;
            }}
            QRadioButton::indicator {{
                width: 12px;
                height: 12px;
                border-radius: 6px;
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
            QRadioButton:checked {{
                color: {PRIMARY_COLOR};
                font-weight: bold;
            }}
        """)
        self.orientation_button_group.addButton(self.radio_landscape)
        orientation_container.addWidget(self.radio_landscape)
        
        # 默认选中竖向
        self.radio_portrait.setChecked(True)
        
        self.radio_portrait.toggled.connect(lambda checked: checked and self._on_config_changed())
        self.radio_landscape.toggled.connect(lambda checked: checked and self._on_config_changed())
        
        layout.addLayout(orientation_container)
        
        # ========== 行列设置区域 ==========
        grid_container = QHBoxLayout()
        grid_container.setSpacing(8)
        
        # 行数输入框
        row_label = QLabel("行")
        row_label.setStyleSheet(f"font-size: 11px; color: {TEXT_SECONDARY};")
        grid_container.addWidget(row_label)
        
        self.row_spinbox = QSpinBox()
        self.row_spinbox.setRange(1, 10)
        self.row_spinbox.setValue(2)
        self.row_spinbox.setFixedWidth(45)
        self.row_spinbox.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self.row_spinbox.setStyleSheet(f"""
            QSpinBox {{
                padding: 4px 8px;
                border-radius: 4px;
                border: 1px solid {BORDER_COLOR};
                background-color: {CARD_BG};
                font-size: 12px;
            }}
            QSpinBox:focus {{
                border-color: {PRIMARY_COLOR};
            }}
        """)
        self.row_spinbox.valueChanged.connect(self._on_config_changed)
        grid_container.addWidget(self.row_spinbox)
        
        # 列数输入框
        col_label = QLabel("列")
        col_label.setStyleSheet(f"font-size: 11px; color: {TEXT_SECONDARY};")
        grid_container.addWidget(col_label)
        
        self.col_spinbox = QSpinBox()
        self.col_spinbox.setRange(1, 10)
        self.col_spinbox.setValue(2)
        self.col_spinbox.setFixedWidth(45)
        self.col_spinbox.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self.col_spinbox.setStyleSheet(f"""
            QSpinBox {{
                padding: 4px 8px;
                border-radius: 4px;
                border: 1px solid {BORDER_COLOR};
                background-color: {CARD_BG};
                font-size: 12px;
            }}
            QSpinBox:focus {{
                border-color: {PRIMARY_COLOR};
            }}
        """)
        self.col_spinbox.valueChanged.connect(self._on_config_changed)
        grid_container.addWidget(self.col_spinbox)
        
        layout.addLayout(grid_container)
        
        # 添加分隔线
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.Shape.VLine)
        separator1.setStyleSheet(f"background-color: {BORDER_COLOR};")
        separator1.setFixedWidth(1)
        layout.addWidget(separator1)
        
        # ========== 处理模式区域 ==========
        mode_container = QHBoxLayout()
        mode_container.setSpacing(8)
        
        # mode_icon = self._icon_label("扫描设置_scan-setting.svg", 14)
        # mode_container.addWidget(mode_icon)
        
        mode_title = QLabel("模式:")
        mode_title.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {TEXT_PRIMARY}; background: transparent; border: none;")
        mode_container.addWidget(mode_title)
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["普通", "图像"])
        self.mode_combo.setToolTip("普通模式保留PDF矢量信息，图像模式转换为图片")
        self.mode_combo.currentIndexChanged.connect(self._on_config_changed)
        self.mode_combo.setFixedWidth(60)
        mode_container.addWidget(self.mode_combo)
        
        layout.addLayout(mode_container)
        
        # 添加分隔线
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.Shape.VLine)
        separator2.setStyleSheet(f"background-color: {BORDER_COLOR};")
        separator2.setFixedWidth(1)
        layout.addWidget(separator2)
        
        # ========== 排序方式区域 ==========
        order_container = QHBoxLayout()
        order_container.setSpacing(8)
        
        # order_icon = self._icon_label("排序2_sort-two.svg", 14)
        # order_container.addWidget(order_icon)
        
        order_title = QLabel("打印顺序:")
        order_title.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {TEXT_PRIMARY}; background: transparent; border: none;")
        order_container.addWidget(order_title)
        
        self.order_combo = QComboBox()
        self.order_combo.addItems(["列表顺序", "开票日期", "开票金额"])
        self.order_combo.setToolTip("选择发票的打印顺序")
        self.order_combo.currentIndexChanged.connect(self._on_config_changed)
        self.order_combo.setFixedWidth(80)
        order_container.addWidget(self.order_combo)
        
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
        
        # ========== 文件操作组（添加、删除、清空）==========
        file_ops_layout = QHBoxLayout()
        file_ops_layout.setSpacing(6)
        
        self.add_file_btn = QPushButton("添加")
        self.add_file_btn.setObjectName("iconButton")
        self.add_file_btn.setToolTip("添加PDF文件到列表")
        self.add_file_btn.clicked.connect(self._on_add_file)
        self._set_btn_icon(self.add_file_btn, "加_plus.svg", "添加")
        file_ops_layout.addWidget(self.add_file_btn)

        self.del_btn = QPushButton("删除")
        self.del_btn.setObjectName("iconButton")
        self.del_btn.setToolTip("删除选中的文件")
        self.del_btn.clicked.connect(self._on_del)
        self._set_btn_icon(self.del_btn, "减_minus.svg", "删除")
        file_ops_layout.addWidget(self.del_btn)

        self.del_all_btn = QPushButton("清空")
        self.del_all_btn.setObjectName("iconButton")
        self.del_all_btn.setToolTip("清空所有文件")
        self.del_all_btn.clicked.connect(self._on_del_all)
        self._set_btn_icon(self.del_all_btn, "关闭_close.svg", "清空")
        file_ops_layout.addWidget(self.del_all_btn)
        
        layout.addLayout(file_ops_layout)
        
        # 添加分隔线（清空与上移之间）
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.Shape.VLine)
        separator1.setStyleSheet(f"background-color: {BORDER_COLOR};")
        separator1.setFixedWidth(1)
        layout.addWidget(separator1)
        
        # ========== 排序操作组（上移、下移）==========
        sort_ops_layout = QHBoxLayout()
        sort_ops_layout.setSpacing(6)
        
        self.move_up_btn = QPushButton("上移")
        self.move_up_btn.setObjectName("iconButton")
        self.move_up_btn.setToolTip("将选中的文件上移一位")
        self.move_up_btn.clicked.connect(self._on_move_up)
        self._set_btn_icon(self.move_up_btn, "箭头上_arrow-up.svg", "上移")
        sort_ops_layout.addWidget(self.move_up_btn)

        self.move_down_btn = QPushButton("下移")
        self.move_down_btn.setObjectName("iconButton")
        self.move_down_btn.setToolTip("将选中的文件下移一位")
        self.move_down_btn.clicked.connect(self._on_move_down)
        self._set_btn_icon(self.move_down_btn, "箭头下_arrow-down.svg", "下移")
        sort_ops_layout.addWidget(self.move_down_btn)
        
        layout.addLayout(sort_ops_layout)
        
        # 添加分隔线（下移与重命名之间）
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.Shape.VLine)
        separator2.setStyleSheet(f"background-color: {BORDER_COLOR};")
        separator2.setFixedWidth(1)
        layout.addWidget(separator2)
        
        # ========== 重命名操作组 ==========
        rename_ops_layout = QHBoxLayout()
        rename_ops_layout.setSpacing(6)
        
        self.rename_btn = QPushButton("重命名")
        self.rename_btn.setObjectName("iconButton")
        self.rename_btn.setToolTip("批量重命名文件")
        self.rename_btn.clicked.connect(self._on_rename)
        self._set_btn_icon(self.rename_btn, "铅笔_pencil.svg", "重命名")
        rename_ops_layout.addWidget(self.rename_btn)
        
        layout.addLayout(rename_ops_layout)
        
        # 添加分隔线（重命名与导出列表之间）
        separator_export = QFrame()
        separator_export.setFrameShape(QFrame.Shape.VLine)
        separator_export.setStyleSheet(f"background-color: {BORDER_COLOR};")
        separator_export.setFixedWidth(1)
        layout.addWidget(separator_export)
        
        # ========== 导出列表操作组 ==========
        export_ops_layout = QHBoxLayout()
        export_ops_layout.setSpacing(6)
        
        self.export_list_btn = QPushButton("导出列表")
        self.export_list_btn.setObjectName("iconButton")
        self.export_list_btn.setToolTip("导出文件列表到Excel")
        self.export_list_btn.clicked.connect(self._on_export_list)
        self._set_btn_icon(self.export_list_btn, "下载_download-four.svg", "导出列表")
        export_ops_layout.addWidget(self.export_list_btn)
        
        layout.addLayout(export_ops_layout)
        
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
        # path_icon = QLabel("💾")
        # path_icon.setStyleSheet("font-size: 14px; background: transparent; border: none;")
        # layout.addWidget(path_icon)
        
        # path_label = QLabel("保存路径:")
        # path_label.setObjectName("titleLabel")
        # path_label.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {TEXT_PRIMARY}; background: transparent; border: none;")
        # layout.addWidget(path_label)
        
        # 保存路径输入框
        # self.path_edit = QLineEdit()
        # self.path_edit.setObjectName("pathInput")
        # self.path_edit.setPlaceholderText("选择合并后的PDF保存位置...")
        # self.path_edit.setMinimumWidth(200)
        # layout.addWidget(self.path_edit, 1)
        
        # 选择路径按钮
        self.select_path_btn = QPushButton("浏览...")
        self.select_path_btn.setObjectName("iconButton")
        self.select_path_btn.setToolTip("选择保存位置")
        self.select_path_btn.clicked.connect(self._on_select_path)
        self._set_btn_icon(self.select_path_btn, "文件夹-开_folder-open.svg", "浏览...")
        layout.addWidget(self.select_path_btn)
        
        return card
    
    def _create_left_functional_area(self):
        """
        创建左侧功能区
        
        功能描述:
            创建左侧功能区容器，垂直排列文件列表、配置项、操作按钮、保存路径和版本号
        
        返回值:
            QWidget: 左侧功能区控件
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        # 1. 文件列表区域（占据主要空间）
        file_list_card = QFrame()
        file_list_card.setObjectName("card")
        file_list_card.setFrameShape(QFrame.Shape.StyledPanel)
        
        file_list_layout = QVBoxLayout(file_list_card)
        file_list_layout.setContentsMargins(12, 12, 12, 12)
        file_list_layout.setSpacing(8)
        
        # 文件列表标题
        file_list_header = QHBoxLayout()
        # file_list_icon = self._icon_label("文件夹-开_folder-open.svg", 14)
        # file_list_header.addWidget(file_list_icon)
        
        self.file_list_label = QLabel("文件列表")
        self.file_list_label.setObjectName("titleLabel")
        self.file_list_label.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {TEXT_PRIMARY}; background: transparent; border: none;")
        file_list_header.addWidget(self.file_list_label)
        file_list_header.addStretch()
        file_list_layout.addLayout(file_list_header)

        # 文件列表组件
        self.file_list = FileListPanel(self.pdf_handler, on_file_added=self._on_first_file_added)
        self.file_list.selection_changed.connect(self._on_list_selection_changed)
        self.file_list.duplicate_count_changed.connect(self._on_duplicate_count_changed)
        self.file_list.setStyleSheet(f"background-color: {CARD_BG}; border: none;")
        file_list_layout.addWidget(self.file_list)
        
        layout.addWidget(file_list_card, 1)  # 占据主要空间
        
        # 2. 操作按钮区域（单行水平布局）
        actions_card = self._create_actions_widget()
        layout.addWidget(actions_card)

        # 3 配置选项区域（单行水平布局）
        options_card = self._create_options_widget()
        layout.addWidget(options_card)
        
        # 4. 保存路径和版本号区域
        bottom_card = QFrame()
        bottom_card.setObjectName("card")
        bottom_card.setFrameShape(QFrame.Shape.StyledPanel)
        
        bottom_layout = QVBoxLayout(bottom_card)
        bottom_layout.setContentsMargins(12, 12, 12, 12)
        bottom_layout.setSpacing(8)
        
        # 保存路径
        # path_header = QHBoxLayout()
        # path_icon = QLabel("💾")
        # path_icon.setStyleSheet("font-size: 12px; background: transparent; border: none;")
        # path_header.addWidget(path_icon)
        # path_label = QLabel("保存路径")
        # path_label.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {TEXT_PRIMARY};")
        # path_header.addWidget(path_label)
        # path_header.addStretch()
        # bottom_layout.addLayout(path_header)

        path_input_layout = QHBoxLayout()
        path_input_layout.setSpacing(6)

        self.path_edit = QLineEdit()
        self.path_edit.setObjectName("pathInput")
        self.path_edit.setPlaceholderText("选择保存位置...")
        path_input_layout.addWidget(self.path_edit, 1)

        self.select_path_btn = QPushButton("浏览")
        self.select_path_btn.setObjectName("iconButton")
        self.select_path_btn.setToolTip("选择保存位置")
        self._set_btn_icon(self.select_path_btn, "文件夹-开_folder-open.svg", "浏览")
        self.select_path_btn.clicked.connect(self._on_select_path)
        path_input_layout.addWidget(self.select_path_btn)
        
        # 添加分隔线（浏览与合并之间）
        separator_merge = QFrame()
        separator_merge.setFrameShape(QFrame.Shape.VLine)
        separator_merge.setStyleSheet(f"background-color: {BORDER_COLOR};")
        separator_merge.setFixedWidth(1)
        path_input_layout.addWidget(separator_merge)
        
        # 合并按钮
        self.merge_btn = QPushButton("合并")
        self.merge_btn.setObjectName("primaryButton")
        self.merge_btn.setToolTip("合并所有文件并保存")
        self.merge_btn.setMinimumWidth(100)
        self.merge_btn.clicked.connect(self._on_merge_all)
        # self._set_btn_icon(self.merge_btn, "合并单元格_merge-cells.svg", "合并")
        path_input_layout.addWidget(self.merge_btn)

                # ========== 一式两份配置 ==========
        self.duplicate_copy_checkbox = QCheckBox("一式两份")
        self.duplicate_copy_checkbox.setToolTip("合并时生成两份相同的文件")
        self.duplicate_copy_checkbox.setStyleSheet(f"font-size: 12px; color: {TEXT_PRIMARY};")
        self.duplicate_copy_checkbox.stateChanged.connect(self._on_duplicate_copy_changed)
        self.duplicate_copy_checkbox.setMinimumWidth(80)
        path_input_layout.addWidget(self.duplicate_copy_checkbox)
        
        # 合并后打印复选框
        self.print_checkbox = QCheckBox("合并后打印")
        self.print_checkbox.setToolTip("合并后打开文件")
        self.print_checkbox.setStyleSheet(f"font-size: 12px; color: {TEXT_PRIMARY};")
        path_input_layout.addWidget(self.print_checkbox)
        
        bottom_layout.addLayout(path_input_layout)
        
        # 版本号（底部）
        # version_layout = QHBoxLayout()
        # version_layout.addStretch()
        
        # self.version_label = QLabel(self._get_version())
        # self.version_label.setObjectName("versionLabel")
        # self.version_label.setStyleSheet(f"""
        #     color: {TEXT_SECONDARY};
        #     font-size: 11px;
        #     padding: 2px 6px;
        #     border-radius: 3px;
        #     background: transparent;
        # """)
        # self.version_label.setToolTip("点击检查更新")
        # self.version_label.setCursor(Qt.CursorShape.PointingHandCursor)
        # self.version_label.mousePressEvent = lambda event: self._on_version_click()
        # version_layout.addWidget(self.version_label)
        
        # bottom_layout.addLayout(version_layout)
        layout.addWidget(bottom_card)
        
        return widget
    
    def _create_right_preview_area(self):
        """
        创建右侧预览区
        
        功能描述:
            创建右侧预览区域，占据整列显示预览内容，包含预览开关
        
        返回值:
            QWidget: 右侧预览区控件
        """
        preview_card = QFrame()
        preview_card.setObjectName("card")
        preview_card.setFrameShape(QFrame.Shape.StyledPanel)
        
        preview_layout = QVBoxLayout(preview_card)
        preview_layout.setContentsMargins(12, 12, 12, 12)
        preview_layout.setSpacing(8)
        
        # 预览区域标题栏
        preview_header = QHBoxLayout()
        preview_icon = self._icon_label("预览-打开_preview-open.svg", 14)
        preview_header.addWidget(preview_icon)
        
        preview_label = QLabel("合并预览")
        preview_label.setObjectName("titleLabel")
        preview_label.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {TEXT_PRIMARY}; background: transparent; border: none;")
        preview_header.addWidget(preview_label)
        
        self.preview_status_label = QLabel("(添加文件后自动更新)")
        self.preview_status_label.setObjectName("subtitleLabel")
        self.preview_status_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px; background: transparent; border: none;")
        preview_header.addWidget(self.preview_status_label)
        preview_header.addStretch()
        
        # 预览开关
        # self.preview_checkbox = QCheckBox("启用预览")
        # self.preview_checkbox.setToolTip("关闭后不再渲染预览，提升性能")
        # self.preview_checkbox.setChecked(True)
        # self.preview_checkbox.stateChanged.connect(self._on_preview_checkbox_changed)
        # self.preview_checkbox.setStyleSheet(f"""
        #     QCheckBox {{
        #         font-size: 12px;
        #         color: {TEXT_PRIMARY};
        #         spacing: 4px;
        #     }}
        #     QCheckBox::indicator {{
        #         width: 14px;
        #         height: 14px;
        #         border-radius: 3px;
        #         border: 2px solid {TEXT_MUTED};
        #         background-color: {CARD_BG};
        #     }}
        #     QCheckBox::indicator:checked {{
        #         border-color: {PRIMARY_COLOR};
        #         background-color: {PRIMARY_COLOR};
        #     }}
        #     QCheckBox::indicator:hover {{
        #         border-color: {PRIMARY_COLOR};
        #     }}
        # """)
        # preview_header.addWidget(self.preview_checkbox)
        
        # 刷新预览按钮
        self.refresh_preview_btn = QPushButton("刷新")
        self.refresh_preview_btn.setObjectName("iconButton")
        self.refresh_preview_btn.setToolTip("手动刷新预览")
        self.refresh_preview_btn.clicked.connect(self._update_preview)
        self.refresh_preview_btn.setEnabled(False)
        self._set_btn_icon(self.refresh_preview_btn, "刷新_refresh.svg", "刷新")
        preview_header.addWidget(self.refresh_preview_btn)
        
        preview_layout.addLayout(preview_header)
        
        # 预览内容区域
        self.preview_stack = QStackedWidget()
        
        # 页面1：提示信息
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
        placeholder_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder_layout.setSpacing(12)

        self.preview_placeholder_icon = self._icon_label("笔记_notes.svg", 48)
        self.preview_placeholder_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder_layout.addWidget(self.preview_placeholder_icon)

        self.preview_placeholder = QLabel("添加PDF文件后，此处将显示合并后的预览效果\n\n支持实时预览，调整选项后自动更新")
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
        
        # 创建预览容器
        self.preview_container = QWidget()
        self.preview_container.setStyleSheet("background-color: transparent;")
        self.preview_layout = QVBoxLayout(self.preview_container)
        self.preview_layout.setSpacing(12)
        self.preview_layout.setContentsMargins(12, 12, 12, 12)
        self.preview_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.preview_scroll.setWidget(self.preview_container)
        
        # 初始化预览相关变量
        self.preview_pixmaps = []
        self.preview_scale = 0.8
        self.preview_labels = []
        
        # 启用鼠标滚轮事件
        self.preview_scroll.viewport().installEventFilter(self)
        
        self.preview_stack.addWidget(self.preview_scroll)
        
        preview_layout.addWidget(self.preview_stack, 1)
        
        return preview_card
    
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
            根据方向选择和行列设置返回布局配置字典
        
        返回值:
            dict: 布局配置字典，包含orientation、rows、cols
        """
        orientation = 'portrait' if self.radio_portrait.isChecked() else 'landscape'
        rows = self.row_spinbox.value()
        cols = self.col_spinbox.value()
        
        return {
            'orientation': orientation,
            'rows': rows,
            'cols': cols,
            'rotate': 0
        }
    
    def _get_layout_display_name(self):
        """
        获取布局的显示名称
        
        功能描述:
            根据当前配置生成布局显示名称
        
        返回值:
            str: 布局显示名称（如"竖向2x2"）
        """
        orientation_text = "竖向" if self.radio_portrait.isChecked() else "横向"
        rows = self.row_spinbox.value()
        cols = self.col_spinbox.value()
        return f"{orientation_text}{rows}x{cols}"
    
    def _get_version(self):
        """
        获取当前版本号
        
        功能描述:
            从version.json文件中读取当前版本号
            支持开发环境和PyInstaller打包后的环境
        
        返回值:
            str: 版本号字符串（如"v0.1.0"）
        """
        try:
            # 尝试多个可能的路径（开发环境和打包环境）
            possible_paths = []
            
            # 1. 标准路径（开发环境）
            possible_paths.append(VERSION_FILE)
            
            # 2. PyInstaller打包后的路径
            if hasattr(sys, '_MEIPASS'):
                # PyInstaller打包后的临时目录
                possible_paths.append(os.path.join(sys._MEIPASS, 'version.json'))
                possible_paths.append(os.path.join(sys._MEIPASS, 'code', 'version.json'))
            
            # 3. 当前工作目录
            possible_paths.append(os.path.join(os.getcwd(), 'version.json'))
            possible_paths.append(os.path.join(os.getcwd(), 'code', 'version.json'))
            
            # 4. 可执行文件所在目录
            if getattr(sys, 'frozen', False):
                exe_dir = os.path.dirname(sys.executable)
                possible_paths.append(os.path.join(exe_dir, 'version.json'))
                possible_paths.append(os.path.join(exe_dir, 'code', 'version.json'))
            
            # 尝试所有可能的路径
            for path in possible_paths:
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        version = data.get('version', '0.1.0')
                        return f"v{version}"
            
            # 如果都找不到，返回默认版本
            return "v0.1.0"
        except Exception as e:
            print(f"读取版本号失败: {e}")
            return "v0.1.0"
    
    def _get_current_sort_by(self):
        """
        获取当前选中的排序方式
        
        功能描述:
            根据排序下拉框的当前选项返回对应的排序字段
        
        返回值:
            str: 排序字段（"list"、"date"、"amount"）
        """
        sort_text = self.order_combo.currentText()
        sort_map = {
            "列表顺序": "list",
            "开票日期": "date",
            "开票金额": "amount"
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
    
    def _on_preview_checkbox_changed(self, state):
        """
        预览开关状态改变时的处理
        
        功能描述:
            当用户切换预览开关时，更新预览状态并保存配置
        
        参数:
            state: 复选框状态
        """
        is_enabled = state == Qt.CheckState.Checked.value
        
        if is_enabled:
            # 开启预览，立即更新
            self._update_preview()
        else:
            # 关闭预览，显示占位符
            self.preview_stack.setCurrentIndex(0)
            self.preview_status_label.setText("(预览已关闭)")
            self.preview_placeholder.setText("预览功能已关闭\n\n如需查看预览，请勾选「启用预览」开关")
        
        # 保存配置
        self._save_config()

    def _on_duplicate_copy_changed(self, state):
        """
        一式两份选项状态改变时的处理
        
        功能描述:
            当用户切换一式两份选项时，保存配置并刷新预览
        
        参数:
            state: 复选框状态
        """
        # 保存配置
        self._save_config()
        
        # 刷新预览
        self._update_preview()
    
    def _update_preview(self):
        """
        更新预览图像
        
        功能描述:
            生成并显示合并后的PDF预览图像，使用临时文件进行预览，不影响正式合并
            仅预览第一页，避免发票过多时预览窗卡死
        """
        # 检查预览开关状态
        if hasattr(self, 'preview_checkbox') and not self.preview_checkbox.isChecked():
            self.preview_stack.setCurrentIndex(0)
            self.preview_status_label.setText("(预览已关闭)")
            return
        
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
            # 先切换到预览页面，确保viewport宽度计算正确
            self.preview_stack.setCurrentIndex(1)
            QGuiApplication.processEvents()

            # 使用viewport宽度计算预览尺寸（viewport是实际可显示区域，不包含滚动条）
            viewport_width = self.preview_scroll.viewport().width()
            scroll_width = self.preview_scroll.width()
            print(f"[调试] viewport_width: {viewport_width}, scroll_width: {scroll_width}")
            # 如果viewport宽度为0或过大（初始化时窗口可能未布局完成），使用一个合理的默认值
            if viewport_width <= 0 or viewport_width > 2000:
                viewport_width = 600  # 使用一个合理的默认宽度
                print(f"[调试] 使用默认宽度: {viewport_width}")

            # 清除旧的预览内容（包括页面容器和标签）
            while self.preview_layout.count() > 0:
                item = self.preview_layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
            
            # 清除旧的预览标签列表
            self.preview_labels.clear()
            
            # 重置缩放比例
            self._reset_preview_zoom()
            
            # 生成第一页的预览图像（使用viewport宽度确保尺寸稳定）
            # 只生成第一页，避免发票过多时预览窗卡死
            pixmaps = self._generate_preview_images(viewport_width, max_pages=1)
            
            if pixmaps:
                self.preview_pixmaps = pixmaps
                
                # 只为第一页创建标签
                for i, pixmap in enumerate(pixmaps):
                    # 创建页面容器
                    page_container = QFrame()
                    page_container.setStyleSheet(f"""
                        QFrame {{
                            background-color: white;
                            border: 1px solid {BORDER_COLOR};
                            border-radius: 4px;
                        }}
                    """)
                    page_layout = QVBoxLayout(page_container)
                    page_layout.setSpacing(4)
                    page_layout.setContentsMargins(8, 8, 8, 8)
                    
                    # 页面编号标签
                    # page_num_label = QLabel(f"第 {i + 1} 页")
                    # page_num_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    # page_num_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px;")
                    # page_layout.addWidget(page_num_label)
                    
                    # 图像标签
                    label = QLabel()
                    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    label.setPixmap(pixmap)
                    label.setStyleSheet("background-color: transparent; border: none;")
                    page_layout.addWidget(label)
                    
                    self.preview_labels.append(label)
                    self.preview_layout.addWidget(page_container)
                
                self.preview_stack.setCurrentIndex(1)
                # 计算总页数
                layout_config = self._get_current_layout()
                items_per_page = layout_config['rows'] * layout_config['cols']
                total_pages = (len(files) + items_per_page - 1) // items_per_page
                self.preview_status_label.setText(f"(仅预览第1页/共{total_pages}页，{len(files)}个文件，Ctrl+滚轮缩放)")
            else:
                self.preview_status_label.setText("(预览生成失败)")
                
        except Exception as e:
            print(f"预览生成失败: {str(e)}")
            import traceback
            traceback.print_exc()
            self.preview_status_label.setText("(预览生成失败)")
        
        self.refresh_preview_btn.setEnabled(True)
    
    def _generate_preview_images(self, viewport_width=None, max_pages=None):
        """
        生成预览图像

        功能描述:
            使用PDFHandler合并PDF文件，应用与实际合并相同的布局设置
            生成高清晰度的预览图像，确保与实际合并效果一致

        参数:
            viewport_width: 可选，指定viewport宽度用于计算预览尺寸，
                           如果不提供则使用 preview_scroll.viewport() 的当前宽度
            max_pages: 可选，限制生成的最大页面数，用于性能优化

        返回值:
            list: 页面的QPixmap列表，如果失败则返回空列表
        """
        files = self.file_list.get_all_files()
        if not files:
            return []
        
        # 创建临时文件用于预览
        temp_fd = None
        temp_path = None
        
        try:
            # 获取当前配置
            layout_config = self._get_current_layout()
            mode = self.mode_combo.currentText()
            sort_by = self._get_current_sort_by()
            
            # 根据排序方式获取文件列表（全部文件）
            if sort_by == 'list':
                files_to_preview = files
            else:
                files_to_preview = self.file_list.get_sorted_files(sort_by)
            
            # 如果勾选了一式两份，将每个文件复制一份
            if hasattr(self, 'duplicate_copy_checkbox') and self.duplicate_copy_checkbox.isChecked():
                files_to_preview = [f for f in files_to_preview for _ in range(2)]
            
            # 创建临时文件
            import tempfile
            temp_fd, temp_path = tempfile.mkstemp(suffix='.pdf')
            os.close(temp_fd)
            
            # 调用PDFHandler合并PDF（使用与实际合并相同的参数）
            mode_str = "图像" if mode == 1 else "普通"
            result = self.pdf_handler.merge_pdfs(
                files_to_preview, 
                temp_path, 
                layout_config, 
                mode_str
            )
            
            pixmaps = []
            
            if result and os.path.exists(temp_path):
                # 使用PyMuPDF将合并后的PDF转换为图像
                import fitz
                doc = fitz.open(temp_path)
                
                if len(doc) > 0:
                    # 预览区域可用大小（按宽度自适应）
                    # 使用传入的viewport宽度计算，减去边距
                    if viewport_width and viewport_width > 0:
                        available_width = viewport_width - 40  # 减去边距
                    else:
                        available_width = self.preview_scroll.viewport().width() - 40

                    if available_width <= 0:
                        available_width = 560
                    
                    # 获取第一页的尺寸
                    first_page = doc[0]
                    page_rect = first_page.rect
                    page_width_pt = page_rect.width
                    page_height_pt = page_rect.height
                    
                    # 计算目标显示尺寸（按宽度自适应）
                    target_width = int(available_width * 0.95)
                    target_height = int(target_width * page_height_pt / page_width_pt)
                    print(f"[调试] available_width: {available_width}, target_width: {target_width}")

                    # 限制最大高度
                    max_height = 800
                    if target_height > max_height:
                        target_height = max_height
                        target_width = int(target_height * page_width_pt / page_height_pt)
                    
                    # 使用高DPI生成预览
                    dpi_scale = 2.0
                    render_width = int(target_width * dpi_scale)
                    render_height = int(target_height * dpi_scale)
                    
                    scale_x = render_width / page_width_pt
                    scale_y = render_height / page_height_pt
                    scale = min(scale_x, scale_y)
                    
                    # 确定要生成的页面数
                    pages_to_render = len(doc)
                    if max_pages is not None and max_pages > 0:
                        pages_to_render = min(pages_to_render, max_pages)
                    
                    # 生成预览图像
                    for page_num in range(pages_to_render):
                        page = doc[page_num]
                        
                        mat = fitz.Matrix(scale, scale)
                        pix = page.get_pixmap(matrix=mat)
                        
                        img_data = pix.tobytes("png")
                        pixmap = QPixmap()
                        pixmap.loadFromData(img_data)
                        
                        pixmap = pixmap.scaled(
                            target_width,
                            target_height,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation
                        )
                        print(f"[调试] 生成pixmap尺寸: {pixmap.width()}x{pixmap.height()}")

                        pixmaps.append(pixmap)
                    
                    doc.close()
            
            # 清理临时文件
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except:
                    pass
            
            return pixmaps
            
        except Exception as e:
            print(f"生成预览图像失败: {str(e)}")
            import traceback
            traceback.print_exc()
            # 清理临时文件
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except:
                    pass
            return []
    
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
        self.file_list.clear()
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
        layout_config = self._get_current_layout()
        mode = self.mode_combo.currentText()
        
        try:
            # 显示进度
            self.merge_btn.setEnabled(False)
            self.merge_btn.setText("合并中...")
            QGuiApplication.processEvents()
            
            # 获取排序方式
            sort_by = self._get_current_sort_by()
            
            # 根据排序方式获取文件列表
            if sort_by == 'list':
                sorted_files = files
            else:
                sorted_files = self.file_list.get_sorted_files(sort_by)
            
            # 如果勾选了一式两份，将每个文件复制一份
            if hasattr(self, 'duplicate_copy_checkbox') and self.duplicate_copy_checkbox.isChecked():
                sorted_files = [f for f in sorted_files for _ in range(2)]
            
            # 执行合并
            result = self.pdf_handler.merge_pdfs(
                sorted_files,
                output_path,
                layout=layout_config,
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
            self.merge_btn.setText("合并")
            # self._set_btn_icon(self.merge_btn, "合并选择_union-selection.svg", "合并")
    
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
        files = self.file_list.get_all_files()
        if not files:
            QMessageBox.warning(self, "警告", "请先添加PDF文件")
            return
        
        try:
            # 创建临时合并文件用于打印
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                tmp_path = tmp.name
            
            layout_config = self._get_current_layout()
            sort_by = self._get_current_sort_by()
            
            # 根据排序方式获取文件列表
            if sort_by == 'list':
                sorted_files = files
            else:
                sorted_files = self.file_list.get_sorted_files(sort_by)
            
            # 如果勾选了一式两份，将每个文件复制一份
            if hasattr(self, 'duplicate_copy_checkbox') and self.duplicate_copy_checkbox.isChecked():
                sorted_files = [f for f in sorted_files for _ in range(2)]
            
            self.pdf_handler.merge_pdfs(
                sorted_files,
                tmp_path,
                layout=layout_config,
                mode="普通"
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
    
    def _on_rename(self):
        """
        批量重命名按钮点击处理
        
        功能描述:
            打开重命名对话框，配置重命名规则并执行批量重命名
        """
        files = self.file_list.get_all_files()
        if not files:
            QMessageBox.warning(self, "警告", "请先添加PDF文件")
            return
        
        # 打开重命名对话框
        dialog = RenameDialog(self, config_file=CONFIG_FILE)
        dialog.rename_executed.connect(self._perform_batch_rename)
        dialog.exec()

    def _on_export_list(self):
        """
        导出列表按钮点击处理

        功能描述:
            调用文件列表的导出方法，将文件列表导出到Excel
        """
        files = self.file_list.get_all_files()
        if not files:
            QMessageBox.warning(self, "警告", "请先添加PDF文件")
            return

        # 调用file_list的_export_file方法，传入-1表示导出整个列表
        self.file_list._export_file()

    def _perform_batch_rename(self, rule):
        """
        执行批量重命名

        功能描述:
            根据规则对文件列表中的文件进行批量重命名

        参数:
            rule: 重命名规则字符串
        """
        if not rule:
            return

        files = self.file_list.get_all_files()
        if not files:
            return

        try:
            renamed_count = 0
            failed_count = 0
            unrecognized_files = []  # 记录无法识别的文件
            name_conflicts = {}

            for file_path in files:
                try:
                    # 提取文件信息
                    file_info = self.pdf_handler.extract_all_invoice_info(file_path)

                    # 如果无法识别该文件（可能是图片），记录并跳过
                    if file_info is None:
                        unrecognized_files.append(os.path.basename(file_path))
                        continue

                    # 应用规则生成新文件名
                    new_name = RenameDialog.apply_rule(rule, file_info)

                    if not new_name:
                        failed_count += 1
                        continue

                    # 获取原文件扩展名
                    _, ext = os.path.splitext(file_path)
                    new_name_with_ext = new_name + ext

                    # 处理文件名冲突
                    dir_path = os.path.dirname(file_path)
                    final_name = new_name_with_ext
                    counter = 1

                    while os.path.exists(os.path.join(dir_path, final_name)):
                        if final_name == os.path.basename(file_path):
                            # 如果生成的名字和原文件名相同，跳过
                            break
                        base_name = f"{new_name}({counter})"
                        final_name = base_name + ext
                        counter += 1

                    # 如果最终名字和原文件名不同，执行重命名
                    if final_name != os.path.basename(file_path):
                        new_path = os.path.join(dir_path, final_name)
                        os.rename(file_path, new_path)
                        renamed_count += 1

                        # 更新文件列表中的路径
                        self.file_list.update_file_path(file_path, new_path)

                except Exception as e:
                    print(f"重命名文件失败 {file_path}: {e}")
                    failed_count += 1

            # 刷新文件列表显示
            self.file_list.refresh_display()
            self._update_preview()

            # 构建提示消息
            messages = []
            if renamed_count > 0:
                messages.append(f"成功重命名 {renamed_count} 个文件")
            if failed_count > 0:
                messages.append(f"失败: {failed_count} 个")
            if len(unrecognized_files) > 0:
                messages.append(f"未能识别: {len(unrecognized_files)} 个文件（可能是图片格式，无法提取文本）")

            # 显示结果
            if messages:
                QMessageBox.information(
                    self,
                    "重命名完成",
                    "\n".join(messages)
                )
            else:
                QMessageBox.information(
                    self,
                    "重命名完成",
                    "没有文件需要重命名\n（可能是生成的文件名与原文件名相同）"
                )

        except Exception as e:
            QMessageBox.critical(self, "错误", f"批量重命名失败: {str(e)}")
    
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

    def _on_duplicate_count_changed(self, count):
        """
        重复发票数量变化时的处理

        功能描述:
            当检测到重复发票数量变化时，更新文件列表标签显示

        参数:
            count: 重复发票号码的数量
        """
        # 获取文件数量和总金额
        file_count = self.file_list.table.rowCount()
        total_amount = 0.0
        for row in range(file_count):
            amount_item = self.file_list.table.item(row, 3)
            if amount_item:
                amount = amount_item.data(Qt.ItemDataRole.UserRole)
                if amount and isinstance(amount, (int, float)):
                    total_amount += amount

        if count > 0:
            self.file_list_label.setText(f"文件列表  文件数量:{file_count}  总金额:{total_amount:.2f}  重复发票数量:{count}")
            # 设置警告颜色（橙色）
            self.file_list_label.setStyleSheet(
                f"font-size: 14px; font-weight: bold; color: #FF9800; background: transparent; border: none;"
            )
        else:
            self.file_list_label.setText(f"文件列表  文件数量:{file_count}  总金额:{total_amount:.2f}")
            # 恢复默认颜色
            self.file_list_label.setStyleSheet(
                f"font-size: 14px; font-weight: bold; color: {TEXT_PRIMARY}; background: transparent; border: none;"
            )

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
        has_selection = self.file_list.get_selected_file() is not None
        
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

                # 加载布局设置 - 新版配置
                layout_config = config.get('layout_config')
                if layout_config:
                    # 新版配置格式
                    orientation = layout_config.get('orientation', 'portrait')
                    if orientation == 'portrait':
                        self.radio_portrait.setChecked(True)
                    else:
                        self.radio_landscape.setChecked(True)
                    
                    rows = layout_config.get('rows', 2)
                    cols = layout_config.get('cols', 2)
                    self.row_spinbox.setValue(rows)
                    self.col_spinbox.setValue(cols)
                else:
                    # 兼容旧版配置
                    layout = config.get('layout', '横向2x2')
                    if layout == '竖向1x2':
                        self.radio_portrait.setChecked(True)
                        self.row_spinbox.setValue(2)
                        self.col_spinbox.setValue(1)
                    elif layout == '竖向1x3':
                        self.radio_portrait.setChecked(True)
                        self.row_spinbox.setValue(3)
                        self.col_spinbox.setValue(1)
                    elif layout == '竖向2x4':
                        self.radio_portrait.setChecked(True)
                        self.row_spinbox.setValue(4)
                        self.col_spinbox.setValue(2)
                    elif layout == '横向2x2':
                        self.radio_landscape.setChecked(True)
                        self.row_spinbox.setValue(2)
                        self.col_spinbox.setValue(2)
                    elif layout == '横向2x4':
                        self.radio_landscape.setChecked(True)
                        self.row_spinbox.setValue(2)
                        self.col_spinbox.setValue(4)
                    else:
                        # 默认配置
                        self.radio_portrait.setChecked(True)
                        self.row_spinbox.setValue(2)
                        self.col_spinbox.setValue(2)

                # 加载模式设置
                mode = config.get('mode', '普通')
                mode_index = self.mode_combo.findText(mode)
                if mode_index >= 0:
                    self.mode_combo.setCurrentIndex(mode_index)

                # 加载排序设置 - 支持字符串值和旧版的索引值
                sort_by = config.get('sort_by', 'list')
                # 兼容旧版配置（使用索引）
                if isinstance(sort_by, int):
                    if 0 <= sort_by < self.order_combo.count():
                        self.order_combo.setCurrentIndex(sort_by)
                else:
                    # 新版使用字符串值
                    sort_map_reverse = {
                        'list': '列表顺序',
                        'date': '开票日期',
                        'amount': '开票金额'
                    }
                    sort_text = sort_map_reverse.get(sort_by, '列表顺序')
                    sort_index = self.order_combo.findText(sort_text)
                    if sort_index >= 0:
                        self.order_combo.setCurrentIndex(sort_index)

                # 加载合并后打印设置
                print_checkbox = config.get('print_checkbox', False)
                self.print_checkbox.setChecked(print_checkbox)

                # 加载一式两份设置
                duplicate_copy = config.get('duplicate_copy', False)
                if hasattr(self, 'duplicate_copy_checkbox'):
                    self.duplicate_copy_checkbox.setChecked(duplicate_copy)

                # 加载输出路径
                output_path = config.get('output_path', '')
                if output_path:
                    self.path_edit.setText(output_path)
                
                # 加载预览开关设置
                preview_enabled = config.get('preview_enabled', True)
                if hasattr(self, 'preview_checkbox'):
                    self.preview_checkbox.setChecked(preview_enabled)

                # 版本号从 version.json 读取，不在 config.json 中存储
                # 避免覆盖 _get_version() 获取的正确版本号
                pass

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

            # 更新配置 - 新版布局配置
            layout_config = self._get_current_layout()
            config['layout_config'] = layout_config
            # 保留旧版配置以兼容旧版本
            config['layout'] = self._get_layout_display_name()
            config['mode'] = self.mode_combo.currentText()
            config['sort_by'] = self._get_current_sort_by()
            config['print_checkbox'] = self.print_checkbox.isChecked()
            config['duplicate_copy'] = self.duplicate_copy_checkbox.isChecked()
            config['output_path'] = self.path_edit.text().strip()
            
            # 保存预览开关设置
            if hasattr(self, 'preview_checkbox'):
                config['preview_enabled'] = self.preview_checkbox.isChecked()

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
    
    def eventFilter(self, obj, event):
        """
        事件过滤器，处理鼠标滚轮缩放
        
        参数:
            obj: 事件对象
            event: 事件
            
        返回值:
            bool: 是否已处理事件
        """
        if obj == self.preview_scroll.viewport() and event.type() == event.Type.Wheel:
            # 检查是否按下了Ctrl键
            if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                # Ctrl+滚轮进行缩放
                delta = event.angleDelta().y()
                if delta > 0:
                    self._zoom_preview(1.1)  # 放大10%
                else:
                    self._zoom_preview(0.9)  # 缩小10%
                return True
        return super().eventFilter(obj, event)
    
    def _zoom_preview(self, factor):
        """
        缩放预览图像
        
        参数:
            factor: 缩放因子（大于1放大，小于1缩小）
        """
        if not self.preview_pixmaps:
            return
        
        print("缩放因子:" , factor)
        
        # 计算新的缩放比例
        new_scale = self.preview_scale * factor
        
        print("新的缩放比例:" , new_scale)
        
        # 限制缩放范围（0.1到5倍）
        if new_scale < 0.1:
            new_scale = 0.1
        elif new_scale > 5.0:
            new_scale = 5.0
        
        self.preview_scale = new_scale
        
        # 更新所有预览标签的图像
        for i, label in enumerate(self.preview_labels):
            if i < len(self.preview_pixmaps):
                pixmap = self.preview_pixmaps[i]
                scaled_pixmap = pixmap.scaled(
                    int(pixmap.width() * self.preview_scale),
                    int(pixmap.height() * self.preview_scale),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                label.setPixmap(scaled_pixmap)
        
        # 更新状态标签显示缩放比例
        zoom_percent = int(self.preview_scale * 100)
        files = self.file_list.get_all_files()
        self.preview_status_label.setText(f"(预览全部页面，共{len(files)}个文件，缩放{zoom_percent}%)")
    
    def _reset_preview_zoom(self):
        """
        重置预览缩放比例
        """
        print("重置预览缩放比例:" , self.preview_scale)

        self.preview_scale = 0.8
    
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
    使用帮助对话框类
    
    功能描述:
        显示应用程序的使用帮助信息
    
    参数:
        parent (QWidget): 父窗口
    """
    
    def __init__(self, parent=None):
        """
        初始化使用帮助对话框
        
        参数:
            parent (QWidget): 父窗口
        """
        super().__init__(parent)
        
        self.setWindowTitle("使用帮助")
        self.setMinimumSize(500, 450)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题
        title = QLabel("📖 使用帮助")
        title.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
            color: #212121;
        """)
        layout.addWidget(title)
        
        # 帮助内容区域
        help_text = QTextEdit()
        help_text.setReadOnly(True)
        help_text.setStyleSheet("""
            QTextEdit {
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                background-color: #FFFFFF;
                padding: 12px;
                font-size: 13px;
                line-height: 1.6;
            }
        """)
        
        help_content = """<h3>快速开始</h3>
<ol>
<li><b>添加文件</b>：点击"添加"按钮或直接将PDF文件拖入列表</li>
<li><b>选择布局</b>：选择合并布局（竖向1x2、竖向1x3、横向2x2等）</li>
<li><b>调整顺序</b>：使用"上移"/"下移"按钮</li>
<li><b>合并保存</b>：选择保存路径，点击"合并"按钮</li>
</ol>

<h3>功能说明</h3>
<ul>
<li><b>布局选择</b>：
  <ul>
    <li>方向：选择A4纸的排列方向（竖向/横向）</li>
    <li>行列：设置每页排列的发票数量（行数 x 列数）</li>
    <li>常用组合：竖向2x2=4张/页，横向2x2=4张/页，竖向2x4=8张/页</li>
  </ul>
</li>
<li><b>处理模式</b>：
  <ul>
    <li>普通模式：保留PDF矢量信息，文件较小</li>
    <li>图像模式：转换为图片，兼容性更好</li>
  </ul>
</li>
<li><b>排序方式</b>：支持按列表顺序、开票日期、开票金额排序</li>
<li><b>一式两份</b>：勾选后每张发票会合并两份到输出文件中</li>
<li><b>合并后打印</b>：勾选后合并完成自动打开文件</li>
</ul>

<h3>使用技巧</h3>
<ul>
<li>双击列表中的文件可直接打开查看</li>
<li>支持批量拖拽添加多个文件</li>
<li>合并前可在右侧预览效果</li>
<li>使用"重命名"功能可批量修改文件名</li>
<li>勾选"一式两份"可快速生成双份发票</li>
</ul>

<h3>常见问题</h3>
<ul>
<li><b>Q: 支持哪些文件格式？</b><br>A: 目前仅支持PDF格式文件</li>
<li><b>Q: 合并后的文件在哪里？</b><br>A: 默认保存在第一个PDF文件的目录下，可手动选择保存位置</li>
<li><b>Q: 如何调整文件顺序？</b><br>A: 选中文件后点击"上移"/"下移"按钮</li>
<li><b>Q: 一式两份是什么意思？</b><br>A: 勾选后每张发票会在合并后的PDF中出现两次，方便打印双份</li>
</ul>"""
        
        help_text.setHtml(help_content)
        layout.addWidget(help_text)
        
        # 添加分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: #E0E0E0;")
        separator.setFixedHeight(1)
        layout.addWidget(separator)
        
        # 二维码区域
        qrcode_layout = QHBoxLayout()
        qrcode_layout.setSpacing(16)
        qrcode_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 二维码图片
        qrcode_label = QLabel()
        # 计算二维码路径：从ui目录的上级目录(code)进入res目录
        qrcode_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'res', 'qrcode.jpg')
        print(f"二维码路径: {qrcode_path}")  # 调试输出
        if os.path.exists(qrcode_path):
            qrcode_pixmap = QPixmap(qrcode_path)
            if not qrcode_pixmap.isNull():
                # 缩放二维码到合适大小（120x120）
                qrcode_pixmap = qrcode_pixmap.scaled(120, 120, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                qrcode_label.setPixmap(qrcode_pixmap)
            else:
                qrcode_label.setText("图片加载失败")
                qrcode_label.setStyleSheet("color: #757575; font-size: 12px; border: 1px solid #E0E0E0; border-radius: 4px;")
        else:
            qrcode_label.setText("二维码")
            qrcode_label.setStyleSheet("color: #757575; font-size: 12px; border: 1px solid #E0E0E0; border-radius: 4px;")
        qrcode_label.setFixedSize(120, 120)
        qrcode_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        qrcode_layout.addWidget(qrcode_label)
        
        # 提示文字
        qrcode_text = QLabel("有其他问题可以扫码反馈")
        qrcode_text.setStyleSheet("color: #757575; font-size: 13px;")
        qrcode_layout.addWidget(qrcode_text)
        
        layout.addLayout(qrcode_layout)
        
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
