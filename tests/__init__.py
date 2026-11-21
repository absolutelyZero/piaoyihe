"""测试包

导入时安装受限环境兼容补丁（临时目录/写入限制），
避免环境问题掩盖真实测试结果。
"""

try:
    from . import _env_patch  # noqa: F401
except Exception:  # pragma: no cover - 补丁本身不应导致测试无法导入
    pass
