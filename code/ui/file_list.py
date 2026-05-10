#!/usr/bin/env python3
"""
文件列表面板模块

该模块提供文件列表面板组件，用于显示和管理发票PDF文件的列表
支持拖放添加文件、文件排序、双击打开、列排序、拖拽调整顺序、预览浮窗等功能
"""

import os
import time
import fitz  # PyMuPDF
from concurrent.futures import ThreadPoolExecutor
from PySide6.QtWidgets import (
    QWidget, QTableWidget, QVBoxLayout, QTableWidgetItem, 
    QHeaderView, QAbstractItemView, QMenu, QLabel, QFrame
)
from PySide6.QtCore import Qt, Signal, QUrl, QTimer, QPoint
from PySide6.QtGui import QDesktopServices, QAction, QPixmap, QCursor


class PreviewPopup(QFrame):
    """
    发票预览浮窗类
    
    功能描述:
        显示PDF发票的预览图像，点击预览图标时显示
    
    参数:
        parent: 父窗口部件
    """
    
    def __init__(self, parent=None):
        """
        初始化预览浮窗
        
        参数:
            parent: 父窗口部件，可选
        """
        super().__init__(parent)
        # 使用ToolTip窗口类型，不拦截鼠标事件
        self.setWindowFlags(Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
        # 设置属性，使窗口不获取焦点，不拦截鼠标事件
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        
        # 设置样式 - 使用白色背景
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 2px solid #2196F3;
                border-radius: 8px;
            }
        """)
        
        # 创建布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(0)
        
        # 创建图片标签
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("border: none; background-color: white;")
        layout.addWidget(self.image_label)
        
        # 设置固定大小（增大尺寸以获得更清晰的预览）
        self.setFixedSize(800, 1000)
        
        self.current_file = None
    
    def show_preview(self, file_path, global_pos):
        """
        显示指定文件的预览
        
        参数:
            file_path: PDF文件路径
            global_pos: 浮窗显示的全局位置
        """
        if not os.path.exists(file_path):
            return
        
        self.current_file = file_path
        
        try:
            # 使用PyMuPDF渲染PDF第一页
            doc = fitz.open(file_path)
            page = doc[0]
            
            # 设置渲染分辨率（DPI）- 使用更高缩放比例以获得更清晰的图像
            mat = fitz.Matrix(8, 8)  # 4x缩放以获得更清晰的图像
            pix = page.get_pixmap(matrix=mat)
            
            # 转换为QPixmap
            img_data = pix.tobytes("png")
            pixmap = QPixmap()
            pixmap.loadFromData(img_data)
            
            doc.close()
            
            # 缩放图片以适应浮窗大小（保持宽高比）- 增大尺寸
            scaled_pixmap = pixmap.scaled(
                780, 980,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            
            self.image_label.setPixmap(scaled_pixmap)
            
            # 调整浮窗大小以适应图片
            self.setFixedSize(
                max(scaled_pixmap.width() + 16, 400),
                max(scaled_pixmap.height() + 16, 500)
            )
            
        except Exception as e:
            print(f"预览加载失败: {e}")
            self.image_label.setText("预览加载失败")
            self.setFixedSize(500, 400)
        
        self.move(global_pos)
        self.show()
        self.raise_()
    
    def hide_preview(self):
        """
        隐藏预览浮窗
        """
        self.hide()


class FileListPanel(QWidget):
    """
    文件列表面板类
    
    功能描述:
        提供文件列表显示和管理的界面组件，支持文件添加、删除、排序、
        双击打开、列排序、拖拽调整顺序、预览浮窗等操作
    
    信号:
        selection_changed: 当选中项发生变化时发出
        file_added: 当添加文件时发出，参数为文件路径
        order_changed: 当列表顺序改变时发出（通过拖拽）
        duplicate_count_changed: 当重复发票数量变化时发出，参数为重复数量
        _duplicate_check_result: 内部信号，用于传递重复检查结果到主线程
    """

    selection_changed = Signal()
    file_added = Signal(str)
    order_changed = Signal()
    duplicate_count_changed = Signal(int)
    _duplicate_check_result = Signal(set)  # 内部信号，传递重复代码集合
    
    def __init__(self, pdf_handler, on_file_added=None, parent=None):
        """
        初始化文件列表面板
        
        参数:
            pdf_handler: PDF处理器实例，用于提取文件信息
            on_file_added: 文件添加回调函数，可选
            parent: 父窗口部件，可选
        """
        super().__init__(parent)
        
        self.pdf_handler = pdf_handler
        self.files = []
        self.on_file_added = on_file_added
        
        # 预览浮窗
        self.preview_popup = PreviewPopup(self)
        self.preview_timer = QTimer(self)
        self.preview_timer.setSingleShot(True)
        self.preview_timer.timeout.connect(self._show_preview_popup)
        
        # 当前悬停的行
        self.hover_row = -1
        
        # 重复发票检查相关
        self._duplicate_check_timer = QTimer(self)
        self._duplicate_check_timer.setSingleShot(True)
        self._duplicate_check_timer.timeout.connect(self._check_duplicates_async)
        self._executor = ThreadPoolExecutor(max_workers=2)
        self._duplicate_codes = set()

        # 连接内部信号到更新方法
        self._duplicate_check_result.connect(self._update_duplicate_display)

        self._init_ui()
    
    def _init_ui(self):
        """
        初始化用户界面
        
        功能描述:
            创建表格控件并设置列标题、布局等
            设置表格不可编辑、启用排序、启用拖拽
        """
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.table = QTableWidget()
        # 增加列数到8，新增发票号码列（放在文件名列前面）
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(["", "发票号码", "文件名", "金额", "开票日期", "路径", "修改日期", "大小"])

        # 设置选择行为
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

        # 设置表格不可编辑
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        # 启用排序功能
        self.table.setSortingEnabled(True)

        # 禁用拖拽功能（根据需求）
        self.table.setDragEnabled(False)
        self.table.setAcceptDrops(False)
        self.table.setDragDropMode(QAbstractItemView.DragDropMode.NoDragDrop)
        self.table.setDropIndicatorShown(False)

        # 设置交替行颜色
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(True)
        self.table.verticalHeader().setVisible(False)

        # 设置列宽调整模式
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # 预览图标列固定宽度
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # 发票号码列
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)  # 文件名列
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
        
        # 连接排序信号，当用户点击列标题排序时同步更新self.files列表
        header.sortIndicatorChanged.connect(self._on_sort_changed)
        
        # 设置预览图标列宽度
        self.table.setColumnWidth(0, 40)
        
        # 启用鼠标跟踪（macOS需要）
        self.table.setMouseTracking(True)
        self.table.viewport().setMouseTracking(True)
        
        # 连接信号
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        
        # 启用自定义上下文菜单（右键菜单）
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        
        # 安装事件过滤器以处理鼠标悬停
        self.table.viewport().installEventFilter(self)
        
        layout.addWidget(self.table)
    
    def eventFilter(self, obj, event):
        """
        事件过滤器，处理鼠标悬停事件
        
        参数:
            obj: 事件对象
            event: 事件
            
        返回值:
            bool: 是否已处理事件
        """
        if obj == self.table.viewport():
            if event.type() == event.Type.MouseMove:
                self._handle_mouse_move(event)
            elif event.type() == event.Type.Leave:
                self._handle_mouse_leave()
        
        return super().eventFilter(obj, event)
    
    def _handle_mouse_move(self, event):
        """
        处理鼠标移动事件，检测是否悬停在预览图标上
        
        参数:
            event: 鼠标事件
        """
        pos = event.position().toPoint()
        row = self.table.rowAt(pos.y())
        col = self.table.columnAt(pos.x())
        
        # 检查是否在预览图标列（第0列）且行有效
        if row >= 0 and row < len(self.files) and col == 0:
            if self.hover_row != row:
                self.hover_row = row
                # 立即显示预览，无需延迟
                self.preview_timer.stop()
                self._show_preview_popup()
        else:
            if self.hover_row != -1:
                self.hover_row = -1
                self.preview_timer.stop()
                self.preview_popup.hide_preview()
    
    def _handle_mouse_leave(self):
        """
        处理鼠标离开表格区域事件
        """
        self.hover_row = -1
        self.preview_timer.stop()
        self.preview_popup.hide_preview()
    
    def _show_preview_popup(self):
        """
        显示预览浮窗
        """
        if self.hover_row >= 0 and self.hover_row < len(self.files):
            file_path = self.files[self.hover_row]['path']
            
            # 计算浮窗位置（在鼠标右侧显示）
            cursor_pos = QCursor.pos()
            popup_pos = QPoint(cursor_pos.x() + 20, cursor_pos.y() - 300)
            
            # 确保浮窗不超出屏幕边界
            screen = self.screen()
            if screen:
                screen_geo = screen.availableGeometry()
                if popup_pos.x() + 800 > screen_geo.right():
                    popup_pos.setX(cursor_pos.x() - 820)
                if popup_pos.y() + 1000 > screen_geo.bottom():
                    popup_pos.setY(screen_geo.bottom() - 1020)
                if popup_pos.y() < screen_geo.top():
                    popup_pos.setY(screen_geo.top() + 10)
            
            self.preview_popup.show_preview(file_path, popup_pos)
    
    def _on_selection_changed(self):
        """
        选中项变化事件处理
        
        功能描述:
            触发selection_changed信号
        """
        self.selection_changed.emit()
    
    def _on_sort_changed(self, logical_index, order):
        """
        表格排序变化事件处理
        
        功能描述:
            当用户点击列标题排序时，同步更新self.files列表的顺序，
            确保"列表顺序"打印时使用当前界面显示的顺序
        
        参数:
            logical_index: 排序的列索引
            order: 排序顺序（Qt.SortOrder.AscendingOrder 或 Qt.SortOrder.DescendingOrder）
        """
        # 定义列索引到排序字段的映射
        # 列索引: 0-预览图标, 1-文件名, 2-金额, 3-开票日期, 4-路径, 5-修改日期, 6-大小
        sort_key_map = {
            1: lambda x: x['name'],       # 文件名
            2: lambda x: x['amount'],     # 金额
            3: lambda x: x['invoice_date'], # 开票日期
            4: lambda x: x['path'],       # 路径
            5: lambda x: x['mod_time'],   # 修改日期
            6: lambda x: x['size']        # 大小
        }
        
        if logical_index in sort_key_map:
            # 根据列索引获取排序键函数
            sort_key = sort_key_map[logical_index]
            
            # 对self.files列表进行排序
            self.files.sort(key=sort_key, reverse=(order == Qt.SortOrder.DescendingOrder))
            
            # 触发顺序变更信号
            self.order_changed.emit()
    
    def _show_context_menu(self, position):
        """
        显示右键上下文菜单
        
        功能描述:
            右键点击表格行时显示上下文菜单，包含打开文件、删除等选项
        
        参数:
            position: 鼠标右键点击的位置
        """
        # 获取视觉行索引
        visual_row = self.table.rowAt(position.y())
        if visual_row < 0 or visual_row >= len(self.files):
            return
        
        # 获取该行的文件路径，用于找到对应的数据索引
        path_item = self.table.item(visual_row, 5)  # 第5列是路径列（列号已改变）
        if not path_item:
            return
        
        file_path = path_item.text()
        
        # 在self.files中查找对应的索引
        data_row = -1
        for i, file_info in enumerate(self.files):
            if file_info['path'] == file_path:
                data_row = i
                break
        
        if data_row < 0:
            return
        
        # 选中当前行
        self.table.selectRow(visual_row)
        
        # 创建菜单
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                padding: 6px;
            }
            QMenu::item {
                padding: 8px 24px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #E3F2FD;
                color: #1976D2;
            }
            QMenu::separator {
                height: 1px;
                background-color: #E0E0E0;
                margin: 6px 0px;
            }
        """)
        
        # 添加"打开文件"动作
        open_action = QAction("📄 打开文件", self)
        open_action.triggered.connect(lambda: self._open_file_at_row(data_row))
        menu.addAction(open_action)
        
        # 添加"在文件夹中显示"动作
        show_in_folder_action = QAction("📁 在文件夹中显示", self)
        show_in_folder_action.triggered.connect(lambda: self._show_in_folder(data_row))
        menu.addAction(show_in_folder_action)
        
        menu.addSeparator()
        
        # 添加"删除"动作
        delete_action = QAction("🗑️ 删除", self)
        delete_action.triggered.connect(self.delete_selected)
        menu.addAction(delete_action)
        
        # 显示菜单
        menu.exec(self.table.viewport().mapToGlobal(position))
    
    def _open_file_at_row(self, row):
        """
        打开指定行的文件
        
        功能描述:
            使用系统默认程序打开指定行的PDF文件
        
        参数:
            row: 文件所在的行索引
        """
        if 0 <= row < len(self.files):
            file_path = self.files[row]['path']
            if os.path.exists(file_path):
                url = QUrl.fromLocalFile(file_path)
                QDesktopServices.openUrl(url)
    
    def _show_in_folder(self, row):
        """
        在文件夹中显示指定文件
        
        功能描述:
            使用系统文件管理器打开文件所在文件夹（仅打开目录，不选中文件）
        
        参数:
            row: 文件所在的行索引
        """
        if 0 <= row < len(self.files):
            file_path = self.files[row]['path']
            if os.path.exists(file_path):
                import subprocess
                import platform
                
                folder_path = os.path.dirname(file_path)
                system = platform.system()
                try:
                    if system == 'Windows':
                        # 仅打开文件夹，不选中文件
                        subprocess.run(['explorer', folder_path], check=True)
                    elif system == 'Darwin':  # macOS
                        subprocess.run(['open', folder_path], check=True)
                    else:  # Linux
                        subprocess.run(['xdg-open', folder_path], check=True)
                except Exception as e:
                    # 如果打开文件夹失败，静默处理
                    pass
    
    def _trigger_duplicate_check(self):
        """
        触发重复发票检查
        
        功能描述:
            当文件列表发生变化时，延迟触发异步重复发票检查
        """
        self._duplicate_check_timer.stop()
        self._duplicate_check_timer.start(300)  # 300ms延迟，避免频繁检查
    
    def _check_duplicates_async(self):
        """
        异步检查重复发票
        
        功能描述:
            在线程池中异步检查重复发票，避免阻塞主界面
        """
        if not self.files:
            self._duplicate_codes = set()
            self.duplicate_count_changed.emit(0)
            return
        
        # 提交异步任务
        self._executor.submit(self._do_check_duplicates)
    
    def _do_check_duplicates(self):
        """
        执行重复发票检查（在后台线程中运行）

        功能描述:
            统计所有发票号码的出现次数，找出重复的发票号码
        """
        from collections import Counter

        # 收集所有发票号码
        codes = []
        for file_info in self.files:
            code = file_info.get('invoice_code', '')
            print(f"[DEBUG] 文件: {file_info.get('name', '')}, 发票代码: '{code}'")
            if code:  # 只统计非空代码
                codes.append(code)

        print(f"[DEBUG] 收集到的发票代码: {codes}")

        # 统计重复
        code_counts = Counter(codes)
        print(f"[DEBUG] 代码统计: {dict(code_counts)}")

        duplicates = {code for code, count in code_counts.items() if count > 1}
        print(f"[DEBUG] 重复的发票代码: {duplicates}")

        # 更新UI（通过信号槽机制在主线程中执行）
        self._duplicate_check_result.emit(duplicates)
    
    def _update_duplicate_display(self, duplicate_codes):
        """
        更新重复发票显示

        功能描述:
            根据重复发票号码集合，更新表格行的背景色

        参数:
            duplicate_codes: 重复的发票号码集合
        """
        self._duplicate_codes = duplicate_codes
        duplicate_count = len(duplicate_codes)

        print(f"[DEBUG] _update_duplicate_display 被调用，重复代码: {duplicate_codes}, 表格行数: {self.table.rowCount()}")

        # 更新每行的背景色
        for row in range(self.table.rowCount()):
            # 获取该行的发票代码（第1列）
            code_item = self.table.item(row, 1)
            if code_item:
                code = code_item.text()
                is_duplicate = code in duplicate_codes and code != ""
                print(f"[DEBUG] 行 {row}: 代码='{code}', 是否重复={is_duplicate}")

                # 设置背景色
                for col in range(self.table.columnCount()):
                    item = self.table.item(row, col)
                    if item:
                        if is_duplicate:
                            item.setBackground(Qt.GlobalColor.yellow)
                        else:
                            item.setBackground(Qt.GlobalColor.transparent)

        # 发出重复数量变化信号
        print(f"[DEBUG] 发出 duplicate_count_changed 信号: {duplicate_count}")
        self.duplicate_count_changed.emit(duplicate_count)
    
    def dropEvent(self, event):
        """
        处理拖放事件（内部拖拽调整顺序）
        
        功能描述:
            处理表格内部的行拖拽，调整文件顺序
            拖拽前会禁用排序，确保视觉顺序和数据顺序一致
        
        参数:
            event: 拖放事件对象
        """
        # 临时禁用排序，确保视觉顺序和数据顺序一致
        was_sorting_enabled = self.table.isSortingEnabled()
        self.table.setSortingEnabled(False)
        
        # 获取拖放的源行和目标行（视觉行索引）
        source_row = self.table.currentRow()
        target_row = self.table.rowAt(event.position().toPoint().y())
        
        if source_row < 0 or target_row < 0 or source_row == target_row:
            event.ignore()
            if was_sorting_enabled:
                self.table.setSortingEnabled(True)
            return
        
        if target_row >= len(self.files):
            target_row = len(self.files) - 1
        
        # 调整文件列表顺序
        file_info = self.files.pop(source_row)
        self.files.insert(target_row, file_info)
        
        # 更新表格显示（不恢复排序，保持列表顺序）
        self._update_table_without_sort()
        
        # 选中被移动的行
        self.table.selectRow(target_row)
        
        # 发出顺序改变信号
        self.order_changed.emit()
        
        # 触发重复检查
        self._trigger_duplicate_check()
        
        event.accept()
    
    def _update_table_without_sort(self):
        """
        更新表格显示（不恢复排序）
        
        功能描述:
            重新渲染表格内容，不恢复之前的排序状态
        """
        self.table.setRowCount(0)
        
        for file_info in self.files:
            row = self.table.rowCount()
            self.table.insertRow(row)

            # 预览图标列
            preview_item = QTableWidgetItem("👁")
            preview_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            preview_item.setToolTip("悬停查看预览")

            # 发票号码列（第1列）
            code_item = QTableWidgetItem(file_info.get('invoice_code', ''))
            code_item.setData(Qt.ItemDataRole.UserRole, file_info.get('invoice_code', ''))

            name_item = QTableWidgetItem(file_info['name'])

            amount_item = QTableWidgetItem()
            amount_item.setData(Qt.ItemDataRole.DisplayRole, file_info['amount'])
            amount_item.setData(Qt.ItemDataRole.UserRole, file_info['amount'])

            date_item = QTableWidgetItem(file_info['invoice_date'])
            date_item.setData(Qt.ItemDataRole.UserRole, file_info['invoice_date'])

            path_item = QTableWidgetItem(file_info['path'])
            mod_item = QTableWidgetItem(file_info['mod_time'])
            size_item = QTableWidgetItem(file_info['size'])

            self.table.setItem(row, 0, preview_item)
            self.table.setItem(row, 1, code_item)
            self.table.setItem(row, 2, name_item)
            self.table.setItem(row, 3, amount_item)
            self.table.setItem(row, 4, date_item)
            self.table.setItem(row, 5, path_item)
            self.table.setItem(row, 6, mod_item)
            self.table.setItem(row, 7, size_item)

    def add_file(self, file_path):
        """
        添加文件到列表
        
        参数:
            file_path: 要添加的PDF文件路径
            
        返回值:
            无
        """
        for file_info in self.files:
            if file_info['path'] == file_path:
                return
        
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path) / 1024
        mod_time = os.path.getmtime(file_path)
        mod_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(mod_time))
        
        amount = self.pdf_handler.extract_amount(file_path)
        invoice_date = self.pdf_handler.extract_invoice_date(file_path)
        invoice_code = self.pdf_handler.extract_invoice_code(file_path)
        
        file_info = {
            'name': file_name,
            'amount': amount,
            'invoice_date': invoice_date,
            'invoice_code': invoice_code,
            'path': file_path,
            'mod_time': mod_time_str,
            'size': f"{file_size:.2f} KB"
        }
        
        is_first_file = len(self.files) == 0
        
        self.files.append(file_info)
        
        row = self.table.rowCount()
        self.table.insertRow(row)

        # 预览图标列
        preview_item = QTableWidgetItem("👁")
        preview_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_item.setToolTip("悬停查看预览")

        # 发票代码列（第1列）
        code_item = QTableWidgetItem(invoice_code)
        code_item.setData(Qt.ItemDataRole.UserRole, invoice_code)

        # 创建表格项并设置数据（用于排序）
        name_item = QTableWidgetItem(file_name)

        amount_item = QTableWidgetItem()
        amount_item.setData(Qt.ItemDataRole.DisplayRole, amount)
        amount_item.setData(Qt.ItemDataRole.UserRole, amount)

        date_item = QTableWidgetItem(invoice_date)
        date_item.setData(Qt.ItemDataRole.UserRole, invoice_date)

        path_item = QTableWidgetItem(file_path)
        mod_item = QTableWidgetItem(mod_time_str)
        size_item = QTableWidgetItem(file_info['size'])

        self.table.setItem(row, 0, preview_item)
        self.table.setItem(row, 1, code_item)
        self.table.setItem(row, 2, name_item)
        self.table.setItem(row, 3, amount_item)
        self.table.setItem(row, 4, date_item)
        self.table.setItem(row, 5, path_item)
        self.table.setItem(row, 6, mod_item)
        self.table.setItem(row, 7, size_item)
        
        # 触发重复发票检查
        self._trigger_duplicate_check()
        
        if is_first_file and self.on_file_added:
            self.on_file_added(file_path)
        
        self.file_added.emit(file_path)
    
    def delete_selected(self):
        """
        删除选中的文件
        
        功能描述:
            从文件列表中移除当前选中的文件
            
        返回值:
            bool: 删除是否成功
        """
        current_row = self.table.currentRow()
        if current_row < 0 or current_row >= len(self.files):
            return False
        
        self.files.pop(current_row)
        self.table.removeRow(current_row)
        
        # 触发重复发票检查
        self._trigger_duplicate_check()
        
        self.selection_changed.emit()
        return True
    
    def get_selected_file(self):
        """
        获取当前选中的文件路径
        
        返回值:
            str or None: 选中的文件路径，未选中则返回None
        """
        current_row = self.table.currentRow()
        if current_row < 0 or current_row >= len(self.files):
            return None
        return self.files[current_row]['path']
    
    def get_all_files(self, sort_by='list', selected_only=False):
        """
        获取所有文件路径列表
        
        功能描述:
            根据指定排序方式返回文件路径列表
        
        参数:
            sort_by: 排序方式，可选值：'list'（列表顺序）, 'date'（开票日期）, 'amount'（开票金额）
            selected_only: 是否只返回选中的文件
            
        返回值:
            list: 排序后的文件路径列表
        """
        if selected_only:
            current_row = self.table.currentRow()
            if current_row < 0:
                return []
            files_to_sort = [self.files[current_row]]
        else:
            files_to_sort = self.files.copy()
        
        if sort_by == 'date':
            files_to_sort.sort(key=lambda x: x['invoice_date'])
        elif sort_by == 'amount':
            files_to_sort.sort(key=lambda x: x['amount'])
        
        return [file_info['path'] for file_info in files_to_sort]
    
    def get_sorted_files(self, sort_by='list'):
        """
        获取排序后的文件路径列表
        
        功能描述:
            根据指定排序方式返回文件路径列表，与get_all_files功能相同
            用于兼容main_frame.py中的调用
        
        参数:
            sort_by: 排序方式，可选值：'list'（列表顺序）, 'date'（开票日期）, 'amount'（开票金额）
            
        返回值:
            list: 排序后的文件路径列表
        """
        return self.get_all_files(sort_by=sort_by, selected_only=False)
    
    def move_up(self):
        """
        将选中的文件上移一位
        
        返回值:
            bool: 移动是否成功
        """
        current_row = self.table.currentRow()
        if current_row <= 0:
            return False
        
        self.files[current_row], self.files[current_row - 1] = self.files[current_row - 1], self.files[current_row]
        
        self._update_table()
        
        self.table.selectRow(current_row - 1)
        self.order_changed.emit()
        
        # 触发重复发票检查
        self._trigger_duplicate_check()
        
        return True
    
    def move_down(self):
        """
        将选中的文件下移一位
        
        返回值:
            bool: 移动是否成功
        """
        current_row = self.table.currentRow()
        if current_row < 0 or current_row >= len(self.files) - 1:
            return False
        
        self.files[current_row], self.files[current_row + 1] = self.files[current_row + 1], self.files[current_row]
        
        self._update_table()
        
        self.table.selectRow(current_row + 1)
        self.order_changed.emit()
        
        # 触发重复发票检查
        self._trigger_duplicate_check()
        
        return True
    
    def _update_table(self):
        """
        更新表格显示
        
        功能描述:
            重新渲染表格内容以反映文件列表的当前状态
        """
        # 保存当前排序状态
        sort_column = self.table.horizontalHeader().sortIndicatorSection()
        sort_order = self.table.horizontalHeader().sortIndicatorOrder()
        
        # 临时禁用排序以避免冲突
        self.table.setSortingEnabled(False)
        
        self.table.setRowCount(0)
        
        for file_info in self.files:
            row = self.table.rowCount()
            self.table.insertRow(row)

            # 预览图标列
            preview_item = QTableWidgetItem("👁")
            preview_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            preview_item.setToolTip("悬停查看预览")

            # 发票代码列（第1列）
            code_item = QTableWidgetItem(file_info.get('invoice_code', ''))
            code_item.setData(Qt.ItemDataRole.UserRole, file_info.get('invoice_code', ''))

            name_item = QTableWidgetItem(file_info['name'])

            amount_item = QTableWidgetItem()
            amount_item.setData(Qt.ItemDataRole.DisplayRole, file_info['amount'])
            amount_item.setData(Qt.ItemDataRole.UserRole, file_info['amount'])

            date_item = QTableWidgetItem(file_info['invoice_date'])
            date_item.setData(Qt.ItemDataRole.UserRole, file_info['invoice_date'])

            path_item = QTableWidgetItem(file_info['path'])
            mod_item = QTableWidgetItem(file_info['mod_time'])
            size_item = QTableWidgetItem(file_info['size'])

            self.table.setItem(row, 0, preview_item)
            self.table.setItem(row, 1, code_item)
            self.table.setItem(row, 2, name_item)
            self.table.setItem(row, 3, amount_item)
            self.table.setItem(row, 4, date_item)
            self.table.setItem(row, 5, path_item)
            self.table.setItem(row, 6, mod_item)
            self.table.setItem(row, 7, size_item)

        # 恢复排序
        self.table.setSortingEnabled(True)
        if sort_column >= 0:
            self.table.sortItems(sort_column, sort_order)

        # 触发重复发票检查
        self._trigger_duplicate_check()

    def update_file_path(self, old_path, new_path):
        """
        更新文件路径
        
        功能描述:
            在文件列表中更新指定文件的路径和名称
        
        参数:
            old_path: 原文件路径
            new_path: 新文件路径
            
        返回值:
            bool: 更新是否成功
        """
        for file_info in self.files:
            if file_info['path'] == old_path:
                file_info['path'] = new_path
                file_info['name'] = os.path.basename(new_path)
                return True
        return False
    
    def refresh_display(self):
        """
        刷新显示
        
        功能描述:
            刷新文件列表的显示，更新所有文件信息
        """
        # 重新提取所有文件的信息
        for file_info in self.files:
            try:
                file_path = file_info['path']
                if os.path.exists(file_path):
                    # 更新文件信息
                    file_info['name'] = os.path.basename(file_path)
                    file_info['amount'] = self.pdf_handler.extract_amount(file_path)
                    file_info['invoice_date'] = self.pdf_handler.extract_invoice_date(file_path)
                    file_info['invoice_code'] = self.pdf_handler.extract_invoice_code(file_path)
                    
                    # 更新文件大小和修改时间
                    file_size = os.path.getsize(file_path) / 1024
                    mod_time = os.path.getmtime(file_path)
                    file_info['mod_time'] = __import__('time').strftime('%Y-%m-%d %H:%M:%S', __import__('time').localtime(mod_time))
                    file_info['size'] = f"{file_size:.2f} KB"
            except Exception as e:
                print(f"刷新文件信息失败: {e}")
        
        # 更新表格显示
        self._update_table()
    
    def clear(self):
        """
        清空文件列表
        
        功能描述:
            清空所有文件和表格内容
        """
        self.files.clear()
        self.table.setRowCount(0)
        self._duplicate_codes = set()
        self.duplicate_count_changed.emit(0)
