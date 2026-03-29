#!/usr/bin/env python3
"""
发票PDF合并排版工具
主程序入口
"""

import wx
import os
from ui.main_frame import MainFrame

class InvoiceToolApp(wx.App):
    """应用程序类"""
    
    def OnInit(self):
        """初始化应用"""
        # 创建主窗口
        frame = MainFrame(None, title="票易合 - 发票合并工具")
        frame.Center()
        frame.Show()
        return True

if __name__ == "__main__":
    app = InvoiceToolApp()
    app.MainLoop()
