#!/usr/bin/env python3
"""
文件列表面板模块

该模块提供文件列表面板组件，用于显示和管理发票PDF文件的列表
支持拖放添加文件、文件排序、双击打开、列排序、拖拽调整顺序等功能
"""

import os
import time
from PySide6.QtWidgets import (
    QWidget, QTableWidget, QVBoxLayout, QTableWidgetItem, 
    QHeaderView, QAbstractItemView, QMenu
)
from PySide6.QtCore import Qt, Signal, QUrl
from PySide6.QtGui import QDesktopServices, QAction


class FileListPanel(QWidget):
    """
    文件列表面板类
    
    功能描述:
        提供文件列表显示和管理的界面组件，支持文件添加、删除、排序、
        双击打开、列排序、拖拽调整顺序等操作
    
    信号:
        selection_changed: 当选中项发生变化时发出
        file_added: 当添加文件时发出，参数为文件路径
        order_changed: 当列表顺序改变时发出（通过拖拽）
    """
    
    selection_changed = Signal()
    file_added = Signal(str)
    order_changed = Signal()
    
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
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["文件名", "金额", "开票日期", "路径", "修改日期", "大小"])
        
        # 设置选择行为
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        
        # 设置表格不可编辑
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        
        # 启用排序功能
        self.table.setSortingEnabled(True)
        
        # 启用拖拽功能（用于调整顺序）
        self.table.setDragEnabled(True)
        self.table.setAcceptDrops(True)
        self.table.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.table.setDropIndicatorShown(True)
        
        # 设置交替行颜色
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(True)
        self.table.verticalHeader().setVisible(False)
        
        # 设置列宽调整模式
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        
        # 连接信号
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        
        # 启用自定义上下文菜单（右键菜单）
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        
        layout.addWidget(self.table)
    
    def _on_selection_changed(self):
        """
        选中项变化事件处理
        
        功能描述:
            触发selection_changed信号
        """
        self.selection_changed.emit()
    
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
        path_item = self.table.item(visual_row, 3)  # 第3列是路径列
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
            
            name_item = QTableWidgetItem(file_info['name'])
            
            amount_item = QTableWidgetItem()
            amount_item.setData(Qt.ItemDataRole.DisplayRole, file_info['amount'])
            amount_item.setData(Qt.ItemDataRole.UserRole, file_info['amount'])
            
            date_item = QTableWidgetItem(file_info['invoice_date'])
            date_item.setData(Qt.ItemDataRole.UserRole, file_info['invoice_date'])
            
            path_item = QTableWidgetItem(file_info['path'])
            mod_item = QTableWidgetItem(file_info['mod_time'])
            size_item = QTableWidgetItem(file_info['size'])
            
            self.table.setItem(row, 0, name_item)
            self.table.setItem(row, 1, amount_item)
            self.table.setItem(row, 2, date_item)
            self.table.setItem(row, 3, path_item)
            self.table.setItem(row, 4, mod_item)
            self.table.setItem(row, 5, size_item)
    
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
        
        file_info = {
            'name': file_name,
            'amount': amount,
            'invoice_date': invoice_date,
            'path': file_path,
            'mod_time': mod_time_str,
            'size': f"{file_size:.2f} KB"
        }
        
        is_first_file = len(self.files) == 0
        
        self.files.append(file_info)
        
        row = self.table.rowCount()
        self.table.insertRow(row)
        
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
        
        self.table.setItem(row, 0, name_item)
        self.table.setItem(row, 1, amount_item)
        self.table.setItem(row, 2, date_item)
        self.table.setItem(row, 3, path_item)
        self.table.setItem(row, 4, mod_item)
        self.table.setItem(row, 5, size_item)
        
        if is_first_file and self.on_file_added:
            self.on_file_added(file_path)
    
    def delete_selected(self):
        """
        删除选中的文件
        
        功能描述:
            删除表格中当前选中的文件
        
        返回值:
            无
        """
        current_row = self.table.currentRow()
        if current_row >= 0:
            self.table.removeRow(current_row)
            self.files.pop(current_row)
    
    def delete_all(self):
        """
        删除所有文件
        
        功能描述:
            清空表格和文件列表
        
        返回值:
            无
        """
        self.table.setRowCount(0)
        self.files.clear()
    
    def get_all_files(self):
        """
        获取所有文件路径
        
        返回值:
            list: 所有文件的路径列表
        """
        return [file_info['path'] for file_info in self.files]
    
    def get_selected_files(self):
        """
        获取选中的文件路径
        
        返回值:
            list: 选中文件的路径列表
        """
        selected_files = []
        current_row = self.table.currentRow()
        if current_row >= 0 and current_row < len(self.files):
            selected_files.append(self.files[current_row]['path'])
        return selected_files
    
    def get_sorted_files(self, sort_by, selected_only=False):
        """
        获取排序后的文件路径列表
        
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
            
            name_item = QTableWidgetItem(file_info['name'])
            
            amount_item = QTableWidgetItem()
            amount_item.setData(Qt.ItemDataRole.DisplayRole, file_info['amount'])
            amount_item.setData(Qt.ItemDataRole.UserRole, file_info['amount'])
            
            date_item = QTableWidgetItem(file_info['invoice_date'])
            date_item.setData(Qt.ItemDataRole.UserRole, file_info['invoice_date'])
            
            path_item = QTableWidgetItem(file_info['path'])
            mod_item = QTableWidgetItem(file_info['mod_time'])
            size_item = QTableWidgetItem(file_info['size'])
            
            self.table.setItem(row, 0, name_item)
            self.table.setItem(row, 1, amount_item)
            self.table.setItem(row, 2, date_item)
            self.table.setItem(row, 3, path_item)
            self.table.setItem(row, 4, mod_item)
            self.table.setItem(row, 5, size_item)
        
        # 恢复排序
        self.table.setSortingEnabled(True)
        if sort_column >= 0:
            self.table.sortItems(sort_column, sort_order)
