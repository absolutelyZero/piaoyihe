#!/usr/bin/env python3
"""
主窗口界面
"""

import wx
import os
from ui.file_list import FileListPanel
from core.pdf_handler import PDFHandler

class MainFrame(wx.Frame):
    """主窗口类"""
    
    def __init__(self, parent, title):
        """初始化主窗口"""
        super(MainFrame, self).__init__(parent, title=title, size=(900, 600))
        
        # 初始化PDF处理器
        self.pdf_handler = PDFHandler()
        
        # # 设置窗口图标
        # icon_path = os.path.join(os.path.dirname(__file__), '../res/logo2.png')
        # if os.path.exists(icon_path):
        #     icon = wx.Icon(icon_path, wx.BITMAP_TYPE_PNG)
        #     self.SetIcon(icon)
        
        # 创建主面板
        self.panel = wx.Panel(self)
        
        # 创建布局管理器
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # 创建顶部区域（logo、拖放提示和布局选择）
        top_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        # 添加logo
        # logo_path = os.path.join(os.path.dirname(__file__), '../res/logo2.png')
        # if os.path.exists(logo_path):
        #     # 使用Image进行缩放
        #     logo_img = wx.Image(logo_path, wx.BITMAP_TYPE_PNG)
        #     logo_img = logo_img.Rescale(32, 32)
        #     logo_bmp = wx.Bitmap(logo_img)
        #     logo_static = wx.StaticBitmap(self.panel, -1, logo_bmp)
        #     top_sizer.Add(logo_static, 0, wx.ALL | wx.CENTER, 5)
        
        # 拖放提示
        self.drop_label = wx.StaticText(self.panel, label="拖入PDF")
        top_sizer.Add(self.drop_label, 0, wx.ALL, 20)
        
        # 布局选择
        layout_box = wx.StaticText(self.panel, label="布局选择:")

        layout_sizer = wx.BoxSizer(wx.HORIZONTAL)
        layout_sizer.Add(layout_box, 0, wx.ALL, 10)
        
        self.layout_choices = ["竖向 1x2", "竖向 1x3", "竖向 2x4", "横向 2x2"]
        self.layout_radio = wx.RadioBox(self.panel, choices=self.layout_choices, majorDimension=0, style=wx.RA_SPECIFY_COLS)
        self.layout_radio.SetSelection(0)  # 默认选择 竖向 1x2
        # 根据操作系统设置不同的边距参数
        if wx.Platform == '__WXMSW__':
            # Windows系统
            layout_sizer.Add(self.layout_radio, 0, wx.ALL, -10)
        else:
            # macOS及其他系统
            layout_sizer.Add(self.layout_radio, 0, wx.ALL, 0)
        
        top_sizer.Add(layout_sizer, 0, wx.ALL, 10)
        
        # 打印顺序选择
        order_box = wx.StaticText(self.panel, label="打印顺序:")
        top_sizer.Add(order_box, 0, wx.RIGHT | wx.TOP, 20)
        
        self.order_choices = ["列表顺序", "开票日期(从先到后)", "开票金额(从小到大)"]
        self.order_combo = wx.ComboBox(self.panel, choices=self.order_choices,size=(150,-1), style=wx.CB_READONLY)
        self.order_combo.SetSelection(0)  # 默认选择列表顺序
        top_sizer.Add(self.order_combo, 0, wx.TOP, 18)

        # 添加反馈问题按钮
        feedback_button = wx.Button(self.panel, label="?")
        feedback_button.Bind(wx.EVT_BUTTON, self.on_feedback)
        top_sizer.Add(feedback_button, 0, wx.ALL, 15)

        main_sizer.Add(top_sizer, 0, wx.EXPAND)
        
        # 创建中间区域（文件列表和统计面板）
        middle_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        # 文件列表面板
        self.file_list = FileListPanel(self.panel, self.pdf_handler, on_file_added=self.on_first_file_added)
        middle_sizer.Add(self.file_list, 1, wx.ALL | wx.EXPAND, 10)
        
        # 统计面板
        self.stats_panel = wx.Panel(self.panel)
        stats_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # 文件数
        self.file_count_label = wx.StaticText(self.stats_panel, label="文件数量: 0")
        stats_sizer.Add(self.file_count_label, 0, wx.ALL, 5)
        
        # 选中数量
        self.selected_count_label = wx.StaticText(self.stats_panel, label="选中数量: 0")
        stats_sizer.Add(self.selected_count_label, 0, wx.ALL, 5)
        
        # 总金额
        self.total_amount_label = wx.StaticText(self.stats_panel, label="总金额: 0")
        stats_sizer.Add(self.total_amount_label, 0, wx.ALL, 5)
        
        # 选中金额
        self.selected_amount_label = wx.StaticText(self.stats_panel, label="选中金额: 0")
        stats_sizer.Add(self.selected_amount_label, 0, wx.ALL, 5)
        
        # 操作按钮
        button_sizer = wx.BoxSizer(wx.VERTICAL)
        
        self.del_button = wx.Button(self.stats_panel, label="删除选中")
        self.del_button.Bind(wx.EVT_BUTTON, self.on_del)
        button_sizer.Add(self.del_button, 0, wx.ALL, 5)
        
        self.del_all_button = wx.Button(self.stats_panel, label="删除所有")
        self.del_all_button.Bind(wx.EVT_BUTTON, self.on_del_all)
        button_sizer.Add(self.del_all_button, 0, wx.ALL, 5)
        
        self.add_file_button = wx.Button(self.stats_panel, label="添加文件")
        self.add_file_button.Bind(wx.EVT_BUTTON, self.on_add_file)
        button_sizer.Add(self.add_file_button, 0, wx.ALL, 5)
        
        # self.merge_selected_button = wx.Button(self.stats_panel, label="合并选中")
        # self.merge_selected_button.Bind(wx.EVT_BUTTON, self.on_merge_selected)
        # button_sizer.Add(self.merge_selected_button, 0, wx.ALL, 5)
        
        self.merge_all_button = wx.Button(self.stats_panel, label="合并")
        self.merge_all_button.Bind(wx.EVT_BUTTON, self.on_merge_all)
        button_sizer.Add(self.merge_all_button, 0, wx.ALL, 5)
        
        stats_sizer.Add(button_sizer, 0, wx.ALL, 5)
        
        # 并打印复选框
        self.print_checkbox = wx.CheckBox(self.stats_panel, label="并打印")
        stats_sizer.Add(self.print_checkbox, 0, wx.ALL, 5)

        
        self.stats_panel.SetSizer(stats_sizer)
        middle_sizer.Add(self.stats_panel, 0, wx.ALL, 10)
        
        main_sizer.Add(middle_sizer, 1, wx.EXPAND)
        
        # 创建底部区域（保存路径和打印按钮）
        bottom_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        # 保存路径
        save_label = wx.StaticText(self.panel, label="保存路径")
        bottom_sizer.Add(save_label, 0, wx.ALL | wx.CENTER, 5)
        
        self.save_path_ctrl = wx.TextCtrl(self.panel, value="out.pdf")
        bottom_sizer.Add(self.save_path_ctrl, 1, wx.ALL, 5)
        
        self.select_path_button = wx.Button(self.panel, label="选择")
        self.select_path_button.Bind(wx.EVT_BUTTON, self.on_select_path)
        bottom_sizer.Add(self.select_path_button, 0, wx.ALL, 5)
        
        self.print_button = wx.Button(self.panel, label="打印")
        self.print_button.Bind(wx.EVT_BUTTON, self.on_print)
        bottom_sizer.Add(self.print_button, 0, wx.ALL, 5)
        
        main_sizer.Add(bottom_sizer, 0, wx.ALL | wx.EXPAND, 10)
        
        # 设置主面板布局
        self.panel.SetSizer(main_sizer)
        
        # 设置文件拖放
        self.SetDropTarget(FileDropTarget(self))
        
        # 更新统计信息
        self.update_stats()
    
    def on_del(self, event):
        """删除选中文件"""
        self.file_list.delete_selected()
        self.update_stats()
    
    def on_del_all(self, event):
        """删除所有文件"""
        self.file_list.delete_all()
        self.update_stats()
    
    def on_add_file(self, event):
        """添加文件"""
        with wx.FileDialog(self, "选择PDF文件", wildcard="PDF files (*.pdf)|*.pdf",
                          style=wx.FD_OPEN | wx.FD_MULTIPLE) as dialog:
            if dialog.ShowModal() == wx.ID_OK:
                paths = dialog.GetPaths()
                for path in paths:
                    self.file_list.add_file(path)
                self.update_stats()
    
    def on_merge_selected(self, event):
        """合并选中文件"""
        self.merge_files(selected_only=True)
    
    def on_merge_all(self, event):
        """合并所有文件"""
        self.merge_files(selected_only=False)
    
    def on_select_path(self, event):
        """选择保存路径"""
        with wx.FileDialog(self, "保存PDF文件", wildcard="PDF files (*.pdf)|*.pdf",
                          style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as dialog:
            if dialog.ShowModal() == wx.ID_OK:
                self.save_path_ctrl.SetValue(dialog.GetPath())
    
    def on_print(self, event):
        """打印功能"""
        save_path = self.save_path_ctrl.GetValue()
        if not os.path.exists(save_path):
            wx.MessageBox("请先合并PDF文件", "提示", wx.OK | wx.ICON_INFORMATION)
            return
        
        # 使用系统默认程序打开并打印
        if wx.Platform == '__WXMAC__':
            # macOS
            os.system(f'open -a Preview {save_path}')
        elif wx.Platform == '__WXMSW__':
            # Windows
            os.system(f'start {save_path}')
        else:
            # Linux
            os.system(f'xdg-open {save_path}')
    
    def merge_files(self, selected_only=False):
        """合并文件"""
        files = self.file_list.get_selected_files() if selected_only else self.file_list.get_all_files()
        if not files:
            wx.MessageBox("请先添加文件", "提示", wx.OK | wx.ICON_INFORMATION)
            return
        
        # 获取布局选择
        layout_index = self.layout_radio.GetSelection()
        layout = self.layout_choices[layout_index]
        
        # 获取打印顺序选择
        order_index = self.order_combo.GetSelection()
        order = self.order_choices[order_index]
        
        # 根据打印顺序获取排序后的文件列表（不影响列表显示）
        if order_index == 1:
            files = self.file_list.get_sorted_files('date', selected_only)
        elif order_index == 2:
            files = self.file_list.get_sorted_files('amount', selected_only)
        
        # 执行合并
        save_path = self.save_path_ctrl.GetValue()
        try:
            result = self.pdf_handler.merge_pdfs(files, save_path, layout)
            if result:
                wx.MessageBox(f"合并成功！保存至：{save_path}", "成功", wx.OK | wx.ICON_INFORMATION)
                # 如果勾选了并打印，执行打印
                if self.print_checkbox.GetValue():
                    self.on_print(None)
        except Exception as e:
            wx.MessageBox(f"合并失败：{str(e)}", "错误", wx.OK | wx.ICON_ERROR)
    
    def update_stats(self):
        """更新统计信息"""
        files = self.file_list.get_all_files()
        selected_files = self.file_list.get_selected_files()
        
        # 更新文件数
        self.file_count_label.SetLabel(f"文件数量: {len(files)}")
        
        # 更新选中数量
        self.selected_count_label.SetLabel(f"选中数量: {len(selected_files)}")
        
        # 计算总金额
        total_amount = 0
        for file_info in self.file_list.files:
            total_amount += file_info['amount']
        self.total_amount_label.SetLabel(f"总金额: {total_amount:.2f}")
        
        # 计算选中金额
        selected_amount = 0
        selected_indices = []
        item = self.file_list.list_ctrl.GetFirstSelected()
        while item != -1:
            selected_indices.append(item)
            item = self.file_list.list_ctrl.GetNextSelected(item)
        
        for index in selected_indices:
            if 0 <= index < len(self.file_list.files):
                selected_amount += self.file_list.files[index]['amount']
        self.selected_amount_label.SetLabel(f"选中金额: {selected_amount:.2f}")
    
    def add_files(self, paths):
        """添加文件（从拖放调用）"""
        for path in paths:
            if path.lower().endswith('.pdf'):
                self.file_list.add_file(path)
        self.update_stats()
    
    def on_first_file_added(self, file_path):
        """当第一个文件添加时更新保存路径"""
        # 获取第一个文件所在的目录
        directory = os.path.dirname(file_path)
        # 创建默认的输出路径
        output_path = os.path.join(directory, 'output.pdf')
        # 更新保存路径文本框
        self.save_path_ctrl.SetValue(output_path)
    
    def on_feedback(self, event):
        """显示反馈问题对话框"""
        # 创建对话框
        dialog = wx.Dialog(self, title="反馈问题", size=(300, 400))
        dialog_panel = wx.Panel(dialog)
        dialog_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # 添加二维码图片
        qrcode_path = os.path.join(os.path.dirname(__file__), '../res/qrcode.jpg')
        if os.path.exists(qrcode_path):
            qrcode_img = wx.Image(qrcode_path, wx.BITMAP_TYPE_JPEG)
            qrcode_img = qrcode_img.Rescale(200, 200)
            qrcode_bmp = wx.Bitmap(qrcode_img)
            qrcode_static = wx.StaticBitmap(dialog_panel, -1, qrcode_bmp)
            dialog_sizer.Add(qrcode_static, 0, wx.ALL | wx.CENTER, 20)
        
        # 添加说明文字
        feedback_text = wx.StaticText(dialog_panel, label="如有问题，私信公众号反馈")
        feedback_text.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        dialog_sizer.Add(feedback_text, 0, wx.ALL | wx.CENTER, 10)
        
        # 添加关闭按钮
        close_button = wx.Button(dialog_panel, label="关闭")
        close_button.Bind(wx.EVT_BUTTON, lambda e: dialog.Close())
        dialog_sizer.Add(close_button, 0, wx.ALL | wx.CENTER, 20)
        
        # 设置对话框布局
        dialog_panel.SetSizer(dialog_sizer)
        dialog.CenterOnParent()
        dialog.ShowModal()
        dialog.Destroy()

class FileDropTarget(wx.FileDropTarget):
    """文件拖放目标"""
    
    def __init__(self, frame):
        """初始化拖放目标"""
        super(FileDropTarget, self).__init__()
        self.frame = frame
    
    def OnDropFiles(self, x, y, filenames):
        """处理文件拖放"""
        self.frame.add_files(filenames)
        return True
