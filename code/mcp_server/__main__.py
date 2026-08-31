#!/usr/bin/env python3
"""
MCP Server 命令行入口

支持通过以下方式启动：
    python -m code.mcp_server
    python -m code.mcp_server --transport sse --port 8765
"""

import argparse
import sys
import os

# 将 code 目录加入模块搜索路径，支持直接以模块方式运行
script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

from mcp_server.server import run_server
from mcp_server.config import DEFAULT_TRANSPORT, DEFAULT_PORT, DEFAULT_HOST, DEFAULT_CORS_ORIGINS


def parse_args() -> argparse.Namespace:
    """
    解析命令行参数

    返回值:
        argparse.Namespace: 解析后的参数命名空间
    """
    parser = argparse.ArgumentParser(
        prog="python -m code.mcp_server",
        description="票易合 MCP Server 命令行入口"
    )
    parser.add_argument(
        "--transport",
        type=str,
        choices=["stdio", "sse"],
        default=DEFAULT_TRANSPORT,
        help=f"MCP 传输方式，默认 {DEFAULT_TRANSPORT}"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"SSE 模式监听端口，默认 {DEFAULT_PORT}"
    )
    parser.add_argument(
        "--host",
        type=str,
        default=DEFAULT_HOST,
        help=f"SSE 模式监听地址，默认 {DEFAULT_HOST}"
    )
    parser.add_argument(
        "--cors-origins",
        type=str,
        nargs="*",
        default=DEFAULT_CORS_ORIGINS,
        help=f"SSE 模式允许的 CORS 来源列表，默认 {' '.join(DEFAULT_CORS_ORIGINS)}"
    )
    return parser.parse_args()


def main() -> int:
    """
    命令行主入口

    返回值:
        int: 程序退出码，0 表示正常
    """
    args = parse_args()
    run_server(
        transport=args.transport,
        port=args.port,
        host=args.host,
        cors_origins=args.cors_origins,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
