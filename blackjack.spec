# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller specification file for Blackjack.
Configured for reproducible standalone directory builds (--onedir) suitable for itch.io distribution.
"""

from pathlib import Path

block_cipher = None

# Base directory for relative asset resolution
base_dir = Path.cwd()

datas = [
    (str(base_dir / "cards"), "cards"),
    (str(base_dir / "audio"), "audio"),
    (str(base_dir / "assets"), "assets"),
]

hiddenimports = [
    "pygame",
    "pygame.mixer",
    "pygame._sdl2",
    "pygame._sdl2.audio",
    "tkinter",
]

a = Analysis(
    ["blackjack.py"],
    pathex=[str(base_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["test", "tests", "unittest", "pytest", "numpy", "pandas"],
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
    name="Blackjack",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(base_dir / "assets" / "icon.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Blackjack-Windows",
)
