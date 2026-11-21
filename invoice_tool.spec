# -*- mode: python ; coding: utf-8 -*-

import sys
import os
import json

from PyInstaller.utils.hooks import collect_data_files

# ofd2pdf 内置的 ofd-cli 可执行文件（OFD 渲染依赖）
# macOS 官方未提供平台 wheel，缺失时打包不影响其余功能（OFD 能力降级）
try:
    import ofd2pdf  # noqa: F401
    ofd2pdf_datas = collect_data_files('ofd2pdf')
    ofd2pdf_hiddenimports = ['ofd2pdf', 'ofd2pdf.ofd_cli', 'ofd2pdf.converter']
except Exception:
    # macOS 官方无 wheel：OFD 能力降级，不打包 ofd2pdf 相关模块
    ofd2pdf_datas = []
    ofd2pdf_hiddenimports = []

try:
    with open('code/version.json', encoding='utf-8') as _vf:
        _APP_VERSION = json.load(_vf).get('version', '0.0.0')
except Exception:
    _APP_VERSION = '0.0.0'

block_cipher = None

a = Analysis(
    ['code/main.py'],
    # pathex 由 scripts/patch_spec.py 在打包前写入当前仓库的绝对路径
    # （ui/core 是 code/ 下的顶层包，缺少 code 目录会打出 No module named 'ui'）
    pathex=[r'/Users/xieyonggao/Documents/self/minipro/invoiceTool', r'/Users/xieyonggao/Documents/self/minipro/invoiceTool/code'],
    binaries=[],
    datas=[
        ('code/res/logo3.png', 'res'),
        ('code/res/qrcode.jpg', 'res'),
        # 设计稿同款字体（SIL OFL 1.1）：随程序分发，QSS / 财务列不再依赖系统字体
        ('code/res/fonts/Inter-VF.ttf', 'res/fonts'),
        ('code/res/fonts/NotoSansSC-VF.ttf', 'res/fonts'),
        ('code/res/fonts/OFL-1.1.txt', 'res/fonts'),
        ('code/version.json', 'code'),
        ('code/config.json', 'code'),
        # 图标整目录打包：代码按文件名引用，避免新增图标漏打包
        ('code/res/icons', 'res/icons'),
        *ofd2pdf_datas,
    ],
    hiddenimports=[
        # PySide6 核心模块
        'PySide6',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'PySide6.QtNetwork',
        # PyMuPDF
        'fitz',
        # Pillow
        'PIL',
        'PIL.Image',
        'PIL.ImageQt',
        # 其他依赖
        'json',
        'os',
        'sys',
        'tempfile',
        'urllib',
        're',
        'math',
        'io',
        'time',

        # MCP Server 相关模块（显式列出，避免 collect_submodules 静默失败）
        'mcp',
        'mcp.server.fastmcp',
        'mcp.server.sse',
        'mcp.server.stdio',
        'mcp_server',
        'mcp_server.config',
        'mcp_server.server',
        'mcp_server.tools',
        'mcp_server.__main__',
        'core',
        'core.pdf_handler',
        'core.update_checker',
        'core.invoice_extractors',
        'core.invoice_extractors.base',
        'core.invoice_extractors.factory',
        'core.invoice_extractors.common_invoice',
        'core.invoice_extractors.train_ticket',
        'core.invoice_extractors.flight_ticket',
        'core.invoice_extractors.vehicle_invoice',
        'core.invoice_extractors.taxi_invoice',
        'core.invoice_extractors.fixed_amount_invoice',
        'core.invoice_extractors.toll_invoice',
        'core.invoice_service',
        'core.ofd_converter',

        # OFD 渲染依赖（ofd2pdf 及其内置 ofd-cli），仅平台可用时打包
        *ofd2pdf_hiddenimports,

        # GUI 界面模块（namespace 包无法被自动收集，必须显式列出）
        'ui',
        'ui.main_frame',
        'ui.file_list',
        'ui.rename_dialog',
        'ui.merge_worker',
        'ui.file_load_worker',
        'ui.theme',

        # SSE 传输依赖
        'uvicorn',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.lifespan.on',
        'click',                  # uvicorn CLI 依赖
        'starlette',
        'starlette.middleware.cors',
        'anyio',

        # MCP 底层 HTTP 依赖
        'httpx',
        'httpx._transports.default',
        'httpx_sse',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter', 'sqlite3', 'test', 'distutils', 'setuptools',
        'numpy', 'scipy', 'matplotlib', 'pandas',
        'bs4', 'lxml', 'PIL.PdfImagePlugin',
        # 排除不必要的 Qt 模块以减小体积
        'PySide6.Qt3DCore',
        'PySide6.Qt3DRender',
        'PySide6.Qt3DInput',
        'PySide6.Qt3DLogic',
        'PySide6.Qt3DAnimation',
        'PySide6.Qt3DExtras',
        'PySide6.QtCharts',
        'PySide6.QtDataVisualization',
        'PySide6.QtQuick',
        'PySide6.QtQuickWidgets',
        'PySide6.QtQml',
        'PySide6.QtSql',
        'PySide6.QtTest',
        'PySide6.QtXml',
        'PySide6.QtXmlPatterns',
        'PySide6.QtMultimedia',
        'PySide6.QtMultimediaWidgets',
        'PySide6.QtOpenGL',
        'PySide6.QtPositioning',
        'PySide6.QtLocation',
        'PySide6.QtSensors',
        'PySide6.QtSerialPort',
        'PySide6.QtWebChannel',
        'PySide6.QtWebEngine',
        'PySide6.QtWebEngineCore',
        'PySide6.QtWebEngineWidgets',
        'PySide6.QtWebSockets',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='票易合',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 隐藏控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=True,  # macOS 需要启用 argv 模拟
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='票易合',
)

app = BUNDLE(
    coll,
    name='票易合.app',
    icon='code/res/logo3.png',
    bundle_identifier='com.invoice.piaoyihe',
    info_plist={
        'CFBundleName': '票易合',
        'CFBundleDisplayName': '票易合 - 发票合并工具',
        'CFBundleShortVersionString': _APP_VERSION,
        'CFBundleVersion': _APP_VERSION,
        'NSHighResolutionCapable': True,
        'LSBackgroundOnly': False,
        'LSUIElement': False,
    },
)
