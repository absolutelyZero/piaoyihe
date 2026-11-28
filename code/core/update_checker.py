# -*- coding: utf-8 -*-
"""
更新检查模块

提供软件版本更新检查功能，包括：
- 从 GitHub Release 的稳定地址读取版本清单
- 本地版本与远程版本比较、忽略指定版本
- 更新提示对话框（当前版本 + 最新版本与 Release 地址 + 公众号二维码）
- 手动检查时先显示弹窗、再在后台线程拉取结果
"""

import json
import os
import re
import sys
from dataclasses import dataclass
from urllib import request

from PySide6.QtCore import QThread, QTimer, Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
)
from ui.tokens import (
    build_stylesheet, numeric_font, FONT_SIZE, apply_numeric_text_fonts, _res_dir
)


# 版本清单的稳定下载地址：随 Release 一同发布，地址不随版本号变化
VERSION_MANIFEST_URL = (
    "https://github.com/absolutelyZero/piaoyihe/releases/latest/download/version.json"
)

# 项目固定的公众号二维码：不随版本更新，随应用打包分发
QRCODE_FILENAME = "qrcode.jpg"
QRCODE_DISPLAY_SIZE = 160

# 内容区第二行预留高度：状态文案切换时不改变窗口尺寸
LATEST_LINE_MIN_HEIGHT = 44

# 版本号形如 1、1.2、1.2.3，只允许点分数字
_VERSION_PATTERN = re.compile(r"^[0-9]+([.][0-9]+)*$")

# 检查过程中的状态文案
TEXT_CHECKING = '正在检查最新版本中…'
TEXT_CHECK_FAILED = '检查最新版本失败'


@dataclass(frozen=True)
class UpdateInfo:
    """一次成功检查到的新版本信息。"""

    version: str        # 远程版本号，如 "0.1.17"
    release_url: str    # Release 页面地址；清单未提供时为空串
    tag: str            # 原始标签，如 "v0.1.17"；清单未提供时为空串


def read_local_version(local_version_file):
    """
    读取本地版本号

    Args:
        local_version_file (str): 本地版本文件路径

    Returns:
        str: 本地版本号，读取失败返回 '0.0.0'
    """
    try:
        # 尝试多个可能的路径（开发环境和打包环境）
        possible_paths = [local_version_file]

        # PyInstaller打包后的路径
        if hasattr(sys, '_MEIPASS'):
            possible_paths.append(os.path.join(sys._MEIPASS, 'version.json'))
            possible_paths.append(os.path.join(sys._MEIPASS, 'code', 'version.json'))

        # 当前工作目录
        possible_paths.append(os.path.join(os.getcwd(), 'version.json'))
        possible_paths.append(os.path.join(os.getcwd(), 'code', 'version.json'))

        # 可执行文件所在目录
        if getattr(sys, 'frozen', False):
            exe_dir = os.path.dirname(sys.executable)
            possible_paths.append(os.path.join(exe_dir, 'version.json'))
            possible_paths.append(os.path.join(exe_dir, 'code', 'version.json'))

        # 尝试所有可能的路径
        for path in possible_paths:
            if path and os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('version', '0.0.0')

        return '0.0.0'
    except Exception:
        return '0.0.0'


