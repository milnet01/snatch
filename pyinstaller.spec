# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the Windows one-file build.

Invoked by .github/workflows/build-windows.yml after it downloads
yt-dlp.exe and ffmpeg.exe into the ./bin/ directory of the build checkout.
The .exe extracts everything to a temp dir at runtime; user data goes
next to the .exe itself via platform_utils.app_data_dir().
"""

import os
import sys

# ── Inputs ────────────────────────────────────────────────────────────
APP_NAME = "snatch"
ENTRY = "snatch.py"
ICON = "icon.png"  # PyInstaller converts PNG → .ico automatically on Windows.

# Bundled binaries are downloaded by the CI workflow into ./bin/ before
# this spec runs. If they're missing locally, the build still succeeds
# but produces a non-self-contained .exe that needs PATH-installed
# yt-dlp/ffmpeg — useful for dev/test, not for distribution.
BIN_DIR = "bin"
binaries = []
for name in ("yt-dlp.exe", "ffmpeg.exe"):
    path = os.path.join(BIN_DIR, name)
    if os.path.isfile(path):
        binaries.append((path, "bin"))

# Data files (icons, etc.) bundled into the .exe.
datas = [
    ("icon.png", "."),
    ("icon_48.png", "."),
    ("icon_64.png", "."),
]

# ── Analysis ──────────────────────────────────────────────────────────
a = Analysis(
    [ENTRY],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=[
        "tkinterdnd2",
        "PIL._tkinter_finder",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        # Trim unused stdlib heavyweights that PyInstaller pulls in
        # speculatively — saves ~5 MB.
        "test",
        "unittest",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,           # UPX often trips Windows Defender; not worth it.
    runtime_tmpdir=None,
    console=False,        # No console window — pure GUI.
    disable_windowed_traceback=False,
    icon="icon.png",
    version=None,         # Could embed a Windows version-info resource later.
)
