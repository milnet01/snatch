#!/usr/bin/env bash
# Build the self-contained Linux AppImage: dist/Snatch-x86_64.AppImage
#
# Run natively on Linux. The GitHub workflow calls this same script, so what
# runs here and what runs in CI cannot drift.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

APPIMAGETOOL_VERSION="${APPIMAGETOOL_VERSION:-continuous}"
ARCH="$(uname -m)"

[ "$(uname -s)" = "Linux" ] || { echo "build-linux.sh must run on Linux" >&2; exit 1; }

echo "=== 1/5 fetch bundled binaries ==="
scripts/fetch-binaries.sh

echo "=== 2/5 smoke-test platform_utils ==="
python3 scripts/verify_platform_utils.py

echo "=== 3/5 PyInstaller one-file build ==="
rm -rf build dist AppDir
pyinstaller pyinstaller.spec --clean --noconfirm
[ -f dist/snatch ] || { echo "dist/snatch not produced" >&2; exit 1; }

echo "=== 4/5 assemble AppDir ==="
mkdir -p AppDir/usr/bin AppDir/usr/share/applications AppDir/usr/share/icons/hicolor/256x256/apps
cp dist/snatch AppDir/usr/bin/snatch
chmod +x AppDir/usr/bin/snatch
cp icon.png AppDir/snatch.png
cp icon.png AppDir/usr/share/icons/hicolor/256x256/apps/snatch.png

# The desktop file inside an AppImage must NOT carry the absolute Exec/Path of
# the development checkout — the AppImage runs from wherever the user put it.
cat > AppDir/snatch.desktop <<'DESKTOP'
[Desktop Entry]
Type=Application
Name=Snatch
Comment=Download YouTube videos using yt-dlp
Exec=snatch
Icon=snatch
StartupWMClass=Snatch
Terminal=false
Categories=Network;AudioVideo;
DESKTOP
cp AppDir/snatch.desktop AppDir/usr/share/applications/snatch.desktop

cat > AppDir/AppRun <<'APPRUN'
#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/usr/bin/snatch" "$@"
APPRUN
chmod +x AppDir/AppRun

echo "=== 5/5 package AppImage ==="
tool="$(command -v appimagetool || true)"
if [ -z "$tool" ]; then
    tool="$PWD/appimagetool"
    if [ ! -x "$tool" ]; then
        curl --fail --location --silent --show-error --retry 3 --max-time 300 \
          -o "$tool" \
          "https://github.com/AppImage/appimagetool/releases/download/${APPIMAGETOOL_VERSION}/appimagetool-${ARCH}.AppImage"
        chmod +x "$tool"
    fi
fi

# CI containers have no FUSE, so appimagetool must unpack itself rather than
# mount. Harmless on a desktop that does have FUSE.
export APPIMAGE_EXTRACT_AND_RUN=1
export ARCH

# Fetch the type2 runtime ourselves and hand it over with --runtime-file.
# Left to itself appimagetool downloads this at package time, and that fetch
# hangs indefinitely with no output and no timeout — observed 2026-08-19,
# blocked in a futex on an open socket for eight minutes at 0% CPU. Doing it
# here means a network problem fails fast and visibly instead.
runtime="$PWD/.cache/runtime-${ARCH}"
mkdir -p .cache
if [ ! -s "$runtime" ]; then
    echo "    downloading AppImage runtime"
    curl --fail --location --silent --show-error --retry 3 --max-time 180 \
      -o "$runtime" \
      "https://github.com/AppImage/type2-runtime/releases/download/continuous/runtime-${ARCH}"
fi

# --no-appstream: the AppStream validator is a second network dependency and
# this AppDir ships no AppStream metadata for it to check.
"$tool" --no-appstream --runtime-file "$runtime" AppDir "dist/Snatch-${ARCH}.AppImage"

out="dist/Snatch-${ARCH}.AppImage"
[ -f "$out" ] || { echo "$out not produced" >&2; exit 1; }
chmod +x "$out"
echo "=== built $out ($(du -h "$out" | cut -f1)) ==="