class UpdateChecker:
    """
    版本更新检查器类

    用于检查软件是否有新版本可用，支持版本号比较和忽略版本功能。
    """

    def __init__(self, local_version_file, config_file, remote_version_url=VERSION_MANIFEST_URL):
        """
        初始化更新检查器

        Args:
            local_version_file (str): 本地版本文件路径
            config_file (str): 配置文件路径
            remote_version_url (str): 版本清单地址，默认指向 GitHub Release 稳定地址
        """
        self.local_version_file = local_version_file
        self.config_file = config_file
        self.remote_version_url = remote_version_url
        # 最近一次检查失败的原因；成功时为 None
        self.last_error = None

    def _get_local_version(self):
        """
        从本地版本文件读取版本号

        Returns:
            str: 本地版本号，如果读取失败返回'0.0.0'
        """
        return read_local_version(self.local_version_file)

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

    @staticmethod
    def _is_version_greater_than(version1, version2):
        """
        比较版本号，返回version1 > version2

        逐段按数字比较，段数不同时短的一方补 0；任一侧含非数字段时返回 False。

        Args:
            version1 (str): 第一个版本号
            version2 (str): 第二个版本号

        Returns:
            bool: version1是否大于version2
        """
        try:
            v1_parts = [int(x) for x in str(version1).split('.')]
            v2_parts = [int(x) for x in str(version2).split('.')]

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

    def _fetch_manifest(self):
        """
        读取远程版本清单

        Returns:
            dict: 解析后的清单内容

        Raises:
            ValueError: 响应不是合法 JSON 对象，或缺少合法 version 字段
            Exception: 网络层面的异常（超时、无法连接等）
        """
        with request.urlopen(self.remote_version_url, timeout=10) as response:
            raw = response.read().decode('utf-8')

        try:
            data = json.loads(raw)
        except Exception as exc:
            raise ValueError(f"版本清单不是合法 JSON: {exc}") from exc

        if not isinstance(data, dict):
            raise ValueError("版本清单格式错误：期望 JSON 对象")

        version = str(data.get('version', '')).strip()
        if not _VERSION_PATTERN.match(version):
            raise ValueError(f"版本清单中的 version 字段无效: {version!r}")

        return data

    def check_for_updates(self, ignore_ignored_version=False):
        """
        检查是否有可用更新

        网络异常、响应格式异常等失败情形不抛出，统一返回 None，
        失败原因记录在 self.last_error 中，供调用方决定是否提示用户。

        Args:
            ignore_ignored_version (bool): 是否忽略已忽略的版本，默认为False

        Returns:
            UpdateInfo | None: 有新版本时返回版本信息，无更新或检查失败返回 None
        """
        self.last_error = None
        try:
            remote_data = self._fetch_manifest()
            remote_version = str(remote_data.get('version', '')).strip()
            release_url = str(remote_data.get('release_url', '') or '').strip()
            tag = str(remote_data.get('tag', '') or '').strip()

            current_version = self._get_local_version()

            print(f"当前版本: {current_version}, 远程版本: {remote_version}, 忽略版本: {self._get_ignored_version()}")

            # 如果远程版本 > 当前版本
            if self._is_version_greater_than(remote_version, current_version):
                if ignore_ignored_version:
                    print("用户主动检查，显示更新对话框")
                    return UpdateInfo(remote_version, release_url, tag)

                ignored_version = self._get_ignored_version()
                # 如果远程版本 > 已忽略版本
                if self._is_version_greater_than(remote_version, ignored_version):
                    print(f"远程版本 {remote_version} > 忽略版本 {ignored_version}，显示更新对话框")
                    return UpdateInfo(remote_version, release_url, tag)

                print(f"远程版本 {remote_version} <= 忽略版本 {ignored_version}，跳过弹窗")
                return None

            print("当前版本已是最新")
            return None
        except Exception as e:
            self.last_error = str(e)
            print(f"检查更新失败: {e}")
            return None


class UpdateCheckWorker(QThread):
    """
    后台执行一次版本清单检查

    手动检查时弹窗先显示，本线程在后台拉取清单，避免界面出现空窗期。
    成功时发出 checked(UpdateInfo)，无更新时发出 checked(None)，
    失败时发出 failed(原因)，不再发出 checked。
    """

    checked = Signal(object)
    failed = Signal(str)

    def __init__(self, local_version_file, config_file, parent=None):
        super().__init__(parent)
        self.local_version_file = local_version_file
        self.config_file = config_file

    def run(self):
        try:
            checker = UpdateChecker(self.local_version_file, self.config_file)
            update_info = checker.check_for_updates(ignore_ignored_version=True)
        except Exception as e:
            self.failed.emit(str(e))
            return

        if update_info is None and checker.last_error:
            self.failed.emit(checker.last_error)
            return

        self.checked.emit(update_info)


