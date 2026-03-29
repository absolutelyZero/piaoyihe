# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['code\\main.py'],
    pathex=['D:\\path\\to\\invoiceTool'],  # 替换为您的项目路径
    binaries=[],
    datas=[
        ('code\\res\\logo3.png', 'res'),
    ],
    hiddenimports=['wx', 'fitz'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='票易合',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 隐藏控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='code\\res\\logo3.png',  # 设置Windows可执行文件的图标
)