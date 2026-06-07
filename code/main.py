#!/usr/bin/env python3
"""
发票PDF合并排版工具
主程序入口
"""

import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QTimer
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
    
    # 确保窗口正常显示（解决PyInstaller打包后窗口最小化问题）
    window.show()
    window.raise_()
    window.activateWindow()
    
    # 延迟检查更新，确保主窗口完全显示后再弹出更新提示
    def delayed_check_update():
        local_version_file = os.path.join(os.path.dirname(__file__), 'version.json')
        config_file = os.path.join(os.path.dirname(__file__), 'config.json')
        remote_version_url = "https://piaoyihe.oss-cn-hangzhou.aliyuncs.com/update/version.json"
        qrcode_url = "https://piaoyihe.oss-cn-hangzhou.aliyuncs.com/update/updatelog.png"
        check_updates_on_start(window, local_version_file, remote_version_url, qrcode_url, config_file)
    
    # 延迟500毫秒后检查更新，确保主窗口已完全显示
    QTimer.singleShot(500, delayed_check_update)
    
    # 启动事件循环
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
