# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['PyQt6.QtSvg'],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='invoice-assistant',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='invoice-assistant',
)

# macOS .app bundle
app = BUNDLE(
    coll,
    name='发票识别助手.app',
    bundle_identifier='com.invoice.assistant',
    info_plist={
        'CFBundleName': '发票识别助手',
        'CFBundleDisplayName': '发票识别助手',
        'CFBundleVersion': '1.0.1',
        'CFBundleShortVersionString': '1.0.1',
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '10.14',
    },
)
