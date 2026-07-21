#!/usr/bin/env python3
"""
MCP Server 主模块

使用 FastMCP 创建 MCP Server 实例，并注册所有发票处理 Tools。
"""

import asyncio
import logging
import threading
from typing import List, Dict, Any, Optional

from mcp.server.fastmcp import FastMCP

from .config import (
    SERVER_NAME,
    SERVER_VERSION,
    DEFAULT_TRANSPORT,
    DEFAULT_PORT,
    DEFAULT_HOST,
    DEFAULT_CORS_ORIGINS,
    setup_logging,
)
from .tools import (
    handle_merge_invoices,
    handle_extract_invoice_info,
    handle_batch_extract_invoice_info,
    handle_batch_rename_invoices,
    handle_export_invoice_list,
    handle_export_invoice_list_from_paths,
    handle_get_supported_layouts,
    handle_get_supported_fields,
    handle_get_server_info,
)


# 创建 FastMCP 实例
mcp = FastMCP(SERVER_NAME)

# 模块级日志器
logger = logging.getLogger(__name__)


@mcp.tool()
def merge_invoices(pdf_paths: List[str], output_path: str,
                   layout: Dict[str, Any], mode: str = "普通") -> Dict[str, Any]:
    """
    MCP Tool：合并多个 PDF 发票为指定布局

    参数:
        pdf_paths: 待合并的 PDF 文件路径列表
        output_path: 合并后的输出文件路径
        layout: 布局配置字典，包含 orientation、rows、cols、rotate
        mode: 合并模式，可选 "普通" 或 "图像"，默认 "普通"

    返回值:
        Dict[str, Any]: 包含 success 和 message 的字典
    """
    return handle_merge_invoices(pdf_paths, output_path, layout, mode)


@mcp.tool()
def extract_invoice_info(pdf_path: str) -> Dict[str, Any]:
    """
    MCP Tool：提取单张发票的全部字段信息

    参数:
        pdf_path: PDF 文件路径

    返回值:
        Dict[str, Any]: 包含 success、info 和 message 的字典
    """
    return handle_extract_invoice_info(pdf_path)


@mcp.tool()
def batch_extract_invoice_info(pdf_paths: List[str]) -> Dict[str, Any]:
    """
    MCP Tool：批量提取多张发票的字段信息

    参数:
        pdf_paths: PDF 文件路径列表

    返回值:
        Dict[str, Any]: 包含 success、results 和 message 的字典
    """
    return handle_batch_extract_invoice_info(pdf_paths)


@mcp.tool()
def batch_rename_invoices(pdf_paths: List[str], rule: str, dry_run: bool = False) -> Dict[str, Any]:
    """
    MCP Tool：按规则批量重命名发票 PDF 文件

    参数:
        pdf_paths: 需要重命名的 PDF 文件路径列表
        rule: 重命名规则字符串，支持 {发票类型}、{开票日期} 等占位符
        dry_run: 是否为预览模式，默认 False；为 True 时不真正重命名文件

    返回值:
        Dict[str, Any]: 包含 success、renamed_count、failed_count、
                       unrecognized_files、renamed_map、dry_run 和 message 的字典
    """
    return handle_batch_rename_invoices(pdf_paths, rule, dry_run=dry_run)


@mcp.tool()
def export_invoice_list(pdf_infos: List[Dict[str, Any]], output_path: str,
                        duplicate_codes: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    MCP Tool：将发票信息列表导出为 Excel 文件

    参数:
        pdf_infos: 发票信息字典列表
        output_path: 输出 Excel 文件路径
        duplicate_codes: 重复发票号码列表，可选

    返回值:
        Dict[str, Any]: 包含 success、output_path 和 message 的字典
    """
    return handle_export_invoice_list(pdf_infos, output_path, duplicate_codes)


@mcp.tool()
def get_supported_layouts() -> Dict[str, Any]:
    """
    MCP Tool：获取支持的布局配置列表

    返回值:
        Dict[str, Any]: 包含 layouts 的字典
    """
    return handle_get_supported_layouts()


@mcp.tool()
def get_supported_fields() -> Dict[str, Any]:
    """
    MCP Tool：获取重命名规则中支持的字段列表

    返回值:
        Dict[str, Any]: 包含 fields 的字典
    """
    return handle_get_supported_fields()


@mcp.tool()
def export_invoice_list_from_paths(
    pdf_paths: List[str],
    output_path: str,
    duplicate_codes: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    MCP Tool：按 PDF 路径列表直接导出 Excel 文件

    参数:
        pdf_paths: PDF 文件路径列表
        output_path: 输出 Excel 文件路径
        duplicate_codes: 重复发票号码列表，可选

    返回值:
        Dict[str, Any]: 包含 success、output_path 和 message 的字典
    """
    return handle_export_invoice_list_from_paths(pdf_paths, output_path, duplicate_codes)


@mcp.tool()
def get_server_info() -> Dict[str, Any]:
    """
    MCP Tool：获取 MCP Server 元信息

    返回值:
        Dict[str, Any]: 包含 name、version 和 tools 列表的字典
    """
    return handle_get_server_info()


def run_server(
    transport: str = DEFAULT_TRANSPORT,
    port: int = DEFAULT_PORT,
    host: str = DEFAULT_HOST,
    cors_origins: Optional[List[str]] = None,
    shutdown_event: Optional[threading.Event] = None,
) -> None:
    """
    启动 MCP Server

    功能描述:
        使用 FastMCP 运行 MCP Server，支持 stdio 或 sse 传输方式。
        SSE 模式下支持自定义监听地址、CORS 来源以及优雅关闭。

    参数:
        transport: 传输方式，"stdio" 或 "sse"
        port: SSE 模式下的监听端口
        host: SSE 模式下的监听地址，默认 127.0.0.1
        cors_origins: SSE 模式下允许的 CORS 来源列表，默认 ["*"]
        shutdown_event: 用于通知 SSE 服务优雅关闭的线程事件
    """
    setup_logging()
    logger.info(
        "MCP Server 启动中: name=%s, version=%s, transport=%s",
        SERVER_NAME,
        SERVER_VERSION,
        transport,
    )

    if transport == "sse":
        mcp.settings.host = host
        mcp.settings.port = port

        import uvicorn
        from starlette.middleware.cors import CORSMiddleware

        starlette_app = mcp.sse_app()
        origins = cors_origins if cors_origins is not None else DEFAULT_CORS_ORIGINS
        if origins:
            starlette_app.add_middleware(
                CORSMiddleware,
                allow_origins=origins,
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )

        config = uvicorn.Config(
            starlette_app,
            host=host,
            port=port,
            log_level="info",
        )
        server = uvicorn.Server(config)

        watcher: Optional[threading.Thread] = None
        if shutdown_event is not None:
            def _watch_shutdown() -> None:
                """监听关闭事件并通知 uvicorn 停止服务"""
                shutdown_event.wait()
                server.should_exit = True

            watcher = threading.Thread(target=_watch_shutdown, daemon=True)
            watcher.start()

        try:
            asyncio.run(server.serve())
        finally:
            if watcher is not None:
                watcher.join(timeout=1)
        logger.info("MCP Server SSE 已停止")
    else:
        mcp.run(transport="stdio")
