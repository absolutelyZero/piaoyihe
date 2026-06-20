# -*- mode: python ; coding: utf-8 -*-
"""
票易合 - Windows 打包配置
优化版本：剔除未使用的依赖包，减小打包体积
"""

import os
import sys

block_cipher = None

# 分析项目依赖
a = Analysis(
    ['code\\main.py'],
    pathex=['d:\\minipro\\piaoyihe\\piaoyihe'],
    binaries=[],
    datas=[
        ('code\\res\\logo3.png', 'res'),
        ('code\\res\\logo3.ico', 'res'),
        ('code\\res\\qrcode.jpg', 'res'),
        ('code\\res\\icons\\刷新_refresh.svg', 'res\\icons'),
        ('code\\res\\icons\\笔记_notes.svg', 'res\\icons'),
        ('code\\res\\icons\\加_plus.svg', 'res\\icons'),
        ('code\\res\\icons\\减_minus.svg', 'res\\icons'),
        ('code\\res\\icons\\关闭_close.svg', 'res\\icons'),
        ('code\\res\\icons\\箭头上_arrow-up.svg', 'res\\icons'),
        ('code\\res\\icons\\箭头下_arrow-down.svg', 'res\\icons'),
        ('code\\res\\icons\\铅笔_pencil.svg', 'res\\icons'),        
        ('code\\res\\icons\\下载_download-four.svg', 'res\\icons'),        
        ('code\\res\\icons\\预览-打开_preview-open.svg', 'res\\icons'),
        ('code\\version.json', 'code'),
    ],
    # 隐藏导入：包含实际使用的模块及其依赖
    hiddenimports=[
        'fitz',                    # PyMuPDF - PDF处理核心
        'PIL.Image',               # Pillow - 图像处理（用于PDF旋转）
        'PIL.ImageRotate',         # PIL旋转功能
        'PIL.PngImagePlugin',      # PNG图像支持
        'PIL.JpegImagePlugin',     # JPEG图像支持
        'PIL.BmpImagePlugin',      # BMP图像支持
        'PIL.GifImagePlugin',      # GIF图像支持
        'shiboken6',               # PySide6底层绑定库
        'shiboken6.Shiboken',      # Shiboken核心
        'PySide6.QtCore',          # Qt核心模块
        'PySide6.QtGui',           # Qt GUI模块
        'PySide6.QtWidgets',       # Qt控件模块
        'PySide6.QtNetwork',       # Qt网络模块（用于更新检查）
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # 排除未使用的依赖包（谨慎排除，避免排除标准库和必要模块）
    excludes=[
        # GUI框架（未使用）
        'tkinter',
        'matplotlib',
        'wx',
        'wxPython',
        'PyQt5',
        'PyQt6',
        'PyQt4',

        # 数据库（未使用）
        'sqlalchemy',
        'pymongo',
        'psycopg2',
        'mysql',

        # 科学计算（未使用）
        'numpy',
        'scipy',
        'pandas',
        'sklearn',
        'scikit-learn',

        # 网络请求（项目使用标准库urllib）
        'requests',
        'urllib3',
        'certifi',
        'chardet',
        'idna',
        'charset_normalizer',

        # Web框架（未使用）
        'flask',
        'django',
        'tornado',
        'fastapi',

        # 测试相关（未使用）
        'pytest',

        # 开发工具（未使用）
        'setuptools',
        'pkg_resources',
        'distutils',
        'pip',
        'wheel',

        # 其他未使用的库
        'jinja2',
        'markupsafe',
        'werkzeug',
        'click',
        'itsdangerous',
        'blinker',
        'colorama',
        'pygments',
        'docutils',
        'sphinx',

        # Pillow中未使用的图像格式插件
        'PIL.ImageQt',
        'PIL.PdfImagePlugin',
        'PIL.TiffImagePlugin',
        'PIL.WebPImagePlugin',
        'PIL.Jpeg2KImagePlugin',
        'PIL.MpegImagePlugin',
        'PIL.FpxImagePlugin',
        'PIL.FliImagePlugin',
        'PIL.ImImagePlugin',
        'PIL.PcxImagePlugin',
        'PIL.PsdImagePlugin',
        'PIL.SgiImagePlugin',
        'PIL.TgaImagePlugin',
        'PIL.XpmImagePlugin',
        'PIL.XbmImagePlugin',
        'PIL.ImtImagePlugin',
        'PIL.IptcImagePlugin',
        'PIL.McIdasImagePlugin',
        'PIL.MicImagePlugin',
        'PIL.MspImagePlugin',
        'PIL.PalmImagePlugin',
        'PIL.PcdImagePlugin',
        'PIL.PixarImagePlugin',
        'PIL.PpmImagePlugin',
        'PIL.SunImagePlugin',
        'PIL.WmfImagePlugin',
        'PIL.XVThumbImagePlugin',

        # 异步框架（未使用）
        'aiohttp',

        # 加密库（未使用）
        'cryptography',

        # XML/HTML解析库（未使用）
        'lxml',
        'html5lib',
        'beautifulsoup4',
        'bs4',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)


# 排除 Windows API-MS-Win 和 UCRT DLL，依赖系统已安装的运行时
excluded_dlls = [
    'api-ms-win-core-console-l1-1-0.dll',
    'api-ms-win-core-datetime-l1-1-0.dll',
    'api-ms-win-core-debug-l1-1-0.dll',
    'api-ms-win-core-errorhandling-l1-1-0.dll',
    'api-ms-win-core-file-l1-1-0.dll',
    'api-ms-win-core-file-l1-2-0.dll',
    'api-ms-win-core-file-l2-1-0.dll',
    'api-ms-win-core-handle-l1-1-0.dll',
    'api-ms-win-core-heap-l1-1-0.dll',
    'api-ms-win-core-interlocked-l1-1-0.dll',
    'api-ms-win-core-libraryloader-l1-1-0.dll',
    'api-ms-win-core-localization-l1-2-0.dll',
    'api-ms-win-core-memory-l1-1-0.dll',
    'api-ms-win-core-namedpipe-l1-1-0.dll',
    'api-ms-win-core-processenvironment-l1-1-0.dll',
    'api-ms-win-core-processthreads-l1-1-0.dll',
    'api-ms-win-core-processthreads-l1-1-1.dll',
    'api-ms-win-core-profile-l1-1-0.dll',
    'api-ms-win-core-rtlsupport-l1-1-0.dll',
    'api-ms-win-core-string-l1-1-0.dll',
    'api-ms-win-core-synch-l1-1-0.dll',
    'api-ms-win-core-synch-l1-2-0.dll',
    'api-ms-win-core-sysinfo-l1-1-0.dll',
    'api-ms-win-core-timezone-l1-1-0.dll',
    'api-ms-win-core-util-l1-1-0.dll',
    'api-ms-win-crt-conio-l1-1-0.dll',
    'api-ms-win-crt-convert-l1-1-0.dll',
    'api-ms-win-crt-environment-l1-1-0.dll',
    'api-ms-win-crt-filesystem-l1-1-0.dll',
    'api-ms-win-crt-heap-l1-1-0.dll',
    'api-ms-win-crt-locale-l1-1-0.dll',
    'api-ms-win-crt-math-l1-1-0.dll',
    'api-ms-win-crt-multibyte-l1-1-0.dll',
    'api-ms-win-crt-private-l1-1-0.dll',
    'api-ms-win-crt-process-l1-1-0.dll',
    'api-ms-win-crt-runtime-l1-1-0.dll',
    'api-ms-win-crt-stdio-l1-1-0.dll',
    'api-ms-win-crt-string-l1-1-0.dll',
    'api-ms-win-crt-time-l1-1-0.dll',
    'api-ms-win-crt-utility-l1-1-0.dll',
    'ucrtbase.dll',
]

a.binaries = [x for x in a.binaries if x[0] not in excluded_dlls]
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
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='code\\res\\logo3.ico',
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
