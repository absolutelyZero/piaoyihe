#!/usr/bin/env python3
"""
主窗口界面模块

该模块提供应用程序的主窗口界面，包括文件管理、布局选择、
PDF合并和打印等功能
"""

import os
import sys
import json
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                                QLabel, QPushButton, QLineEdit, QCheckBox, 
                                QComboBox, QGroupBox, QRadioButton, QButtonGroup,
                                QFileDialog, QMessageBox, QDialog, QScrollArea,
                                QSizePolicy, QFrame)
from PySide6.QtCore import Qt, QUrl, QTimer
from PySide6.QtGui import QGuiApplication, QDesktopServices, QCursor, QPixmap, QPainter
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from ui.file_list import FileListPanel
from core.pdf_handler import PDFHandler
from core.update_checker import UpdateChecker, show_update_dialog


CONFIG_FILE = os.path.join(os.path.dirname(__file__), '../config.json')
VERSION_FILE = os.path.join(os.path.dirname(__file__), '../version.json')


class MainWindow(QMainWindow):
    """
    主窗口类
    
    功能描述:
        应用程序主窗口，提供PDF文件管理、布局选择、合并和打印功能
    
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
        self.setMinimumSize(900, 600)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        top_widget = self._create_top_widget()
        main_layout.addWidget(top_widget)
        
        middle_widget = self._create_middle_widget()
        main_layout.addWidget(middle_widget, 1)
        
        bottom_widget = self._create_bottom_widget()
        main_layout.addWidget(bottom_widget)
    
    def _create_top_widget(self):
        """
        创建顶部区域控件
        
        功能描述:
            创建包含拖放提示、布局选择、模式选择等控件的顶部区域
        
        返回值:
            QWidget: 顶部区域控件
        """
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setSpacing(20)
        
        self.drop_label = QLabel("拖入PDF")
        self.drop_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(self.drop_label)
        
        layout_label = QLabel("布局选择:")
        layout.addWidget(layout_label)
        
        self.layout_group = QButtonGroup()
        self.layout_buttons = []
        layouts = ["竖向 1x2", "竖向 1x3", "竖向 2x4", "横向 2x2"]
        for i, layout_name in enumerate(layouts):
            radio = QRadioButton(layout_name)
            self.layout_group.addButton(radio, i)
            layout.addWidget(radio)
            self.layout_buttons.append(radio)
        self.layout_buttons[0].setChecked(True)
        
        self.layout_group.buttonClicked.connect(self._on_config_changed)
        
        mode_label = QLabel("模式:")
        layout.addWidget(mode_label)
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["普通", "图像"])
        self.mode_combo.setToolTip("普通模式：直接合并PDF，体积小，合并后内容可编辑，支持大部分情况；图像模式：将PDF转为图片后合并，兼容性更好，普通模式丢失信息时可以使用，合并后文件体积可能会变大")
        layout.addWidget(self.mode_combo)
        self.mode_combo.currentIndexChanged.connect(self._on_config_changed)
        
        order_label = QLabel("打印顺序:")
        layout.addWidget(order_label)
        
        self.order_combo = QComboBox()
        self.order_combo.addItems(["列表顺序", "开票日期(从先到后)", "开票金额(从小到大)"])
        layout.addWidget(self.order_combo)
        self.order_combo.currentIndexChanged.connect(self._on_config_changed)
        
        self.feedback_button = QPushButton("?")
        self.feedback_button.setFixedSize(30, 30)
        self.feedback_button.clicked.connect(self._on_feedback)
        layout.addWidget(self.feedback_button)
        
        layout.addStretch()
        
        return widget
    
    def _create_middle_widget(self):
        """
        创建中间区域控件
        
        功能描述:
            创建文件列表和统计面板
        
        返回值:
            QWidget: 中间区域控件
        """
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setSpacing(10)
        
        self.file_list = FileListPanel(self.pdf_handler, on_file_added=self._on_first_file_added)
        layout.addWidget(self.file_list, 1)
        
        self.file_list.selection_changed.connect(self._on_list_selection_changed)
        
        stats_widget = self._create_stats_widget()
        layout.addWidget(stats_widget)
        
        return widget
    
    def _create_stats_widget(self):
        """
        创建统计面板
        
        功能描述:
            创建包含统计信息和操作按钮的统计面板
        
        返回值:
            QWidget: 统计面板控件
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(5)
        
        self.file_count_label = QLabel("文件数量: 0")
        layout.addWidget(self.file_count_label)
        
        self.selected_count_label = QLabel("选中数量: 0")
        layout.addWidget(self.selected_count_label)
        
        self.total_amount_label = QLabel("总金额: 0")
        layout.addWidget(self.total_amount_label)
        
        self.selected_amount_label = QLabel("选中金额: 0")
        layout.addWidget(self.selected_amount_label)
        
        layout.addSpacing(10)
        
        move_layout = QHBoxLayout()
        self.move_up_button = QPushButton("↑")
        self.move_up_button.setFixedSize(30, 30)
        self.move_up_button.clicked.connect(self._on_move_up)
        move_layout.addWidget(self.move_up_button)
        
        self.move_down_button = QPushButton("↓")
        self.move_down_button.setFixedSize(30, 30)
        self.move_down_button.clicked.connect(self._on_move_down)
        move_layout.addWidget(self.move_down_button)
        layout.addLayout(move_layout)
        
        self.del_button = QPushButton("删除选中")
        self.del_button.clicked.connect(self._on_del)
        layout.addWidget(self.del_button)
        
        self.del_all_button = QPushButton("删除所有")
        self.del_all_button.clicked.connect(self._on_del_all)
        layout.addWidget(self.del_all_button)
        
        self.add_file_button = QPushButton("添加文件")
        self.add_file_button.clicked.connect(self._on_add_file)
        layout.addWidget(self.add_file_button)
        
        self.merge_all_button = QPushButton("合并")
        self.merge_all_button.clicked.connect(self._on_merge_all)
        layout.addWidget(self.merge_all_button)
        
        self.print_checkbox = QCheckBox("并打印")
        layout.addWidget(self.print_checkbox)
        
        self.print_checkbox.stateChanged.connect(self._on_config_changed)
        
        layout.addStretch()
        
        return widget
    
    def _create_bottom_widget(self):
        """
        创建底部区域控件
        
        功能描述:
            创建包含保存路径和打印按钮的底部区域
        
        返回值:
            QWidget: 底部区域控件
        """
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setSpacing(10)
        
        save_label = QLabel("保存路径")
        layout.addWidget(save_label)
        
        self.save_path_ctrl = QLineEdit("out.pdf")
        layout.addWidget(self.save_path_ctrl, 1)
        
        self.select_path_button = QPushButton("选择")
        self.select_path_button.clicked.connect(self._on_select_path)
        layout.addWidget(self.select_path_button)
        
        self.print_button = QPushButton("打印")
        self.print_button.clicked.connect(self._on_print)
        layout.addWidget(self.print_button)
        
        self.version_label = QLabel(self._get_version())
        self.version_label.setStyleSheet("color: gray;")
        self.version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.version_label.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.version_label.mousePressEvent = self._on_version_click
        layout.addWidget(self.version_label)
        
        return widget
    
    def _init_drag_drop(self):
        """
        初始化拖放功能
        
        功能描述:
            设置窗口接受文件拖放
        """
        self.setAcceptDrops(True)
    
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
        文件放下事件
        
        参数:
            event: 拖放事件对象
        """
        files = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.lower().endswith('.pdf'):
                files.append(path)
        
        if files:
            self.add_files(files)
    
    def _on_config_changed(self):
        """
        配置变更事件
        
        功能描述:
            保存配置
        """
        self._save_config()
    
    def _on_del(self):
        """
        删除选中文件
        """
        self.file_list.delete_selected()
        self._update_stats()
    
    def _on_del_all(self):
        """
        删除所有文件
        """
        self.file_list.delete_all()
        self._update_stats()
    
    def _on_add_file(self):
        """
        添加文件
        """
        files, _ = QFileDialog.getOpenFileNames(self, "选择PDF文件", "", "PDF files (*.pdf)")
        if files:
            for path in files:
                self.file_list.add_file(path)
            self._update_stats()
    
    def _on_merge_all(self):
        """
        合并所有文件
        """
        self._merge_files(selected_only=False)
    
    def _on_select_path(self):
        """
        选择保存路径
        """
        path, _ = QFileDialog.getSaveFileName(self, "保存PDF文件", self.save_path_ctrl.text(), "PDF files (*.pdf)")
        if path:
            if not path.endswith('.pdf'):
                path += '.pdf'
            self.save_path_ctrl.setText(path)
            self._save_config()
    
    def _on_print(self):
        """
        打印功能
        """
        save_path = self.save_path_ctrl.text()
        if not os.path.exists(save_path):
            QMessageBox.information(self, "提示", "请先合并PDF文件")
            return
        
        url = QUrl.fromLocalFile(os.path.abspath(save_path))
        QDesktopServices.openUrl(url)
    
    def _merge_files(self, selected_only=False):
        """
        合并文件
        
        参数:
            selected_only: 是否只合并选中的文件
        """
        files = self.file_list.get_selected_files() if selected_only else self.file_list.get_all_files()
        if not files:
            QMessageBox.information(self, "提示", "请先添加文件")
            return
        
        layout_index = self.layout_group.checkedId()
        layout = ["竖向 1x2", "竖向 1x3", "竖向 2x4", "横向 2x2"][layout_index]
        
        order_index = self.order_combo.currentIndex()
        order = ["list", "date", "amount"][order_index]
        
        mode_index = self.mode_combo.currentIndex()
        mode = ["普通", "图像"][mode_index]
        
        if order_index == 1:
            files = self.file_list.get_sorted_files('date', selected_only)
        elif order_index == 2:
            files = self.file_list.get_sorted_files('amount', selected_only)
        
        save_path = self.save_path_ctrl.text()
        try:
            result = self.pdf_handler.merge_pdfs(files, save_path, layout, mode)
            if result:
                QMessageBox.information(self, "成功", f"合并成功！保存至：{save_path}")
                self._save_config()
                if self.print_checkbox.isChecked():
                    self._on_print()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"合并失败：{str(e)}")
    
    def _update_stats(self):
        """
        更新统计信息
        """
        files = self.file_list.get_all_files()
        selected_files = self.file_list.get_selected_files()
        
        self.file_count_label.setText(f"文件数量: {len(files)}")
        self.selected_count_label.setText(f"选中数量: {len(selected_files)}")
        
        total_amount = sum(f['amount'] for f in self.file_list.files)
        self.total_amount_label.setText(f"总金额: {total_amount:.2f}")
        
        selected_amount = 0
        for path in selected_files:
            for f in self.file_list.files:
                if f['path'] == path:
                    selected_amount += f['amount']
                    break
        self.selected_amount_label.setText(f"选中金额: {selected_amount:.2f}")
        
        self._update_button_states()
    
    def _update_button_states(self):
        """
        更新按钮状态
        """
        current_row = self.file_list.table.currentRow()
        file_count = len(self.file_list.files)
        
        self.move_up_button.setEnabled(current_row > 0)
        self.move_down_button.setEnabled(0 <= current_row < file_count - 1)
    
    def _on_list_selection_changed(self):
        """
        列表选择变更事件
        """
        self._update_button_states()
    
    def _on_move_up(self):
        """
        上移选中文件
        """
        if self.file_list.move_up():
            self._update_stats()
    
    def _on_move_down(self):
        """
        下移选中文件
        """
        if self.file_list.move_down():
            self._update_stats()
    
    def add_files(self, paths):
        """
        添加文件
        
        参数:
            paths: 文件路径列表
        """
        for path in paths:
            if path.lower().endswith('.pdf'):
                self.file_list.add_file(path)
        self._update_stats()
    
    def _on_first_file_added(self, file_path):
        """
        当第一个文件添加时更新保存路径
        
        参数:
            file_path: 第一个文件的路径
        """
        directory = os.path.dirname(file_path)
        output_path = os.path.join(directory, 'output.pdf')
        self.save_path_ctrl.setText(output_path)
    
    def _load_config(self):
        """
        加载配置文件
        """
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    
                    if 'layout' in config:
                        layout_index = config['layout']
                        if 0 <= layout_index < len(self.layout_buttons):
                            self.layout_buttons[layout_index].setChecked(True)
                    
                    if 'mode' in config:
                        self.mode_combo.setCurrentIndex(config['mode'])
                    
                    if 'order' in config:
                        self.order_combo.setCurrentIndex(config['order'])
                    
                    if 'print_checkbox' in config:
                        self.print_checkbox.setChecked(config['print_checkbox'])
            else:
                self.layout_buttons[0].setChecked(True)
                self.mode_combo.setCurrentIndex(0)
                self.order_combo.setCurrentIndex(0)
                self.save_path_ctrl.setText("out.pdf")
                self.print_checkbox.setChecked(False)
        except Exception as e:
            print(f"加载配置失败: {e}")
            self.layout_buttons[0].setChecked(True)
            self.mode_combo.setCurrentIndex(0)
            self.order_combo.setCurrentIndex(0)
            self.save_path_ctrl.setText("out.pdf")
            self.print_checkbox.setChecked(False)
    
    def _save_config(self):
        """
        保存配置文件（增量更新，保留原有字段）
        
        功能描述:
            读取现有配置文件，更新界面相关配置，保留其他字段（如ignored_version）
        """
        try:
            # 先读取现有配置（如果存在）
            config = {}
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            
            # 更新界面配置
            config.update({
                'layout': self.layout_group.checkedId(),
                'mode': self.mode_combo.currentIndex(),
                'order': self.order_combo.currentIndex(),
                'print_checkbox': self.print_checkbox.isChecked()
            })
            
            os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"保存配置失败: {e}")
    
    def _on_feedback(self):
        """
        显示反馈问题对话框
        """
        dialog = FeedbackDialog(self)
        dialog.exec()
    
    def _get_version(self):
        """
        获取版本号
        
        返回值:
            str: 版本号字符串
        """
        try:
            if os.path.exists(VERSION_FILE):
                with open(VERSION_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    version = data.get('version', '0.0.0')
                    return f"v{version}"
            return "v0.0.0"
        except Exception as e:
            print(f"获取版本号失败: {e}")
            return "v0.0.0"
    
    def _is_version_newer(self, current_version, new_version):
        """
        比较版本号
        
        参数:
            current_version: 当前版本号
            new_version: 新版本号
            
        返回值:
            bool: 如果新版本更新则返回True
        """
        try:
            current_parts = list(map(int, current_version.split(".")))
            new_parts = list(map(int, new_version.split(".")))
            
            for i in range(max(len(current_parts), len(new_parts))):
                current = current_parts[i] if i < len(current_parts) else 0
                new = new_parts[i] if i < len(new_parts) else 0
                
                if new > current:
                    return True
                elif new < current:
                    return False
            return False
        except Exception:
            return False
    
    def _check_update_status(self):
        """
        检查更新状态并更新版本标签
        """
        try:
            current_version = '0.0.0'
            if os.path.exists(VERSION_FILE):
                with open(VERSION_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    current_version = data.get('version', '0.0.0')
            
            remote_version_url = "https://static-mp-3141b5af-f962-41dd-a6cd-4a4a7aecff39.next.bspapp.com/pyh/version.json"
            import requests
            response = requests.get(remote_version_url, timeout=5)
            response.raise_for_status()
            remote_data = response.json()
            remote_version = remote_data.get('version', '0.0.0')
            
            has_update = self._is_version_newer(current_version, remote_version)
            
            if has_update:
                self.version_label.setStyleSheet("color: blue;")
                self.version_label.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                self.remote_version = remote_version
            else:
                self.version_label.setStyleSheet("color: gray;")
                self.version_label.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
                self.remote_version = None
        except Exception as e:
            print(f"检查更新状态失败: {e}")
    
    def _on_version_click(self, event):
        """
        版本标签点击事件
        
        参数:
            event: 鼠标事件对象
        """
        try:
            if self.remote_version:
                local_version_file = VERSION_FILE
                remote_version_url = "https://static-mp-3141b5af-f962-41dd-a6cd-4a4a7aecff39.next.bspapp.com/pyh/version.json"
                qrcode_url = "https://static-mp-3141b5af-f962-41dd-a6cd-4a4a7aecff39.next.bspapp.com/pyh/updatelog.png"
                
                checker = UpdateChecker(local_version_file, remote_version_url, CONFIG_FILE)
                has_update, remote_version = checker.check_for_updates(ignore_ignored_version=True)
                
                if has_update:
                    show_update_dialog(self, qrcode_url, CONFIG_FILE, remote_version)
        except Exception as e:
            print(f"版本标签点击处理失败: {e}")
    
    def closeEvent(self, event):
        """
        窗口关闭事件
        
        参数:
            event: 关闭事件对象
        """
        self._save_config()
        event.accept()


class FeedbackDialog(QDialog):
    """
    反馈问题对话框类
    
    功能描述:
        显示反馈问题二维码的对话框
    """
    
    def __init__(self, parent=None):
        """
        初始化反馈对话框
        
        参数:
            parent: 父窗口，可选
        """
        super().__init__(parent)
        self.setWindowTitle("反馈问题")
        self.setMinimumSize(300, 400)
        self._init_ui()
    
    def _init_ui(self):
        """
        初始化用户界面
        """
        layout = QVBoxLayout(self)
        
        label = QLabel("如有问题，私信公众号反馈")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("font-size: 12px; font-weight: bold;")
        layout.addWidget(label)
        
        self.qr_label = QLabel()
        self.qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.qr_label.setMinimumSize(200, 200)
        layout.addWidget(self.qr_label)
        
        self._load_qrcode()
        
        close_button = QPushButton("关闭")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)
    
    def _load_qrcode(self):
        """
        加载二维码图片
        """
        if hasattr(sys, '_MEIPASS'):
            qrcode_path = os.path.join(sys._MEIPASS, 'res', 'qrcode.jpg')
        else:
            qrcode_path = os.path.join(os.path.dirname(__file__), '../res/qrcode.jpg')
        
        if os.path.exists(qrcode_path):
            pixmap = QPixmap(qrcode_path)
            scaled_pixmap = pixmap.scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.qr_label.setPixmap(scaled_pixmap)
        else:
            self.qr_label.setText("二维码加载失败")