class UpdateDialog(QDialog):
    """
    检查更新对话框

    构造时即可显示：第一行展示当前版本，第二行展示最新版本与 Release 地址。
    最新版本信息在检查完成后通过 set_update_info / set_check_failed 回填，
    因此弹窗的出现不依赖网络请求。页脚提供「忽略此版本」与「稍后」两个操作。
    """

    def __init__(self, parent, current_version, config_file):
        """
        初始化检查更新对话框

        Args:
            parent (QWidget): 父窗口
            current_version (str): 当前应用版本号
            config_file (str): 配置文件路径
        """
        super().__init__(parent)
        self.current_version = str(current_version or '0.0.0')
        self.config_file = config_file
        self.update_info = None
        self.remote_version = ''
        self.release_url = ''
        # 弹窗关闭后到达的检查结果直接丢弃，不再回填、不再二次弹窗
        self._discard_result = False
        self._update_checker = UpdateChecker('', config_file)
        self._init_ui()

    def _init_ui(self):
        """创建界面：统一标题栏 + 两行内容区 + 页脚两个操作。"""
        self.setWindowTitle('检查更新')
        self.setModal(True)
        self.setMinimumWidth(420)
        self.setStyleSheet(build_stylesheet())
        apply_numeric_text_fonts(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 统一标题栏
        header = QFrame()
        header.setObjectName('dialogHeader')
        header_box = QHBoxLayout(header)
        header_box.setContentsMargins(12, 10, 12, 10)
        title = QLabel('检查更新')
        title.setObjectName('sectionLabel')
        header_box.addWidget(title)
        header_box.addStretch(1)
        layout.addWidget(header)

        # 内容区第一行：当前版本（本地读取，立即渲染）
        self.current_label = QLabel(f"当前版本 v{self.current_version}")
        self.current_label.setObjectName('monoLabel')
        self.current_label.setFont(numeric_font(FONT_SIZE['body']))
        layout.addWidget(self.current_label)

        # 内容区第二行：最新版本与地址，初始为「检查中」
        self.latest_label = QLabel(TEXT_CHECKING)
        self.latest_label.setWordWrap(True)
        self.latest_label.setMinimumHeight(LATEST_LINE_MIN_HEIGHT)
        self.latest_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )
        layout.addWidget(self.latest_label)

        # 内容区第二行的地址部分（成功后显示为可点击超链接）
        self.release_label = QLabel()
        self.release_label.setWordWrap(True)
        self.release_label.setObjectName('monoLabel')
        self.release_label.hide()
        layout.addWidget(self.release_label)

        # 内容区：公众号二维码（本地固定资源，离线可用）
        qrcode_tip = QLabel('无法访问 GitHub？扫描下方公众号二维码获取更新方式')
        qrcode_tip.setWordWrap(True)
        layout.addWidget(qrcode_tip)

        self.qrcode_label = QLabel()
        self.qrcode_label.setObjectName('qrcodeImage')
        self.qrcode_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.qrcode_label.setMinimumSize(QRCODE_DISPLAY_SIZE, QRCODE_DISPLAY_SIZE)
        layout.addWidget(self.qrcode_label)
        self._load_qrcode()

        # 统一页脚操作区：只保留稍后与忽略此版本
        footer = QFrame()
        footer.setObjectName('dialogFooter')
        button_layout = QHBoxLayout(footer)
        button_layout.setContentsMargins(12, 10, 12, 10)
        button_layout.addStretch(1)

        self.later_button = QPushButton('稍后')
        self.later_button.setObjectName('secondaryButton')
        self.later_button.clicked.connect(self.close)
        button_layout.addWidget(self.later_button)

        self.ignore_button = QPushButton('忽略此版本')
        self.ignore_button.setObjectName('secondaryButton')
        self.ignore_button.clicked.connect(self._ignore_version)
        button_layout.addWidget(self.ignore_button)

        layout.addWidget(footer)

    def set_update_info(self, update_info):
        """
        回填检查成功的结果

        Args:
            update_info (UpdateInfo): 检查到的版本信息
        """
        self.update_info = update_info
        self.remote_version = update_info.version
        self.release_url = update_info.release_url

        if not UpdateChecker._is_version_greater_than(
            update_info.version, self.current_version
        ):
            self.set_no_update()
            return

        self.latest_label.setText(f"最新版本 v{update_info.version}")
        if self.release_url:
            self.release_label.setText(
                f'<a href="{self.release_url}">{self.release_url}</a>'
            )
            self.release_label.setOpenExternalLinks(True)
            self.release_label.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextBrowserInteraction
            )
        else:
            self.release_label.setText('本次更新未提供发布页地址，请扫码获取更新方式')
        self.release_label.show()

    def set_no_update(self):
        """回填检查成功但没有新版本的结果。"""
        self.latest_label.setText('当前已是最新版本')
        self.release_label.clear()
        self.release_label.hide()

    def set_check_failed(self):
        """回填检查失败的结果：只在弹窗内提示，不额外弹消息框。"""
        self.latest_label.setText(TEXT_CHECK_FAILED)
        self.release_label.clear()
        self.release_label.hide()

    def _on_worker_checked(self, update_info):
        """后台检查成功：弹窗已关闭则丢弃结果。"""
        if self._discard_result:
            return
        if update_info is None:
            self.set_no_update()
        else:
            self.set_update_info(update_info)

    def _on_worker_failed(self, message):
        """后台检查失败：弹窗已关闭则丢弃结果。"""
        if self._discard_result:
            return
        print(f"检查更新失败: {message}")
        self.set_check_failed()

    def closeEvent(self, event):
        """关闭后到达的结果一律丢弃。"""
        self._discard_result = True
        super().closeEvent(event)

    def _qrcode_path(self):
        """返回公众号二维码的本地路径（随程序分发的资源）。"""
        return os.path.join(_res_dir(), QRCODE_FILENAME)

    def _load_qrcode(self):
        """
        加载本地公众号二维码

        二维码是项目固定资源，不联网获取；资源缺失时降级为文字提示。
        """
        pixmap = QPixmap(self._qrcode_path())
        if pixmap.isNull():
            self.qrcode_label.setText('二维码资源缺失，请通过公众号获取更新方式')
            return
        scaled = pixmap.scaled(
            QRCODE_DISPLAY_SIZE,
            QRCODE_DISPLAY_SIZE,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.qrcode_label.setPixmap(scaled)

    def _ignore_version(self):
        """
        忽略当前版本

        调用_update_checker._set_ignored_version保存忽略版本，关闭对话框
        """
        if not self.remote_version:
            self.close()
            return
        self._update_checker._set_ignored_version(self.remote_version)
        self.close()


def open_update_dialog(parent, local_version_file, config_file):
    """
    手动检查更新：先显示弹窗，再在后台拉取版本清单

    Args:
        parent (QWidget): 父窗口
        local_version_file (str): 本地版本文件路径
        config_file (str): 配置文件路径

    Returns:
        UpdateDialog: 已显示的弹窗（检查结果稍后回填）
    """
    dialog = UpdateDialog(parent, read_local_version(local_version_file), config_file)
    worker = UpdateCheckWorker(local_version_file, config_file, dialog)
    worker.checked.connect(dialog._on_worker_checked)
    worker.failed.connect(dialog._on_worker_failed)
    # 保持引用，避免线程对象被回收
    dialog._worker = worker
    worker.start()
    dialog.open()
    return dialog


def check_updates_on_start(parent, local_version_file, config_file):
    """
    启动时检查更新

    使用QTimer.singleShot延迟2秒后执行更新检查，
    如果有更新则显示更新对话框；任何失败都静默结束，不打扰启动。

    Args:
        parent (QWidget): 父窗口
        local_version_file (str): 本地版本文件路径
        config_file (str): 配置文件路径
    """
    def _do_check():
        try:
            checker = UpdateChecker(local_version_file, config_file)
            update_info = checker.check_for_updates()
            if update_info:
                show_update_dialog(parent, update_info, config_file, local_version_file)
        except Exception as e:
            print(f"启动检查更新失败: {e}")

    QTimer.singleShot(2000, _do_check)


def show_update_dialog(parent, update_info, config_file, local_version_file=None):
    """
    显示已带结果的更新对话框（启动自动检查使用）

    Args:
        parent (QWidget): 父窗口
        update_info (UpdateInfo): 检查到的版本信息
        config_file (str): 配置文件路径
        local_version_file (str): 本地版本文件路径，用于展示当前版本
    """
    current_version = read_local_version(local_version_file) if local_version_file else '0.0.0'
    dialog = UpdateDialog(parent, current_version, config_file)
    dialog.set_update_info(update_info)
    dialog.exec()
