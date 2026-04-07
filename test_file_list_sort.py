#!/usr/bin/env python3
"""
测试文件列表排序功能
"""

import os
import sys
import unittest
from unittest.mock import Mock

# 添加代码目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'code'))

# 简单的文件列表类，只包含排序相关的方法
class SimpleFileList:
    """简化的文件列表类，用于测试排序功能"""
    
    def __init__(self):
        self.files = []
        self.list_ctrl = Mock()
        self.list_ctrl.GetFirstSelected.return_value = -1
        self.list_ctrl.Select = Mock()
        self.list_ctrl.DeleteAllItems = Mock()
        self.list_ctrl.InsertItem = Mock()
        self.list_ctrl.SetItem = Mock()
    
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


class TestFileListSort(unittest.TestCase):
    """测试文件列表排序功能"""
    
    def setUp(self):
        """设置测试环境"""
        self.file_list = SimpleFileList()
    
    def test_move_up_single_file(self):
        """测试单个文件时上移功能"""
        # 添加一个文件
        self.file_list.files = [{'name': 'file1.pdf', 'amount': 100.0, 'invoice_date': '2023-01-01', 
                               'path': '/path/to/file1.pdf', 'mod_time': '2023-01-01', 'size': '100 KB'}]
        self.file_list.list_ctrl.GetFirstSelected.return_value = 0
        
        # 尝试上移（应该失败，因为是第一个文件）
        result = self.file_list.move_up()
        
        # 验证结果
        self.assertFalse(result)
        self.assertEqual(len(self.file_list.files), 1)
        self.assertEqual(self.file_list.files[0]['name'], 'file1.pdf')
    
    def test_move_down_single_file(self):
        """测试单个文件时下移功能"""
        # 添加一个文件
        self.file_list.files = [{'name': 'file1.pdf', 'amount': 100.0, 'invoice_date': '2023-01-01', 
                               'path': '/path/to/file1.pdf', 'mod_time': '2023-01-01', 'size': '100 KB'}]
        self.file_list.list_ctrl.GetFirstSelected.return_value = 0
        
        # 尝试下移（应该失败，因为是最后一个文件）
        result = self.file_list.move_down()
        
        # 验证结果
        self.assertFalse(result)
        self.assertEqual(len(self.file_list.files), 1)
        self.assertEqual(self.file_list.files[0]['name'], 'file1.pdf')
    
    def test_move_up_multiple_files(self):
        """测试多个文件时上移功能"""
        # 添加多个文件
        self.file_list.files = [
            {'name': 'file1.pdf', 'amount': 100.0, 'invoice_date': '2023-01-01', 
             'path': '/path/to/file1.pdf', 'mod_time': '2023-01-01', 'size': '100 KB'},
            {'name': 'file2.pdf', 'amount': 200.0, 'invoice_date': '2023-01-02', 
             'path': '/path/to/file2.pdf', 'mod_time': '2023-01-02', 'size': '200 KB'},
            {'name': 'file3.pdf', 'amount': 300.0, 'invoice_date': '2023-01-03', 
             'path': '/path/to/file3.pdf', 'mod_time': '2023-01-03', 'size': '300 KB'}
        ]
        self.file_list.list_ctrl.GetFirstSelected.return_value = 1  # 选中第二个文件
        
        # 执行上移
        result = self.file_list.move_up()
        
        # 验证结果
        self.assertTrue(result)
        self.assertEqual(len(self.file_list.files), 3)
        self.assertEqual(self.file_list.files[0]['name'], 'file2.pdf')  # 第二个文件移到第一个位置
        self.assertEqual(self.file_list.files[1]['name'], 'file1.pdf')  # 第一个文件移到第二个位置
        self.assertEqual(self.file_list.files[2]['name'], 'file3.pdf')  # 第三个文件位置不变
        
        # 验证重新选中了移动后的项目
        self.file_list.list_ctrl.Select.assert_called_with(0)
    
    def test_move_down_multiple_files(self):
        """测试多个文件时下移功能"""
        # 添加多个文件
        self.file_list.files = [
            {'name': 'file1.pdf', 'amount': 100.0, 'invoice_date': '2023-01-01', 
             'path': '/path/to/file1.pdf', 'mod_time': '2023-01-01', 'size': '100 KB'},
            {'name': 'file2.pdf', 'amount': 200.0, 'invoice_date': '2023-01-02', 
             'path': '/path/to/file2.pdf', 'mod_time': '2023-01-02', 'size': '200 KB'},
            {'name': 'file3.pdf', 'amount': 300.0, 'invoice_date': '2023-01-03', 
             'path': '/path/to/file3.pdf', 'mod_time': '2023-01-03', 'size': '300 KB'}
        ]
        self.file_list.list_ctrl.GetFirstSelected.return_value = 1  # 选中第二个文件
        
        # 执行下移
        result = self.file_list.move_down()
        
        # 验证结果
        self.assertTrue(result)
        self.assertEqual(len(self.file_list.files), 3)
        self.assertEqual(self.file_list.files[0]['name'], 'file1.pdf')  # 第一个文件位置不变
        self.assertEqual(self.file_list.files[1]['name'], 'file3.pdf')  # 第三个文件移到第二个位置
        self.assertEqual(self.file_list.files[2]['name'], 'file2.pdf')  # 第二个文件移到第三个位置
        
        # 验证重新选中了移动后的项目
        self.file_list.list_ctrl.Select.assert_called_with(2)
    
    def test_move_up_top_file(self):
        """测试顶部文件上移（应该失败）"""
        # 添加多个文件
        self.file_list.files = [
            {'name': 'file1.pdf', 'amount': 100.0, 'invoice_date': '2023-01-01', 
             'path': '/path/to/file1.pdf', 'mod_time': '2023-01-01', 'size': '100 KB'},
            {'name': 'file2.pdf', 'amount': 200.0, 'invoice_date': '2023-01-02', 
             'path': '/path/to/file2.pdf', 'mod_time': '2023-01-02', 'size': '200 KB'}
        ]
        self.file_list.list_ctrl.GetFirstSelected.return_value = 0  # 选中第一个文件
        
        # 尝试上移（应该失败）
        result = self.file_list.move_up()
        
        # 验证结果
        self.assertFalse(result)
        self.assertEqual(len(self.file_list.files), 2)
        self.assertEqual(self.file_list.files[0]['name'], 'file1.pdf')
        self.assertEqual(self.file_list.files[1]['name'], 'file2.pdf')
    
    def test_move_down_bottom_file(self):
        """测试底部文件下移（应该失败）"""
        # 添加多个文件
        self.file_list.files = [
            {'name': 'file1.pdf', 'amount': 100.0, 'invoice_date': '2023-01-01', 
             'path': '/path/to/file1.pdf', 'mod_time': '2023-01-01', 'size': '100 KB'},
            {'name': 'file2.pdf', 'amount': 200.0, 'invoice_date': '2023-01-02', 
             'path': '/path/to/file2.pdf', 'mod_time': '2023-01-02', 'size': '200 KB'}
        ]
        self.file_list.list_ctrl.GetFirstSelected.return_value = 1  # 选中第二个文件
        
        # 尝试下移（应该失败）
        result = self.file_list.move_down()
        
        # 验证结果
        self.assertFalse(result)
        self.assertEqual(len(self.file_list.files), 2)
        self.assertEqual(self.file_list.files[0]['name'], 'file1.pdf')
        self.assertEqual(self.file_list.files[1]['name'], 'file2.pdf')
    
    def test_move_up_no_selection(self):
        """测试没有选中文件时上移（应该失败）"""
        # 添加多个文件
        self.file_list.files = [
            {'name': 'file1.pdf', 'amount': 100.0, 'invoice_date': '2023-01-01', 
             'path': '/path/to/file1.pdf', 'mod_time': '2023-01-01', 'size': '100 KB'},
            {'name': 'file2.pdf', 'amount': 200.0, 'invoice_date': '2023-01-02', 
             'path': '/path/to/file2.pdf', 'mod_time': '2023-01-02', 'size': '200 KB'}
        ]
        self.file_list.list_ctrl.GetFirstSelected.return_value = -1  # 没有选中文件
        
        # 尝试上移（应该失败）
        result = self.file_list.move_up()
        
        # 验证结果
        self.assertFalse(result)
        self.assertEqual(len(self.file_list.files), 2)
        self.assertEqual(self.file_list.files[0]['name'], 'file1.pdf')
        self.assertEqual(self.file_list.files[1]['name'], 'file2.pdf')
    
    def test_move_down_no_selection(self):
        """测试没有选中文件时下移（应该失败）"""
        # 添加多个文件
        self.file_list.files = [
            {'name': 'file1.pdf', 'amount': 100.0, 'invoice_date': '2023-01-01', 
             'path': '/path/to/file1.pdf', 'mod_time': '2023-01-01', 'size': '100 KB'},
            {'name': 'file2.pdf', 'amount': 200.0, 'invoice_date': '2023-01-02', 
             'path': '/path/to/file2.pdf', 'mod_time': '2023-01-02', 'size': '200 KB'}
        ]
        self.file_list.list_ctrl.GetFirstSelected.return_value = -1  # 没有选中文件
        
        # 尝试下移（应该失败）
        result = self.file_list.move_down()
        
        # 验证结果
        self.assertFalse(result)
        self.assertEqual(len(self.file_list.files), 2)
        self.assertEqual(self.file_list.files[0]['name'], 'file1.pdf')
        self.assertEqual(self.file_list.files[1]['name'], 'file2.pdf')


if __name__ == '__main__':
    unittest.main(verbosity=2)
