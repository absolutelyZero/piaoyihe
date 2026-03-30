# -*- mode: python ; coding: utf-8 -*-

import wx
import os

block_cipher = None

wx_path = os.path.dirname(wx.__file__)
pymupdf_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath('.'))))

a = Analysis(
    ['code\\main.py'],
    pathex=['d:\\minipro\\piaoyihe\\piaoyihe'],
    binaries=[
        (wx_path, 'wx'),
    ],
    datas=[
        ('code\\res\\logo3.png', 'res'),
        ('code\\res\\qrcode.jpg', 'res'),
    ],
    hiddenimports=['wx', 'fitz', 'PIL', 'multiprocessing'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib'],
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
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='code\\res\\logo3.png',
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
