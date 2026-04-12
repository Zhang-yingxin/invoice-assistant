# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'PyQt6.QtSvg',
        'fitz',
        'pdfplumber',
        'pdfminer',
        'pdfminer.six',
        'PIL',
        'PIL.Image',
        'keyring.backends',
        'keyring.backends.macOS',
        'keyring.backends.Windows',
    ],
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
    upx=False,
    console=False,
    icon='assets/ia.ico',
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
    name='IA.app',
    icon='assets/ia.icns',
    bundle_identifier='com.invoice.assistant',
    info_plist={
        'CFBundleName': 'IA',
        'CFBundleDisplayName': 'IA',
        'CFBundleVersion': '1.0.1',
        'CFBundleShortVersionString': '1.0.1',
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '10.14',
    },
)
