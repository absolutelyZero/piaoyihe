#!/usr/bin/env python3
"""
发票PDF合并排版工具
主程序入口
"""

import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from ui.main_frame import MainWindow
from core.update_checker import check_updates_on_start


def main():
    """
    应用程序主入口函数
    
    功能描述:
        初始化PySide6应用程序，创建主窗口，并启动事件循环
    
    参数:
        无
    
    返回值:
        int: 应用程序退出码
    """
    # 启用高DPI支持
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    # 创建应用程序实例
    app = QApplication(sys.argv)
    
    # 设置应用程序字体
    font = QFont("Microsoft YaHei", 9)
    app.setFont(font)
    
    # 创建主窗口
    window = MainWindow()
    window.show()
    
    # 检查更新
    local_version_file = os.path.join(os.path.dirname(__file__), 'version.json')
    config_file = os.path.join(os.path.dirname(__file__), 'config.json')
    remote_version_url = "https://static-mp-3141b5af-f962-41dd-a6cd-4a4a7aecff39.next.bspapp.com/pyh/version.json"
    qrcode_url = "https://static-mp-3141b5af-f962-41dd-a6cd-4a4a7aecff39.next.bspapp.com/pyh/updatelog.png"
    check_updates_on_start(window, local_version_file, remote_version_url, qrcode_url, config_file)
    
    # 启动事件循环
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
