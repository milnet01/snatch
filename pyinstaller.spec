# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the self-contained Windows, Linux and macOS builds.

Invoked by scripts/build-linux.sh, build-windows.sh and build-macos.sh, each of
which runs scripts/fetch-binaries.sh first to download yt-dlp, ffmpeg and ffprobe
into the ./bin/ directory of the build checkout. .github/workflows/ci.yml calls
those scripts; it does not invoke this spec directly. One spec serves all
three platforms; the differences are the binary file extensions, one file on
Windows against a directory elsewhere, and the macOS .app bundle at the bottom.

Where user data lives is NOT decided here — platform_utils.app_data_dir()
owns that, and it differs per platform (next to the .exe on Windows,
~/Library/Application Support on macOS, XDG data dir under an AppImage).
"""

import os
import sys

# ── Inputs ────────────────────────────────────────────────────────────
APP_NAME = "snatch"
ENTRY = "snatch.py"
ICON_PNG = "icon.png"

IS_WINDOWS = sys.platform == "win32"
IS_MACOS = sys.platform == "darwin"
EXE_SUFFIX = ".exe" if IS_WINDOWS else ""

# Bundled binaries are downloaded by the CI workflow into ./bin/ before this
# spec runs. If they're missing locally the build still succeeds, but produces
# a non-self-contained app that needs PATH-installed yt-dlp/ffmpeg — useful for
# dev/test, not for distribution. platform_utils._find_bundled_binary() looks
# for exactly these names under <_MEIPASS>/bin/.
BIN_DIR = "bin"
binaries = []
missing = []
# Keep this list in step with scripts/fetch-binaries.sh — a binary fetched
# there but missing here is silently left out of the build. "qjs" is the
# QuickJS JavaScript runtime yt-dlp needs for YouTube.
for stem in ("yt-dlp", "ffmpeg", "ffprobe", "qjs"):
    path = os.path.join(BIN_DIR, stem + EXE_SUFFIX)
    if os.path.isfile(path):
        binaries.append((path, "bin"))
    else:
        missing.append(path)
if missing:
    print(f"[spec] WARNING: not bundling {', '.join(missing)} — "
          f"the build will fall back to PATH at runtime.")

# mpv is a DIRECTORY, not a single binary: the Windows build is mpv.exe plus a
# set of DLLs that must sit beside it. Everything under bin/mpv/ is bundled to
# bin/mpv/ so the layout survives into the frozen app. Absent on platforms
# where fetch-binaries.sh does not fetch it, which is fine — the app falls back
# to a system mpv, and to opening a browser if there is none.
MPV_DIR = os.path.join(BIN_DIR, "mpv")
if os.path.isdir(MPV_DIR):
    mpv_files = 0
    for entry in sorted(os.listdir(MPV_DIR)):
        full = os.path.join(MPV_DIR, entry)
        if os.path.isfile(full):
            binaries.append((full, "bin/mpv"))
            mpv_files += 1
    print(f"[spec] bundling mpv: {mpv_files} files from {MPV_DIR}")
else:
    print("[spec] no bin/mpv/ — in-app player will need a system mpv")

# Data files (icons, etc.) bundled into the app.
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

# One file on Windows, a directory elsewhere (SNAT-0026). A one-file build
# unpacks its whole archive to a temp directory on every launch. That buys a
# single portable snatch.exe on Windows, which is the point there. An
# AppImage and a macOS .app are already single packages that run in place,
# so one-file inside them only adds that unpack to every start.
ONE_FILE = IS_WINDOWS

EXE_OPTIONS = dict(
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,           # UPX often trips Windows Defender; not worth it.
    console=False,        # No console window — pure GUI.
    disable_windowed_traceback=False,
    icon=ICON_PNG,
)

if ONE_FILE:
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        runtime_tmpdir=None,
        version=None,     # Could embed a Windows version-info resource later.
        **EXE_OPTIONS,
    )
    app_target = exe
else:
    # dist/snatch/: the launcher, with everything else under _internal/.
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True, **EXE_OPTIONS)
    app_target = COLLECT(
        exe, a.binaries, a.zipfiles, a.datas,
        strip=False, upx=False, name=APP_NAME,
    )

# ── macOS .app bundle ─────────────────────────────────────────────────
# Only meaningful on darwin; the workflow wraps this in a .dmg. The bundle is
# unsigned and un-notarised, so Gatekeeper blocks a first double-click —
# README documents the right-click → Open workaround.
if IS_MACOS:
    app = BUNDLE(
        app_target,
        name="Snatch.app",
        icon=ICON_PNG,
        bundle_identifier="io.github.milnet01.snatch",
        info_plist={
            "CFBundleName": "Snatch",
            "CFBundleDisplayName": "Snatch",
            "CFBundleShortVersionString": "1.2.0",
            "CFBundleVersion": "1.2.0",
            "NSHighResolutionCapable": True,
            # Tk apps must not be treated as background-only.
            "LSBackgroundOnly": False,
        },
    )
