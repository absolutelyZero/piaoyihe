#!/usr/bin/env python3
"""
更新检查模块
"""

import json
import os
import requests
import threading
import wx

class UpdateChecker:
    """
    软件更新检查器
    """
    def __init__(self, local_version_file, remote_version_url, config_file=None):
        """
        初始化更新检查器
        参数:
            local_version_file: 本地版本文件路径
            remote_version_url: 远程版本文件URL
            config_file: 配置文件路径
        """
        self.local_version_file = local_version_file
        self.remote_version_url = remote_version_url
        self.config_file = config_file
        self.current_version = self._get_local_version()
    
    def _get_local_version(self):
        """
        获取本地版本号
        返回:
            str: 本地版本号
        """
        try:
            if os.path.exists(self.local_version_file):
                with open(self.local_version_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('version', '0.0.0')
            return '0.0.0'
        except Exception as e:
            print(f"获取本地版本失败: {e}")
            return '0.0.0'
    
    def _get_ignored_version(self):
        """
        获取忽略的版本号
        返回:
            str: 忽略的版本号
        """
        try:
            if self.config_file and os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    return config.get('ignored_version', '0.0.0')
            return '0.0.0'
        except Exception as e:
            print(f"获取忽略版本失败: {e}")
            return '0.0.0'
    
    def _set_ignored_version(self, version):
        """
        设置忽略的版本号
        参数:
            version: 要忽略的版本号
        """
        try:
            if self.config_file and os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                config['ignored_version'] = version
                
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"设置忽略版本失败: {e}")
    
    def check_for_updates(self, ignore_ignored_version=False):
        """
        检查是否有更新
        参数:
            ignore_ignored_version: 是否忽略已忽略的版本（用于用户主动点击检查时）
        返回:
            tuple: (是否有更新, 远程版本号)
        """
        try:
            # 发送请求获取远程版本信息
            response = requests.get(self.remote_version_url, timeout=5)
            response.raise_for_status()
            remote_data = response.json()
            remote_version = remote_data.get('version', '0.0.0')
            
            # 比较版本号
            if self._is_version_newer(remote_version):
                if ignore_ignored_version:
                    # 用户主动点击检查，忽略已忽略的版本
                    return True, remote_version
                else:
                    # 启动时检查，考虑已忽略的版本
                    ignored_version = self._get_ignored_version()
                    if not self._is_version_newer(ignored_version) or remote_version != ignored_version:
                        return True, remote_version
            return False, remote_version
        except Exception as e:
            print(f"检查更新失败: {e}")
            return False, '0.0.0'
    
    def _is_version_newer(self, version):
        """
        比较版本号
        参数:
            version: 要比较的版本号
        返回:
            bool: 如果版本更新则返回True
        """
        try:
            current_parts = list(map(int, self.current_version.split(".")))
            new_parts = list(map(int, version.split(".")))
            
            for i in range(max(len(current_parts), len(new_parts))):
                current = current_parts[i] if i < len(current_parts) else 0
                new = new_parts[i] if i < len(new_parts) else 0
                
                if new > current:
                    return True
                elif new < current:
                    return False
            return False
        except Exception:
            return False

