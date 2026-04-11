#!/usr/bin/env python3
"""
发票PDF合并排版工具
主程序入口
"""

import wx
import os
from ui.main_frame import MainFrame
from core.update_checker import check_updates_on_start

class InvoiceToolApp(wx.App):
    """应用程序类"""
    
    def OnInit(self):
        """初始化应用"""
        # 创建主窗口
        frame = MainFrame(None, title="票易合 - 发票合并工具")
        frame.Center()
        frame.Show()
        
        # 检查更新
        local_version_file = os.path.join(os.path.dirname(__file__), 'version.json')
        config_file = os.path.join(os.path.dirname(__file__), 'config.json')
        remote_version_url = "https://static-mp-3141b5af-f962-41dd-a6cd-4a4a7aecff39.next.bspapp.com/pyh/version.json"
        qrcode_url = "https://static-mp-3141b5af-f962-41dd-a6cd-4a4a7aecff39.next.bspapp.com/pyh/updatelog.png"
        check_updates_on_start(self, local_version_file, remote_version_url, qrcode_url, config_file)
        
        return True

if __name__ == "__main__":
    app = InvoiceToolApp()
    app.MainLoop()
