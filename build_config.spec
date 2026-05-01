# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller build configuration for CoinStrike

Usage:
    pyinstaller build_config.spec

This creates a single executable with all assets bundled.
Compatible with PyArmor for additional code obfuscation.
"""

block_cipher = None

# Collect all Python source files
python_files = [
    'main.py',
    'player.py',
    'enemy.py',
    'weapon.py',
    'world.py',
    'platforms.py',
    'coins.py',
    'health.py',
    'camera.py',
    'combo.py',
    'mission.py',
    'shop.py',
    'powerups.py',
    'rocks.py',
    'difficulty.py',
    'item_box.py',
    'menu.py',
    'settings.py',
    'security.py',
    'utils.py',
]

# Collect all asset files
asset_files = [
    ('assets', 'assets'),
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=asset_files,
    hiddenimports=[],
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
    name='CoinStrike',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Set to False to hide console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/game-cover.png',  # Optional: add .ico file for Windows
)
