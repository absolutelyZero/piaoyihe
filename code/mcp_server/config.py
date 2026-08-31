#!/usr/bin/env python3
"""
MCP Server 配置模块

提供票易合 MCP Server 的名称、版本、传输方式等常量配置。
"""

import os
import json
import logging
import sys


# 日志级别环境变量名
LOG_LEVEL_ENV = "PYYH_LOG_LEVEL"


def setup_logging() -> None:
    """
    配置 MCP Server 日志

    功能描述:
        初始化 Python logging，默认级别 INFO，输出到 stderr。
        可通过环境变量 PYYH_LOG_LEVEL 覆盖级别。

    返回值:
        无
    """
    level_name = os.environ.get(LOG_LEVEL_ENV, "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
        force=True,
    )


def _load_version() -> str:
    """
    从 version.json 加载当前版本号

    返回值:
        str: 版本号字符串，读取失败返回 "0.2.0"
    """
    version_file = os.path.join(os.path.dirname(__file__), '..', 'version.json')
    try:
        with open(version_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('version', '0.2.0')
    except Exception:
        return '0.2.0'


# MCP Server 名称
SERVER_NAME = "piaoyihe"

# MCP Server 版本，与票易合版本保持一致
SERVER_VERSION = _load_version()

# 默认传输方式：stdio 与 Claude Desktop 兼容性最好
DEFAULT_TRANSPORT = "stdio"

# SSE 传输默认端口
DEFAULT_PORT = 8765

# SSE 默认监听地址
DEFAULT_HOST = "127.0.0.1"

# 默认允许的 CORS 来源（本地服务可放宽为 *）
DEFAULT_CORS_ORIGINS = ["*"]
