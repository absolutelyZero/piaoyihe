#!/usr/bin/env python3
"""
发票PDF合并排版工具
主程序入口

支持两种启动模式：
1. 默认 GUI 模式：启动桌面应用程序
2. MCP Server 模式：通过 --mcp-server 参数启动，支持 stdio（命令行独立）
   或 sse（与 GUI 共存）传输方式
"""

import sys
import os
import argparse
import threading

# 将模块所在根目录加入 sys.path：
# - 开发环境：当前文件所在目录（code/）
# - PyInstaller 打包后：sys._MEIPASS（onedir 模式下为 _internal/ 目录）
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    base_path = sys._MEIPASS
else:
    base_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, base_path)

# 兼容 Windows AI 工具从外部目录调用的场景：
# 将 code/ 的父目录也加入 sys.path，确保 -m mcp_server 等方式也能正常工作
_parent = os.path.dirname(base_path)
if _parent not in sys.path:
    sys.path.insert(0, _parent)

# 懒加载 mcp_server.config，避免 PyInstaller 打包后模块未收集时启动崩溃
# 提供默认值兜底，确保 _parse_args 等函数能正常定义
_DEFAULT_HOST = "127.0.0.1"
_DEFAULT_CORS_ORIGINS = ["*"]
try:
    from mcp_server.config import DEFAULT_HOST, DEFAULT_CORS_ORIGINS
except ModuleNotFoundError:
    DEFAULT_HOST = _DEFAULT_HOST
    DEFAULT_CORS_ORIGINS = _DEFAULT_CORS_ORIGINS


def _parse_args(argv=None):
    """
    解析命令行参数

    功能描述:
        解析 GUI 和 MCP Server 两种模式所需的命令行参数。

    参数:
        argv: 命令行参数列表，默认使用 sys.argv

    返回值:
        argparse.Namespace: 解析后的参数命名空间
    """
    parser = argparse.ArgumentParser(
        prog="python code/main.py",
        description="票易合 - 发票PDF合并排版工具"
    )
    parser.add_argument(
        "--mcp-server",
        action="store_true",
        dest="mcp_server",
        help="启用 MCP Server 模式"
    )
    parser.add_argument(
        "--verify-imports",
        action="store_true",
        dest="verify_imports",
        help=argparse.SUPPRESS
    )
    parser.add_argument(
        "--transport",
        type=str,
        choices=["stdio", "sse"],
        default="stdio",
        help="MCP Server 传输方式，默认 stdio；GUI 共存模式下建议使用 sse"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="SSE 模式监听端口，默认 8765"
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
    return parser.parse_args(argv)


def _run_mcp_server_in_thread(
    transport: str,
    port: int,
    host: str,
    cors_origins: list,
    shutdown_event: threading.Event,
):
    """
    在后台线程中启动 MCP Server

    功能描述:
        用于 GUI 共存模式（sse），避免阻塞 Qt 主事件循环。

    参数:
        transport: 传输方式
        port: SSE 监听端口
        host: SSE 监听地址
        cors_origins: 允许的 CORS 来源列表
        shutdown_event: 用于通知 MCP Server 优雅关闭的线程事件
    """
    from mcp_server.server import run_server
    run_server(
        transport=transport,
        port=port,
        host=host,
        cors_origins=cors_origins,
        shutdown_event=shutdown_event,
    )


def _run_gui_mode(
    start_mcp_server: bool = False,
    transport: str = "stdio",
    port: int = 8765,
    host: str = DEFAULT_HOST,
    cors_origins = DEFAULT_CORS_ORIGINS,
) -> int:
    """
    运行 GUI 模式

    功能描述:
        初始化 PySide6 应用程序，创建主窗口，并启动事件循环。
        可选在后台线程启动 MCP Server（SSE 与 GUI 共存模式）。

    参数:
        start_mcp_server: 是否同时启动 MCP Server
        transport: MCP Server 传输方式
        port: SSE 监听端口
        host: SSE 监听地址
        cors_origins: 允许的 CORS 来源列表

    返回值:
        int: 应用程序退出码
    """
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtGui import QFont
    from ui.main_frame import MainWindow
    from core.update_checker import check_updates_on_start

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

    server_thread = None
    shutdown_event = None
    if start_mcp_server and transport == "sse":
        # GUI 共存模式：在后台线程启动 MCP Server
        shutdown_event = threading.Event()
        server_thread = threading.Thread(
            target=_run_mcp_server_in_thread,
            args=(transport, port, host, cors_origins, shutdown_event),
            daemon=True,
        )
        server_thread.start()
        app.aboutToQuit.connect(shutdown_event.set)

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
    exit_code = app.exec()

    if shutdown_event is not None:
        shutdown_event.set()
    if server_thread is not None:
        server_thread.join(timeout=2)

    return exit_code


def _run_mcp_server_mode(
    transport: str,
    port: int,
    host: str,
    cors_origins: list,
) -> int:
    """
    运行 MCP Server 模式

    功能描述:
        根据传输方式启动 MCP Server。stdio 模式下不启动 Qt；sse 模式下启动 GUI
        并在后台线程运行 MCP Server。

    参数:
        transport: 传输方式，"stdio" 或 "sse"
        port: SSE 监听端口
        host: SSE 监听地址
        cors_origins: 允许的 CORS 来源列表

    返回值:
        int: 程序退出码
    """
    if transport == "stdio":
        from mcp_server.server import run_server
        run_server(transport="stdio")
        return 0
    else:
        # GUI 共存模式：在后台线程启动 MCP Server，主线程运行 Qt 事件循环
        return _run_gui_mode(
            start_mcp_server=True,
            transport=transport,
            port=port,
            host=host,
            cors_origins=cors_origins,
        )


def main(argv=None):
    """
    应用程序主入口函数

    功能描述:
        根据命令行参数决定启动 GUI 模式或 MCP Server 模式。

    参数:
        argv: 命令行参数列表，默认使用 sys.argv

    返回值:
        int: 应用程序退出码
    """
    args = _parse_args(argv)

    if args.verify_imports:
        # 打包验证专用：确认 MCP Server 关键依赖可被导入
        import mcp.server.fastmcp
        import uvicorn
        import starlette
        import httpx
        print("mcp deps ok")
        return 0

    if args.mcp_server:
        return _run_mcp_server_mode(
            args.transport,
            args.port,
            args.host,
            args.cors_origins,
        )
    else:
        return _run_gui_mode()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        # 将未捕获异常写入日志文件，便于在 console=False 的打包版本中排查问题
        log_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'error.log'
        )
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(f"程序启动失败: {e}\n")
            import traceback
            traceback.print_exc(file=f)
        raise
