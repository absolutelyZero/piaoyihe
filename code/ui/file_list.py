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
    QHeaderView, QAbstractItemView
)
from PySide6.QtCore import Qt, Signal, QUrl
from PySide6.QtGui import QDesktopServices


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
        self.table.itemDoubleClicked.connect(self._on_item_double_clicked)
        
        layout.addWidget(self.table)
    
    def _on_selection_changed(self):
        """
        选中项变化事件处理
        
        功能描述:
            触发selection_changed信号
        """
        self.selection_changed.emit()
    
    def _on_item_double_clicked(self, item):
        """
        双击项目事件处理
        
        功能描述:
            双击某行时，使用系统默认程序打开该PDF文件
        
        参数:
            item: 被双击的表格项
        """
        row = item.row()
        if 0 <= row < len(self.files):
            file_path = self.files[row]['path']
            if os.path.exists(file_path):
                url = QUrl.fromLocalFile(file_path)
                QDesktopServices.openUrl(url)
    
    def dropEvent(self, event):
        """
        处理拖放事件（内部拖拽调整顺序）
        
        功能描述:
            处理表格内部的行拖拽，调整文件顺序
        
        参数:
            event: 拖放事件对象
        """
        # 获取拖放的源行和目标行
        source_row = self.table.currentRow()
        target_row = self.table.rowAt(event.position().toPoint().y())
        
        if source_row < 0 or target_row < 0 or source_row == target_row:
            event.ignore()
            return
        
        if target_row >= len(self.files):
            target_row = len(self.files) - 1
        
        # 调整文件列表顺序
        file_info = self.files.pop(source_row)
        self.files.insert(target_row, file_info)
        
        # 更新表格显示
        self._update_table()
        
        # 选中被移动的行
        self.table.selectRow(target_row)
        
        # 发出顺序改变信号
        self.order_changed.emit()
        
        event.accept()
    
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
