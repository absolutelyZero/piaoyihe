# -*- mode: python ; coding: utf-8 -*-

import sys
import os

block_cipher = None

a = Analysis(
    ['code/main.py'],
    pathex=['/Users/xieyonggao/Documents/self/minipro/invoiceTool', '/Users/xieyonggao/Documents/self/minipro/invoiceTool/code'],
    binaries=[],
    datas=[
        ('code/res/logo3.png', 'res'),
        ('code/res/qrcode.jpg', 'res'),
        ('code/version.json', 'code'),
        ('code/config.json', 'code'),
        ('code/res/icons/刷新_refresh.svg', 'res/icons'),
        ('code/res/icons/笔记_notes.svg', 'res/icons'),
        ('code/res/icons/加_plus.svg', 'res/icons'),
        ('code/res/icons/减_minus.svg', 'res/icons'),
        ('code/res/icons/关闭_close.svg', 'res/icons'),
        ('code/res/icons/箭头上_arrow-up.svg', 'res/icons'),
        ('code/res/icons/箭头下_arrow-down.svg', 'res/icons'),
        ('code/res/icons/铅笔_pencil.svg', 'res/icons'),        
        ('code/res/icons/下载_download-four.svg', 'res/icons'),        
        ('code/res/icons/预览-打开_preview-open.svg', 'res/icons')
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
        'fitz.fitz',
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
        'core.rename_engine',

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
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleVersion': '1.0.0',
        'NSHighResolutionCapable': True,
        'LSBackgroundOnly': False,
        'LSUIElement': False,
    },
)