class UpdateDialog(wx.Dialog):
    """
    更新提示对话框
    """
    def __init__(self, parent, qrcode_url, config_file, remote_version):
        """
        初始化更新对话框
        参数:
            parent: 父窗口
            qrcode_url: 二维码图片URL
            config_file: 配置文件路径
            remote_version: 远程版本号
        """
        super().__init__(parent, title="发现新版本", size=(300, 200))
        
        self.config_file = config_file
        self.remote_version = remote_version
        
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)
        
        # 提示信息
        message = wx.StaticText(panel, label=f"发现新版本 v{remote_version}，是否查看更新内容？")
        vbox.Add(message, 0, wx.ALL | wx.CENTER, 20)
        
        # 按钮
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        update_btn = wx.Button(panel, label="查看更新")
        ignore_btn = wx.Button(panel, label="忽略当前版本")
        
        self.Bind(wx.EVT_BUTTON, lambda e: self._show_qrcode(qrcode_url), update_btn)
        self.Bind(wx.EVT_BUTTON, self._ignore_version, ignore_btn)
        
        hbox.Add(update_btn, 0, wx.ALL, 5)
        hbox.Add(ignore_btn, 0, wx.ALL, 5)
        
        vbox.Add(hbox, 0, wx.CENTER, 10)
        panel.SetSizer(vbox)
        self.CenterOnParent()
    
    def _show_qrcode(self, qrcode_url):
        """
        显示二维码对话框
        参数:
            qrcode_url: 二维码图片URL
        """
        dialog = QRCodeDialog(self, qrcode_url)
        dialog.ShowModal()
        dialog.Destroy()
        self.Close()
    
    def _ignore_version(self, event):
        """
        忽略当前版本
        """
        try:
            if self.config_file and os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                config['ignored_version'] = self.remote_version
                
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"设置忽略版本失败: {e}")
        finally:
            self.Close()

class QRCodeDialog(wx.Dialog):
    """
    二维码显示对话框
    """
    def __init__(self, parent, qrcode_url):
        """
        初始化二维码对话框
        参数:
            parent: 父窗口
            qrcode_url: 二维码图片URL
        """
        super().__init__(parent, title="更新内容", size=(400, 450))
        
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)
        
        # 提示信息
        message = wx.StaticText(panel, label="请扫码查看更新内容和更新方法")
        message.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        vbox.Add(message, 0, wx.ALL | wx.CENTER, 20)
        
        # 二维码图片
        try:
            # 下载二维码图片
            response = requests.get(qrcode_url, timeout=10)
            response.raise_for_status()
            
            # 创建临时文件保存图片
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
                f.write(response.content)
                temp_file = f.name
            
            # 显示图片
            qrcode_img = wx.Image(temp_file, wx.BITMAP_TYPE_PNG)
            qrcode_img = qrcode_img.Rescale(300, 300)
            qrcode_bmp = wx.Bitmap(qrcode_img)
            qrcode_static = wx.StaticBitmap(panel, -1, qrcode_bmp)
            vbox.Add(qrcode_static, 0, wx.ALL | wx.CENTER, 10)
            
            # 删除临时文件
            os.unlink(temp_file)
        except Exception as e:
            print(f"加载二维码失败: {e}")
            error_text = wx.StaticText(panel, label="二维码加载失败")
            vbox.Add(error_text, 0, wx.ALL | wx.CENTER, 100)
        
        # 关闭按钮
        close_button = wx.Button(panel, label="关闭")
        close_button.Bind(wx.EVT_BUTTON, lambda e: self.Close())
        vbox.Add(close_button, 0, wx.ALL | wx.CENTER, 20)
        
        panel.SetSizer(vbox)
        self.CenterOnParent()

def check_updates_on_start(app, local_version_file, remote_version_url, qrcode_url, config_file=None):
    """
    启动时检查更新
    参数:
        app: wx.App实例
        local_version_file: 本地版本文件路径
        remote_version_url: 远程版本文件URL
        qrcode_url: 二维码图片URL
        config_file: 配置文件路径
    """
    def check():
        checker = UpdateChecker(local_version_file, remote_version_url, config_file)
        has_update, remote_version = checker.check_for_updates()
        
        if has_update:
            wx.CallAfter(show_update_dialog, app.GetTopWindow(), qrcode_url, config_file, remote_version)
    
    # 在后台线程中检查，避免阻塞UI
    thread = threading.Thread(target=check)
    thread.daemon = True
    thread.start()

def show_update_dialog(parent, qrcode_url, config_file, remote_version):
    """
    显示更新对话框
    参数:
        parent: 父窗口
        qrcode_url: 二维码图片URL
        config_file: 配置文件路径
        remote_version: 远程版本号
    """
    dialog = UpdateDialog(parent, qrcode_url, config_file, remote_version)
    dialog.ShowModal()
    dialog.Destroy()
