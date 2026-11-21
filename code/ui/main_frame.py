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
from ui.merge_worker import MergeWorker
from ui.file_load_worker import FileLoadWorker
from core.pdf_handler import PDFHandler, is_supported_file
from core.invoice_service import InvoiceService, migrate_rename_rules
from core.update_checker import UpdateChecker, show_update_dialog
from ui.theme import AppTheme
from ui.tokens import build_stylesheet, clear_inline_styles, apply_numeric_text_fonts
from ui.shell import (
    build_shell, update_status_bar, update_duplicate_chip, show_feedback,
    create_ledger_column, create_preview_card,
    create_layout_card, create_mode_order_card,
)


CONFIG_FILE = os.path.join(os.path.dirname(__file__), '../config.json')
VERSION_FILE = os.path.join(os.path.dirname(__file__), '../version.json')

# ============================================================================
# 配色方案 - 兼容旧代码的样式常量
# ============================================================================
# v2 UI：唯一色值来源是 ui/tokens.py；这里仅保留旧变量名，避免逐处改写
# 历史 f-string QSS。新增样式一律通过全局 QSS 的 objectName 选择器实现。
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
SCROLL_AREA_BG = _T["surface_sunken"]
SHADOW_COLOR = "rgba(0, 0, 0, 0.08)"


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
        self.invoice_service = InvoiceService(self.pdf_handler)
        self.remote_version = None
        self.preview_pixmap = None
        self.preview_timer = None  # 用于延迟更新预览的定时器
        self.worker = None  # 后台合并工作线程
        self.file_load_worker = None  # 后台文件加载工作线程

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
        初始化用户界面（v2 五段式结构）

        功能描述:
            结构、状态组件与样式统一委托给 ui.shell / ui.tokens；
            所有控件变量名、信号槽与业务 handler 保持不变。
        """
        self.setWindowTitle("票易合 - 发票合并工具")
        self.setMinimumSize(1400, 800)

        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.dirname(__file__))

        icon_path = os.path.join(base_path, 'res', 'logo3.ico')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        self.icon_dir = os.path.join(base_path, 'res', 'icons')

        self._setup_stylesheet()
        build_shell(self)
        # 台账面板在 build_shell 里才创建，创建后必须再同步一次主题，
        # 否则首帧会残留 FileListPanel 自行探测到的系统主题色。
        self._sync_list_theme()

    def _sync_list_theme(self):
        """
        同步台账面板的主题

        功能描述:
            ``FileListPanel`` 自行持有 ``AppTheme`` 用于表头与财务列的动态着色；
            主窗口切换深浅模式时必须同步重建，否则表头/金额色会残留上一个主题，
            深色模式下表现为表头几乎不可读、重复行底色仍是浅色。
        """
        file_list = getattr(self, "file_list", None)
        if file_list is None:
            return
        try:
            file_list.apply_theme(_theme.dark)
        except Exception:
            pass

    def _setup_stylesheet(self):
        """
        设置全局样式表

        功能描述:
            v2 UI 的全部样式由 ui.tokens.build_stylesheet() 依据当前系统主题生成；
            历史逐控件 setStyleSheet 在 build_shell() 末尾统一清除。
        """
        self.setStyleSheet(build_stylesheet(_theme.dark))
        # 台账面板自行持有 AppTheme（表头/金额列动态着色），需与全局主题同步，
        # 否则深色模式下会残留浅色表头而几乎不可读。
        self._sync_list_theme()
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
        preview_header.addWidget(preview_label)
        
        self.preview_status_label = QLabel("(添加文件后自动更新)")
        self.preview_status_label.setObjectName("subtitleLabel")
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
                    stop:0 {_theme.placeholder_start},
                    stop:0.5 {_theme.placeholder_mid},
                    stop:1 {_theme.placeholder_end});
                border: 2px dashed {_theme.placeholder_border};
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
        self.preview_placeholder.setObjectName("subtitleLabel")
        placeholder_layout.addWidget(self.preview_placeholder)
        
        self.preview_stack.addWidget(placeholder_container)
        
        # 页面2：图片预览（支持滚轮缩放和多页面）
        self.preview_scroll = QScrollArea()
        self.preview_scroll.setWidgetResizable(True)
        self.preview_scroll.setStyleSheet(f"""
            QScrollArea {{
                background-color: {SCROLL_AREA_BG};
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
    
    def _create_layout_widget(self):
        """兼容旧调用：返回 v2 紧凑「纸张与布局」参数卡片。"""
        return create_layout_card(self)
    def _create_mode_order_widget(self):
        """兼容旧调用：返回 v2「处理模式与打印顺序」参数卡片。"""
        return create_mode_order_card(self)
    def _create_actions_widget(self):
        """
        创建操作按钮区域

        功能描述:
            创建票据台账下方的操作条（设计稿 01 基线）：七个入口均为纯文字按钮，
            高度 30，按「文件操作｜排序｜重命名｜导出列表」分组，组间用 1px 竖线
            分隔，最右显示「支持 PDF / 图片 / OFD 混合合并」提示。
            按钮变量名、信号连接与业务 handler 全部保持与改造前一致。

        返回值:
            QWidget: 操作按钮区域控件
        """
        card = QFrame()
        card.setObjectName("actionsCard")
        card.setFrameShape(QFrame.Shape.StyledPanel)

        layout = QHBoxLayout(card)
        # 设计稿：操作条内容左右各内缩 10px（首按钮左缘距卡片 10px），按钮间距 10px
        layout.setContentsMargins(10, 9, 10, 9)
        layout.setSpacing(10)

        def _action(text, tooltip, object_name, slot):
            button = QPushButton(text)
            button.setObjectName(object_name)
            button.setToolTip(tooltip)
            # 设计稿：操作条按钮统一 30px 高（QSS 的 min/max-height 会被 sizeHint 撑开）
            button.setFixedHeight(30)
            button.clicked.connect(slot)
            layout.addWidget(button)
            return button

        def _separator():
            line = QFrame()
            line.setObjectName("vSeparator")
            line.setFixedWidth(1)
            line.setFixedHeight(16)
            line.setFrameShape(QFrame.Shape.NoFrame)
            layout.addWidget(line)

        # ========== 文件操作组（添加、删除、清空）==========
        self.add_file_btn = _action(
            "添加文件", "添加 PDF / 图片 / OFD 发票到台账", "actionAccent", self._on_add_file
        )
        self.del_btn = _action(
            "删除选中", "删除选中的文件", "dangerButton", self._on_del
        )
        self.del_all_btn = _action(
            "清空全部", "清空所有文件", "dangerButton", self._on_del_all
        )
        # 设计稿：危险色只用于「清空全部」，「删除选中」保持白底灰边
        self.del_all_btn.setProperty("tone", "danger")

        _separator()

        # ========== 排序操作组（上移、下移）==========
        self.move_up_btn = _action(
            "上移", "将选中的文件上移一位", "actionButton", self._on_move_up
        )
        self.move_down_btn = _action(
            "下移", "将选中的文件下移一位", "actionButton", self._on_move_down
        )

        _separator()

        # ========== 重命名与导出操作组（设计稿这两项之间无分隔线）==========
        self.rename_btn = _action(
            "批量重命名", "按票种规则批量重命名文件", "actionButton", self._on_rename
        )

        self.export_list_btn = _action(
            "导出列表", "导出文件列表到 Excel", "actionButton", self._on_export_list
        )

        layout.addStretch(1)
        actions_hint = QLabel("支持 PDF / 图片 / OFD 混合合并")
        actions_hint.setObjectName("mutedLabel")
        layout.addWidget(actions_hint)

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
        # layout.addWidget(path_icon)
        
        # path_label = QLabel("保存路径:")
        # path_label.setObjectName("titleLabel")
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
        """兼容旧调用：返回票据台账列（参数卡片已移至右侧设置面板）。"""
        return create_ledger_column(self)
    def _create_right_preview_area(self):
        """兼容旧调用：返回合并预览卡片（含空态、页码与缩放状态）。"""
        return create_preview_card(self)
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
            根据方向选择、行列设置和页边距设置返回布局配置字典
        
        返回值:
            dict: 布局配置字典，包含orientation、rows、cols、rotate、margins
        """
        orientation = 'portrait' if self.radio_portrait.isChecked() else 'landscape'
        rows = self.row_spinbox.value()
        cols = self.col_spinbox.value()
        margins = self._get_margin_config()
        
        return {
            'orientation': orientation,
            'rows': rows,
            'cols': cols,
            'rotate': 0,
            'margins': margins,
            'show_crop_marks': self.crop_mark_checkbox.isChecked(),
            'crop_mark_left': self.crop_mark_left_spinbox.value(),
            'crop_mark_right': self.crop_mark_right_spinbox.value()
        }
    
    def _get_margin_config(self):
        """
        获取当前页边距配置
        
        功能描述:
            从四个页边距输入框读取当前设置，返回毫米为单位的边距配置
        
        返回值:
            dict: 页边距配置字典，包含top、bottom、left、right（单位：mm）
        """
        return {
            'top': self.margin_top_spinbox.value(),
            'bottom': self.margin_bottom_spinbox.value(),
            'left': self.margin_left_spinbox.value(),
            'right': self.margin_right_spinbox.value()
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

        # v2：同步状态栏、台账统计与预览摘要（构建阶段控件尚未齐备时跳过）
        if hasattr(self, 'status_left_label'):
            self._update_status_bar()
    
    def _on_margin_changed(self):
        """
        页边距数值改变时的处理

        功能描述:
            当用户手动修改上/下/左/右边距时，触发预览更新和配置保存
        """
        # 触发预览更新和配置保存
        self._on_config_changed()

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
                            background-color: {CARD_BG};
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
                # 计算总页数（考虑一式两份）
                layout_config = self._get_current_layout()
                items_per_page = layout_config['rows'] * layout_config['cols']
                file_count = len(files)
                if hasattr(self, 'duplicate_copy_checkbox') and self.duplicate_copy_checkbox.isChecked():
                    total_pages = (file_count * 2 + items_per_page - 1) // items_per_page
                else:
                    total_pages = (file_count + items_per_page - 1) // items_per_page
                self.preview_status_label.setText(f"(仅预览第1页/共{total_pages}页，{file_count}个文件，Ctrl+滚轮缩放)")
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
            
            # 预览只需生成第一页，限制参与合并的文件数量以提升性能
            # 第一页最多只需要 rows * cols 个源页面
            pages_per_sheet = layout_config['rows'] * layout_config['cols']
            files_to_preview = files_to_preview[:pages_per_sheet]
            
            # 创建临时文件
            import tempfile
            temp_fd, temp_path = tempfile.mkstemp(suffix='.pdf')
            os.close(temp_fd)
            
            # 调用PDFHandler合并PDF（使用与实际合并相同的参数）
            mode_str = "图像" if mode == 1 else "普通"
            batch_size = pages_per_sheet * 10
            result = self.pdf_handler.merge_pdfs(
                files_to_preview,
                temp_path,
                layout_config,
                mode_str,
                batch_size=batch_size
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
            "选择PDF、图片或OFD文件",
            "",
            "PDF文件 (*.pdf);;图片文件 (*.png *.jpg *.jpeg);;OFD文件 (*.ofd);;所有支持文件 (*.pdf *.png *.jpg *.jpeg *.ofd)"
        )
        
        if files:
            self._start_file_load_worker(files)

    def _start_file_load_worker(self, files):
        """
        启动后台线程批量加载文件

        参数:
            files: 需要加载的 PDF 文件路径列表
        """
        # 防止重复启动加载任务
        if self.file_load_worker is not None and self.file_load_worker.isRunning():
            return

        # 合并进行中时不允许加载文件，避免进度条状态冲突
        if self.worker is not None and self.worker.isRunning():
            QMessageBox.warning(self, "警告", "合并任务正在进行中，请稍候再加载文件")
            return

        self.merge_btn.setEnabled(False)
        self._show_progress("文件加载中")

        self.file_load_worker = FileLoadWorker(
            pdf_handler=self.pdf_handler,
            file_paths=files,
            file_list_panel=self.file_list
        )
        self.file_load_worker.progress.connect(self._on_file_load_progress)
        self.file_load_worker.file_loaded.connect(self._on_file_loaded)
        self.file_load_worker.finished.connect(self._on_file_load_finished)
        self.file_load_worker.error.connect(self._on_file_load_error)
        self.file_load_worker.start()

    def _on_file_load_progress(self, current, total):
        """
        更新文件加载进度条

        参数:
            current: 当前已加载的文件数
            total: 总文件数
        """
        if total > 0:
            self.progress_bar.setValue(int(current * 100 / total))

    def _on_file_loaded(self, file_info):
        """
        单个文件加载完成后的回调

        参数:
            file_info: 文件信息字典
        """
        self.file_list.add_file_info(file_info)

    def _on_file_load_finished(self, success, message):
        """
        文件加载完成后的回调

        参数:
            success: 是否成功
            message: 提示信息
        """
        self._hide_progress()
        self._update_stats()
        self._update_button_states()
        self._show_feedback(
            f"导入完成　·　当前 {len(self.file_list.get_all_files())} 张票据", "success"
        )
        self.file_load_worker = None

    def _on_file_load_error(self, error_message):
        """
        文件加载过程中发生错误的回调

        参数:
            error_message: 错误信息
        """
        self._hide_progress()
        self._show_feedback(f"导入失败　·　{error_message}", "danger")
        QMessageBox.critical(self, "错误", f"文件加载失败: {error_message}")
        self.file_load_worker = None

    def _show_progress(self, text):
        """
        显示底部进度条并设置提示文字

        参数:
            text: 进度条上显示的文字前缀
        """
        self.progress_bar.setFormat(f"{text} %p%")
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self._show_feedback(f"{text}　·　任务在后台执行", "info")

    def _hide_progress(self):
        """隐藏底部进度条"""
        self.progress_bar.setVisible(False)

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
        
        # 防止重复启动合并任务
        if self.worker is not None and self.worker.isRunning():
            QMessageBox.warning(self, "警告", "合并任务正在进行中，请稍候")
            return

        # 文件加载进行中时不允许合并
        if self.file_load_worker is not None and self.file_load_worker.isRunning():
            QMessageBox.warning(self, "警告", "文件加载正在进行中，请稍候再合并")
            return

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

        # 进入合并状态：禁用按钮、显示进度条
        self.merge_btn.setEnabled(False)
        self.merge_btn.setText("合并中...")
        self._show_progress("文件合并中")

        # 启动后台工作线程执行合并
        self.worker = MergeWorker(
            pdf_handler=self.pdf_handler,
            pdf_paths=sorted_files,
            output_path=output_path,
            layout=layout_config,
            mode=mode,
            batch_size=50
        )
        self.worker.progress.connect(self._on_merge_progress)
        self.worker.finished.connect(self._on_merge_finished)
        self.worker.error.connect(self._on_merge_error)
        self.worker.start()

    def _on_merge_progress(self, current, total):
        """
        更新合并进度条

        参数:
            current: 当前已完成的步骤数
            total: 总步骤数
        """
        if total > 0:
            self.progress_bar.setValue(int(current * 100 / total))

    def _on_merge_finished(self, success, message):
        """
        合并完成后的回调

        参数:
            success: 是否成功
            message: 提示信息
        """
        self.progress_bar.setVisible(False)
        self.merge_btn.setEnabled(True)
        self.merge_btn.setText("合并 PDF")
        self._show_feedback(
            "合并完成　·　可打印或打开输出文件" if success else "合并未完成，请检查提示信息",
            "success" if success else "warning",
        )

        if success:
            QMessageBox.information(self, "成功", message)
            if self.print_checkbox.isChecked():
                self._on_print()
        else:
            QMessageBox.warning(self, "警告", message)

        self.worker = None

    def _on_merge_error(self, error_message):
        """
        合并过程中发生错误的回调

        参数:
            error_message: 错误信息
        """
        self.progress_bar.setVisible(False)
        self.merge_btn.setEnabled(True)
        self.merge_btn.setText("合并 PDF")
        self._show_feedback(f"合并失败　·　{error_message}", "danger")
        QMessageBox.critical(self, "错误", f"合并失败: {error_message}")
        self.worker = None

    def _on_open_output(self):
        """
        打开上次合并输出文件

        功能描述:
            输出条右侧「打开文件」入口：优先打开当前输出路径指向的 PDF；
            若文件不存在则提示用户先完成一次合并。

        参数:
            无
        """
        output_path = self.path_edit.text().strip()
        if not output_path or not os.path.exists(output_path):
            self._show_feedback("尚未生成输出文件　·　请先点击「合并 PDF」", "warning")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(output_path))

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
            
            invoices_per_page = layout_config['rows'] * layout_config['cols']
            self.pdf_handler.merge_pdfs(
                sorted_files,
                tmp_path,
                layout=layout_config,
                mode="普通",
                batch_size=invoices_per_page * 10
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
            打开重命名对话框，按票种配置重命名规则并执行批量重命名。
            打开前先把旧版单一规则迁移为按票种规则集合（若需要）。
        """
        files = self.file_list.get_all_files()
        if not files:
            QMessageBox.warning(self, "警告", "请先添加PDF文件")
            return

        # 打开对话框前执行旧配置迁移
        self._migrate_rename_rules_if_needed()

        # 打开重命名对话框
        dialog = RenameDialog(self, config_file=CONFIG_FILE)
        dialog.rename_executed.connect(self._perform_batch_rename)
        dialog.exec()

    def _migrate_rename_rules_if_needed(self):
        """
        迁移旧版单一重命名规则到按票种规则集合

        功能描述:
            读取配置，调用 migrate_rename_rules；发生迁移时立即落盘，
            使升级用户的既有规则自动作用于全部 7 类票种。
        """
        try:
            if not os.path.exists(CONFIG_FILE):
                return

            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)

            if migrate_rename_rules(config):
                with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"迁移重命名规则失败: {e}")

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

    def _perform_batch_rename(self, rules):
        """
        执行批量重命名

        功能描述:
            调用 InvoiceService 按票种规则对文件列表中的文件进行批量重命名，
            并刷新界面显示

        参数:
            rules: 票种标识 -> 重命名规则字符串的字典
        """
        if not rules:
            return

        files = self.file_list.get_all_files()
        if not files:
            return

        try:
            result = self.invoice_service.batch_rename(files, rules)

            # 同步更新文件列表中的路径
            for old_path, new_path in result.get('renamed_map', {}).items():
                self.file_list.update_file_path(old_path, new_path)

            # 刷新文件列表显示和预览
            self.file_list.refresh_display()
            self._update_preview()

            # 构建提示消息
            messages = []
            if result.get('renamed_count', 0) > 0:
                messages.append(f"成功重命名 {result['renamed_count']} 个文件")
            if result.get('failed_count', 0) > 0:
                messages.append(f"失败: {result['failed_count']} 个")
            if result.get('skipped_unconfigured_count', 0) > 0:
                messages.append(
                    f"跳过未配置规则的 {result['skipped_unconfigured_count']} 个文件"
                )
            if result.get('skipped_image_count', 0) > 0:
                messages.append(f"跳过 {result['skipped_image_count']} 个图片文件")
            if result.get('skipped_ofd_count', 0) > 0:
                messages.append(f"跳过 {result['skipped_ofd_count']} 个OFD文件")
            if len(result.get('unrecognized_files', [])) > 0:
                messages.append(f"未能识别: {len(result['unrecognized_files'])} 个文件（可能是图片格式，无法提取文本）")

            # 显示结果（v2：同时写入主界面统一回执）
            receipt = "　·　".join(messages) if messages else "没有文件需要重命名"
            self._show_feedback(f"批量重命名完成　·　{receipt}", "success")
            QMessageBox.information(self, "重命名完成", "\n".join(messages) if messages else
                                    "没有文件需要重命名\n（可能是生成的文件名与原文件名相同）")

        except Exception as e:
            self._show_feedback(f"批量重命名失败　·　{str(e)}", "danger")
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
            v2 UI 用台账标题栏的琥珀状态标签表达重复组数与涉及张数，
            行内由 FileListPanel 使用警示色标记；不再拼接标题文字或整行涂色。
        """
        update_duplicate_chip(self, count)
        if hasattr(self, 'status_left_label'):
            self._update_status_bar()
        try:
            self.file_list_label.setText("票据台账")
        except Exception:
            pass
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
            if is_supported_file(file_path):
                files.append(file_path)
            elif os.path.isdir(file_path):
                # 如果是目录，递归查找 PDF、图片和 OFD 文件
                for root, dirs, filenames in os.walk(file_path):
                    for filename in filenames:
                        if is_supported_file(filename):
                            files.append(os.path.join(root, filename))
        
        if files:
            self._start_file_load_worker(files)

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

        # v2：同步台账统计、预览摘要与状态栏
        if hasattr(self, 'status_left_label'):
            self._update_status_bar()
    
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
        self.merge_btn.setToolTip(
            "按当前布局合并全部发票并保存"
            if has_files else "请先添加发票文件后再合并"
        )
        # 空态引导由台账投放带与主按钮 tooltip 承担，状态栏临时消息位只放一次性回执
        if hasattr(self, 'status_left_label'):
            self._update_status_bar()
    
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
                    
                    # 加载页边距配置（兼容旧版无此字段的情况）
                    margins = layout_config.get('margins')
                    if margins:
                        self.margin_top_spinbox.setValue(margins.get('top', self.default_margins['top']))
                        self.margin_bottom_spinbox.setValue(margins.get('bottom', self.default_margins['bottom']))
                        self.margin_left_spinbox.setValue(margins.get('left', self.default_margins['left']))
                        self.margin_right_spinbox.setValue(margins.get('right', self.default_margins['right']))
                        # 触发预览更新和配置保存
                        self._on_margin_changed()
                    else:
                        # 旧版配置使用默认边距
                        self.margin_top_spinbox.setValue(self.default_margins['top'])
                        self.margin_bottom_spinbox.setValue(self.default_margins['bottom'])
                        self.margin_left_spinbox.setValue(self.default_margins['left'])
                        self.margin_right_spinbox.setValue(self.default_margins['right'])
                    
                    # 加载裁切线设置
                    show_crop_marks = layout_config.get('show_crop_marks', False)
                    self.crop_mark_checkbox.setChecked(show_crop_marks)
                    crop_mark_left = layout_config.get('crop_mark_left', 0)
                    self.crop_mark_left_spinbox.setValue(crop_mark_left)
                    crop_mark_right = layout_config.get('crop_mark_right', 0)
                    self.crop_mark_right_spinbox.setValue(crop_mark_right)
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
                    
                    # 旧版配置使用默认页边距
                    self.margin_top_spinbox.setValue(self.default_margins['top'])
                    self.margin_bottom_spinbox.setValue(self.default_margins['bottom'])
                    self.margin_left_spinbox.setValue(self.default_margins['left'])
                    self.margin_right_spinbox.setValue(self.default_margins['right'])

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
                if hasattr(self, 'status_left_label'):
                    self._update_status_bar()

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
                remote_version_url="https://piaoyihe.oss-cn-hangzhou.aliyuncs.com/update/version.json",
                config_file=CONFIG_FILE
            )
            
            # 检查是否有更新
            has_update, remote_version = checker.check_for_updates(ignore_ignored_version=force_check)
            
            if has_update:
                # 显示更新对话框
                qrcode_url = "https://piaoyihe.oss-cn-hangzhou.aliyuncs.com/update/updatelog.png"
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
        if hasattr(self, 'preview_zoom_label'):
            self.preview_zoom_label.setText(f"{zoom_percent}%")
    
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


    def _update_status_bar(self):
        """刷新台账统计、预览摘要与底部状态栏。"""
        update_status_bar(self)

    def _show_feedback(self, text, state="info"):
        """显示统一的结果回执（info / success / warning / danger）。"""
        show_feedback(self, text, state)


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
        
        # 标题（v2：由全局 QSS 的 sectionLabel 提供字号与颜色）
        title = QLabel("使用帮助")
        title.setObjectName("sectionLabel")
        layout.addWidget(title)
        
        # 帮助内容区域
        help_text = QTextEdit()
        help_text.setReadOnly(True)
        # 字体/边框/底色统一由 tokens.build_stylesheet() 的 QTextEdit / #helpText 提供
        help_text.setObjectName("helpText")
        
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
<li><b>页边距设置</b>：
  <ul>
    <li>可分别设置上、下、左、右边距，精度为 1 mm</li>
    <li>提供默认（10mm）、窄边距（5mm）、宽边距（20mm）三种预设</li>
    <li>调整后会实时更新右侧预览，合并与打印时均生效</li>
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
        separator.setObjectName("hSeparator")
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
                qrcode_label.setObjectName("qrcodePlaceholder")
        else:
            qrcode_label.setText("二维码")
            qrcode_label.setObjectName("qrcodePlaceholder")
        qrcode_label.setFixedSize(120, 120)
        qrcode_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        qrcode_layout.addWidget(qrcode_label)
        
        # 提示文字
        qrcode_text = QLabel("有其他问题可以扫码反馈")
        qrcode_text.setObjectName("qrcodeHint")
        qrcode_layout.addWidget(qrcode_text)
        
        layout.addLayout(qrcode_layout)
        
        # 设置样式（v2：统一令牌 + 清除历史内联样式）
        self._setup_stylesheet()
        clear_inline_styles(self)
        apply_numeric_text_fonts(self)
    
    def _setup_stylesheet(self):
        """使用帮助对话框同样消费 ui.tokens 生成的全局 QSS。"""
        self.setStyleSheet(build_stylesheet(_theme.dark))
