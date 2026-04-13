# -*- coding: utf-8 -*-
"""
更新检查模块

提供软件版本更新检查功能，包括：
- 本地版本与远程版本比较
- 更新提示对话框
- 二维码展示对话框
"""

import json
import os
from urllib import request

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMessageBox


class UpdateChecker:
    """
    版本更新检查器类
    
    用于检查软件是否有新版本可用，支持版本号比较和忽略版本功能。
    """
    
    def __init__(self, local_version_file, remote_version_url, config_file):
        """
        初始化更新检查器
        
        Args:
            local_version_file (str): 本地版本文件路径
            remote_version_url (str): 远程版本信息URL
            config_file (str): 配置文件路径
        """
        self.local_version_file = local_version_file
        self.remote_version_url = remote_version_url
        self.config_file = config_file
    
    def _get_local_version(self):
        """
        从本地版本文件读取版本号
        
        Returns:
            str: 本地版本号，如果读取失败返回'0.0.0'
        """
        try:
            if os.path.exists(self.local_version_file):
                with open(self.local_version_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('version', '0.0.0')
            return '0.0.0'
        except Exception:
            return '0.0.0'
    
    def _get_ignored_version(self):
        """
        从config.json读取ignored_version字段
        
        Returns:
            str: 已忽略的版本号，如果不存在或读取失败返回'0.0.0'
        """
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    return config.get('ignored_version', '0.0.0')
            return '0.0.0'
        except Exception:
            return '0.0.0'
    
    def _set_ignored_version(self, version):
        """
        将版本号写入config.json的ignored_version字段
        
        Args:
            version (str): 要忽略的版本号
        """
        try:
            config = {}
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            config['ignored_version'] = version
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    
    def _is_version_greater_than(self, version1, version2):
        """
        比较版本号，返回version1 > version2
        
        Args:
            version1 (str): 第一个版本号
            version2 (str): 第二个版本号
        
        Returns:
            bool: version1是否大于version2
        """
        try:
            v1_parts = [int(x) for x in version1.split('.')]
            v2_parts = [int(x) for x in version2.split('.')]
            
            # 补齐长度
            max_len = max(len(v1_parts), len(v2_parts))
            v1_parts.extend([0] * (max_len - len(v1_parts)))
            v2_parts.extend([0] * (max_len - len(v2_parts)))
            
            for i in range(max_len):
                if v1_parts[i] > v2_parts[i]:
                    return True
                elif v1_parts[i] < v2_parts[i]:
                    return False
            return False
        except Exception:
            return False
    
    def _is_version_newer(self, version):
        """
        比较版本号，返回version > current_version
        
        Args:
            version (str): 要比较的版本号
        
        Returns:
            bool: 该版本是否比当前版本新
        """
        current_version = self._get_local_version()
        return self._is_version_greater_than(version, current_version)
    
    def check_for_updates(self, ignore_ignored_version=False):
        """
        检查是否有可用更新
        
        Args:
            ignore_ignored_version (bool): 是否忽略已忽略的版本，默认为False
        
        Returns:
            tuple: (bool, str) - (是否有更新, 远程版本号)
        """
        try:
            # 获取远程版本
            with request.urlopen(self.remote_version_url, timeout=10) as response:
                remote_data = json.loads(response.read().decode('utf-8'))
                remote_version = remote_data.get('version', '0.0.0')
            
            current_version = self._get_local_version()
            
            print(f"当前版本: {current_version}, 远程版本: {remote_version}, 忽略版本: {self._get_ignored_version()}")
            
            # 如果远程版本 > 当前版本
            if self._is_version_greater_than(remote_version, current_version):
                if ignore_ignored_version:
                    print(f"用户主动检查，显示更新对话框")
                    return (True, remote_version)
                else:
                    ignored_version = self._get_ignored_version()
                    # 如果远程版本 > 已忽略版本
                    if self._is_version_greater_than(remote_version, ignored_version):
                        print(f"远程版本 {remote_version} > 忽略版本 {ignored_version}，显示更新对话框")
                        return (True, remote_version)
                    else:
                        print(f"远程版本 {remote_version} <= 忽略版本 {ignored_version}，跳过弹窗")
                        return (False, remote_version)
            else:
                print(f"当前版本已是最新")
            
            return (False, remote_version)
        except Exception as e:
            print(f"检查更新失败: {e}")
            return (False, '0.0.0')


class UpdateDialog(QDialog):
    """
    更新提示对话框类
    
    用于显示发现新版本的提示，提供查看更新和忽略当前版本选项。
    """
    
    def __init__(self, parent, qrcode_url, config_file, remote_version):
        """
        初始化更新提示对话框
        
        Args:
            parent (QWidget): 父窗口
            qrcode_url (str): 二维码图片URL
            config_file (str): 配置文件路径
            remote_version (str): 远程版本号
        """
        super().__init__(parent)
        self.qrcode_url = qrcode_url
        self.config_file = config_file
        self.remote_version = remote_version
        self._update_checker = UpdateChecker('', '', config_file)
        self._init_ui()
    
    def _init_ui(self):
        """
        创建界面
        
        显示"发现新版本 v{remote_version}，是否查看更新内容？"，
        两个按钮"查看更新"和"忽略当前版本"
        """
        self.setWindowTitle('发现新版本')
        self.setModal(True)
        self.setMinimumWidth(300)
        
        layout = QVBoxLayout()
        
        # 提示文本
        message_label = QLabel(f'发现新版本 v{self.remote_version}，是否查看更新内容？')
        message_label.setWordWrap(True)
        layout.addWidget(message_label)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        
        self.view_button = QPushButton('查看更新')
        self.view_button.clicked.connect(self._show_qrcode)
        button_layout.addWidget(self.view_button)
        
        self.ignore_button = QPushButton('忽略当前版本')
        self.ignore_button.clicked.connect(self._ignore_version)
        button_layout.addWidget(self.ignore_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def _show_qrcode(self):
        """
        打开QRCodeDialog
        
        显示二维码对话框供用户扫码查看更新内容
        """
        dialog = QRCodeDialog(self, self.qrcode_url)
        dialog.exec()
    
    def _ignore_version(self):
        """
        忽略当前版本
        
        调用_update_checker._set_ignored_version保存忽略版本，关闭对话框
        """
        self._update_checker._set_ignored_version(self.remote_version)
        self.close()


class QRCodeDialog(QDialog):
    """
    二维码展示对话框类
    
    用于显示二维码图片，供用户扫码查看更新内容。
    """
    
    def __init__(self, parent, qrcode_url):
        """
        初始化二维码对话框
        
        Args:
            parent (QWidget): 父窗口
            qrcode_url (str): 二维码图片URL
        """
        super().__init__(parent)
        self.qrcode_url = qrcode_url
        self._init_ui()
    
    def _init_ui(self):
        """
        创建界面
        
        显示"请扫码查看更新内容和更新方法"，二维码图片，关闭按钮
        """
        self.setWindowTitle('查看更新')
        self.setModal(True)
        self.setMinimumWidth(300)
        
        layout = QVBoxLayout()
        
        # 提示文本
        message_label = QLabel('请扫码查看更新内容和更新方法')
        message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(message_label)
        
        # 二维码图片标签
        self.qrcode_label = QLabel()
        self.qrcode_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.qrcode_label.setMinimumSize(200, 200)
        layout.addWidget(self.qrcode_label)
        
        # 加载二维码
        self._load_qrcode()
        
        # 关闭按钮
        close_button = QPushButton('关闭')
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)
        
        self.setLayout(layout)
    
    def _load_qrcode(self):
        """
        下载并显示二维码图片
        
        从远程URL下载二维码图片并显示在对话框中
        """
        try:
            from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest
            from PySide6.QtCore import QUrl
            
            self.network_manager = QNetworkAccessManager()
            self.network_manager.finished.connect(self._on_qrcode_loaded)
            req = QNetworkRequest(QUrl(self.qrcode_url))
            self.network_manager.get(req)
        except Exception as e:
            self.qrcode_label.setText(f'加载二维码失败: {str(e)}')
    
    def _on_qrcode_loaded(self, reply):
        """
        二维码图片加载完成的回调函数
        
        Args:
            reply: 网络请求的回复对象
        """
        from PySide6.QtNetwork import QNetworkReply
        
        if reply.error() == QNetworkReply.NetworkError.NoError:
            data = reply.readAll()
            pixmap = QPixmap()
            pixmap.loadFromData(data)
            if not pixmap.isNull():
                # 缩放图片到合适大小
                scaled_pixmap = pixmap.scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self.qrcode_label.setPixmap(scaled_pixmap)
            else:
                self.qrcode_label.setText('二维码图片格式错误')
        else:
            self.qrcode_label.setText(f'加载二维码失败: {reply.errorString()}')
        reply.deleteLater()


def check_updates_on_start(parent, local_version_file, remote_version_url, qrcode_url, config_file):
    """
    启动时检查更新
    
    使用QTimer.singleShot延迟2秒后执行更新检查，
    如果有更新则显示更新对话框。
    
    Args:
        parent (QWidget): 父窗口
        local_version_file (str): 本地版本文件路径
        remote_version_url (str): 远程版本信息URL
        qrcode_url (str): 二维码图片URL
        config_file (str): 配置文件路径
    """
    def _do_check():
        checker = UpdateChecker(local_version_file, remote_version_url, config_file)
        has_update, remote_version = checker.check_for_updates()
        if has_update:
            show_update_dialog(parent, qrcode_url, config_file, remote_version)
    
    QTimer.singleShot(2000, _do_check)


def show_update_dialog(parent, qrcode_url, config_file, remote_version):
    """
    显示更新对话框
    
    创建并显示UpdateDialog供用户选择是否查看更新。
    
    Args:
        parent (QWidget): 父窗口
        qrcode_url (str): 二维码图片URL
        config_file (str): 配置文件路径
        remote_version (str): 远程版本号
    """
    dialog = UpdateDialog(parent, qrcode_url, config_file, remote_version)
    dialog.exec()
