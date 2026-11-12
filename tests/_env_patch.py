#!/usr/bin/env python3
"""
测试环境兼容补丁

背景：
    部分受限沙箱（如 DSH workspace-write 模式）会拒绝 tempfile.TemporaryDirectory
    在清理阶段对临时目录执行 chmod/rmdir，导致与业务逻辑无关的 PermissionError。
    这些失败会掩盖真实缺陷。

处理：
    在导入任何测试模块前，把 tempfile.TemporaryDirectory 替换为一个
    基于 os.makedirs + uuid 的实现，退出时用 shutil.rmtree(ignore_errors=True)
    清理（清理失败不影响断言）。

用法：
    在 tests/__init__.py 中导入本模块即自动生效；也可单独 import。
"""

import os
import shutil
import tempfile
import uuid


# 可写的临时根目录：优先工作区内的 .testtmp，其次系统临时目录
def _pick_root():
    candidates = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.testtmp'),
        os.path.join(tempfile.gettempdir(), 'piaoyihe_tests'),
    ]
    for path in candidates:
        try:
            os.makedirs(path, exist_ok=True)
            probe = os.path.join(path, '.writable_probe')
            with open(probe, 'w', encoding='utf-8') as f:
                f.write('ok')
            os.remove(probe)
            return os.path.abspath(path)
        except OSError:
            continue
    return None


_TMP_ROOT = _pick_root()


class SafeTemporaryDirectory:
    """
    tempfile.TemporaryDirectory 的受限环境友好替代

    接口兼容（name 属性 / 上下文管理器 / cleanup 方法），
    清理失败时静默忽略，避免掩盖真实测试结果。
    """

    def __init__(self, suffix='', prefix='tmp', dir=None, **_kwargs):
        self._finalizer_done = False
        root = dir or _TMP_ROOT or tempfile.gettempdir()
        os.makedirs(root, exist_ok=True)
        self.name = os.path.join(
            root, f'{prefix}{uuid.uuid4().hex[:12]}{suffix}'
        )
        os.makedirs(self.name, exist_ok=True)

    def cleanup(self):
        if self._finalizer_done:
            return
        self._finalizer_done = True
        shutil.rmtree(self.name, ignore_errors=True)

    def __enter__(self):
        return self.name

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
        return False


def install():
    """
    安装补丁

    仅当当前 TemporaryDirectory 在受限环境下不可用时才替换，
    避免在正常环境下改变标准库行为。
    同时把 mkdtemp 重定向到可写根目录（受限环境下系统临时目录不可写）。
    """
    if _TMP_ROOT is None:
        return False

    # 探测标准实现是否可用
    try:
        with tempfile.TemporaryDirectory() as probe_dir:
            probe_file = os.path.join(probe_dir, 'probe.txt')
            with open(probe_file, 'w', encoding='utf-8') as f:
                f.write('ok')
    except (OSError, PermissionError):
        tempfile.TemporaryDirectory = SafeTemporaryDirectory

        # mkdtemp 默认落在系统临时目录；受限环境下改为可写根目录
        _orig_mkdtemp = tempfile.mkdtemp

        def _safe_mkdtemp(suffix=None, prefix=None, dir=None):
            target_dir = dir or _TMP_ROOT
            os.makedirs(target_dir, exist_ok=True)
            name = (prefix or 'tmp') + uuid.uuid4().hex[:12] + (suffix or '')
            path = os.path.join(target_dir, name)
            os.makedirs(path, exist_ok=True)
            return path

        tempfile.mkdtemp = _safe_mkdtemp
        return True

    return False


PATCHED = install()
