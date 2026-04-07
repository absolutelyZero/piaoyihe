#!/usr/bin/env python3
"""
文件列表面板
"""

import wx
import os
import time

class FileListPanel(wx.Panel):
    """文件列表面板类"""
    
    def __init__(self, parent, pdf_handler, on_file_added=None):
        """初始化文件列表面板"""
        super(FileListPanel, self).__init__(parent)
        
        self.pdf_handler = pdf_handler
        self.files = []  # 存储文件信息的列表
        self.on_file_added = on_file_added  # 文件添加回调函数
        
        # 创建布局管理器
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        # 创建列表控件（单选模式）
        self.list_ctrl = wx.ListCtrl(self, style=wx.LC_REPORT | wx.LC_HRULES | wx.LC_VRULES | wx.LC_SINGLE_SEL)
        
        # 添加列
        self.list_ctrl.InsertColumn(0, "文件名", width=200)
        self.list_ctrl.InsertColumn(1, "金额", width=100)
        self.list_ctrl.InsertColumn(2, "开票日期", width=120)
        self.list_ctrl.InsertColumn(3, "路径", width=300)
        self.list_ctrl.InsertColumn(4, "修改日期", width=150)
        self.list_ctrl.InsertColumn(5, "大小", width=100)
        
        sizer.Add(self.list_ctrl, 1, wx.EXPAND | wx.ALL, 5)
        
        # 设置面板布局
        self.SetSizer(sizer)
    
    def add_file(self, file_path):
        """添加文件到列表"""
        # 检查文件是否已经存在
        for file_info in self.files:
            if file_info['path'] == file_path:
                return  # 文件已存在，不重复添加
        
        # 获取文件信息
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path) / 1024  # 转换为KB
        mod_time = os.path.getmtime(file_path)
        mod_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(mod_time))
        
        # 提取金额
        amount = self.pdf_handler.extract_amount(file_path)
        
        # 提取开票日期
        invoice_date = self.pdf_handler.extract_invoice_date(file_path)
        
        # 创建文件信息字典
        file_info = {
            'name': file_name,
            'amount': amount,
            'invoice_date': invoice_date,
            'path': file_path,
            'mod_time': mod_time_str,
            'size': f"{file_size:.2f} KB"
        }
        
        # 检查是否是第一个文件
        is_first_file = len(self.files) == 0
        
        # 添加到文件列表
        self.files.append(file_info)
        
        # 添加到列表控件
        index = self.list_ctrl.InsertItem(self.list_ctrl.GetItemCount(), file_name)
        self.list_ctrl.SetItem(index, 1, str(amount))
        self.list_ctrl.SetItem(index, 2, invoice_date)
        self.list_ctrl.SetItem(index, 3, file_path)
        self.list_ctrl.SetItem(index, 4, mod_time_str)
        self.list_ctrl.SetItem(index, 5, file_info['size'])
        
        # 如果是第一个文件，调用回调函数更新保存路径
        if is_first_file and self.on_file_added:
            self.on_file_added(file_path)
    
    def delete_selected(self):
        """删除选中的文件"""
        selected_items = []
        item = self.list_ctrl.GetFirstSelected()
        while item != -1:
            selected_items.append(item)
            item = self.list_ctrl.GetNextSelected(item)
        
        # 从后往前删除，避免索引混乱
        for item in reversed(selected_items):
            self.list_ctrl.DeleteItem(item)
            self.files.pop(item)
    
    def delete_all(self):
        """删除所有文件"""
        self.list_ctrl.DeleteAllItems()
        self.files.clear()
    
    def get_all_files(self):
        """获取所有文件路径"""
        return [file_info['path'] for file_info in self.files]
    
    def get_selected_files(self):
        """获取选中的文件路径"""
        selected_files = []
        item = self.list_ctrl.GetFirstSelected()
        while item != -1:
            selected_files.append(self.files[item]['path'])
            item = self.list_ctrl.GetNextSelected(item)
        return selected_files
    
    def get_sorted_files(self, sort_by, selected_only=False):
        """获取排序后的文件路径列表
        
        Args:
            sort_by: 排序方式，可选值：'list'（列表顺序）, 'date'（开票日期）, 'amount'（开票金额）
            selected_only: 是否只返回选中的文件
            
        Returns:
            list: 排序后的文件路径列表
        """
        # 获取文件列表
        if selected_only:
            # 获取选中的文件索引
            selected_indices = []
            item = self.list_ctrl.GetFirstSelected()
            while item != -1:
                selected_indices.append(item)
                item = self.list_ctrl.GetNextSelected(item)
            files_to_sort = [self.files[i] for i in selected_indices]
        else:
            files_to_sort = self.files.copy()
        
        # 根据排序方式排序
        if sort_by == 'date':
            # 按开票日期排序
            files_to_sort.sort(key=lambda x: x['invoice_date'])
        elif sort_by == 'amount':
            # 按金额排序
            files_to_sort.sort(key=lambda x: x['amount'])
        
        # 返回排序后的文件路径列表
        return [file_info['path'] for file_info in files_to_sort]
    
    def move_up(self):
        """将选中的文件上移一位"""
        selected_item = self.list_ctrl.GetFirstSelected()
        if selected_item == -1 or selected_item == 0:
            return False
        
        # 交换文件列表中的位置
        self.files[selected_item], self.files[selected_item - 1] = self.files[selected_item - 1], self.files[selected_item]
        
        # 更新列表控件
        self._update_list_display()
        
        # 重新选中移动后的项目
        self.list_ctrl.Select(selected_item - 1)
        return True
    
    def move_down(self):
        """将选中的文件下移一位"""
        selected_item = self.list_ctrl.GetFirstSelected()
        if selected_item == -1 or selected_item >= len(self.files) - 1:
            return False
        
        # 交换文件列表中的位置
        self.files[selected_item], self.files[selected_item + 1] = self.files[selected_item + 1], self.files[selected_item]
        
        # 更新列表控件
        self._update_list_display()
        
        # 重新选中移动后的项目
        self.list_ctrl.Select(selected_item + 1)
        return True
    
    def _update_list_display(self):
        """更新列表控件的显示"""
        # 清空列表控件
        self.list_ctrl.DeleteAllItems()
        
        # 重新添加所有文件
        for i, file_info in enumerate(self.files):
            index = self.list_ctrl.InsertItem(i, file_info['name'])
            self.list_ctrl.SetItem(index, 1, str(file_info['amount']))
            self.list_ctrl.SetItem(index, 2, file_info['invoice_date'])
            self.list_ctrl.SetItem(index, 3, file_info['path'])
            self.list_ctrl.SetItem(index, 4, file_info['mod_time'])
            self.list_ctrl.SetItem(index, 5, file_info['size'])
