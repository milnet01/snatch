#!/usr/bin/env bash
# Build the self-contained Linux AppImage: dist/Snatch-x86_64.AppImage
#
# Run natively on Linux. The GitHub workflow calls this same script, so what
# runs here and what runs in CI cannot drift.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Both of these are PINNED and CHECKSUMMED, and both used to be neither.
#
# The type2 runtime becomes the first bytes of the AppImage every user runs,
# and appimagetool runs on the build host. Fetching either from a rolling
# `continuous` tag means whoever controls that repo can change what we ship
# and what we execute, without a commit here. The old cache test was
# `[ ! -s "$runtime" ]` -- non-emptiness -- so once a file landed it was
# trusted forever, whatever it was.
#
# To move a pin: change the version, run the build, and replace the digest
# with the one the mismatch message prints. Do not delete the check.
APPIMAGETOOL_VERSION="${APPIMAGETOOL_VERSION:-1.9.1}"
TYPE2_RUNTIME_VERSION="${TYPE2_RUNTIME_VERSION:-20251108}"
ARCH="$(uname -m)"

case "$ARCH" in
    x86_64)
        APPIMAGETOOL_SHA256="ed4ce84f0d9caff66f50bcca6ff6f35aae54ce8135408b3fa33abfc3cb384eb0"
        RUNTIME_SHA256="2fca8b443c92510f1483a883f60061ad09b46b978b2631c807cd873a47ec260d"
        ;;
    aarch64)
        APPIMAGETOOL_SHA256="f0837e7448a0c1e4e650a93bb3e85802546e60654ef287576f46c71c126a9158"
        RUNTIME_SHA256="00cbdfcf917cc6c0ff6d3347d59e0ca1f7f45a6df1a428a0d6d8a78664d87444"
        ;;
    *)
        echo "no recorded checksums for arch '$ARCH'" >&2
        echo "add them above rather than removing the verification" >&2
        exit 1
        ;;
esac

# Download to $2 from $1 and refuse anything whose SHA-256 is not $3.
# --proto/--proto-redir keep a redirect from leaving HTTPS, which curl's
# defaults permit; STANDARDS.md section 5.2 names those flags.
fetch_verified() {
    local url="$1" dest="$2" want="$3" got
    curl --fail --location --silent --show-error --retry 3 --max-time 300 \
         --proto '=https' --proto-redir '=https' -o "$dest.part" "$url"
    got="$(sha256sum "$dest.part" | cut -d' ' -f1)"
    if [ "$got" != "$want" ]; then
        rm -f "$dest.part"
        echo "checksum mismatch for $url" >&2
        echo "  expected $want" >&2
        echo "  got      $got" >&2
        exit 1
    fi
    mv "$dest.part" "$dest"
}

# True when $1 already exists with the SHA-256 $2 -- so the cache is keyed on
# CONTENT, not on the file merely being non-empty.
cached_ok() {
    [ -s "$1" ] && [ "$(sha256sum "$1" | cut -d' ' -f1)" = "$2" ]
}

[ "$(uname -s)" = "Linux" ] || { echo "build-linux.sh must run on Linux" >&2; exit 1; }

echo "=== 1/5 fetch bundled binaries ==="
scripts/fetch-binaries.sh

echo "=== 2/5 smoke-test platform_utils ==="
python3 scripts/verify_platform_utils.py --require-bundled

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
# A system appimagetool is deliberately NOT preferred any more. `command -v`
# picked up whatever version happened to be installed, which is the same
# unknown-provenance problem as an unpinned download and is invisible in the
# build log. Set SNATCH_APPIMAGETOOL to use a specific one on purpose.
tool="${SNATCH_APPIMAGETOOL:-$PWD/appimagetool}"
if [ -n "${SNATCH_APPIMAGETOOL:-}" ]; then
    echo "    using SNATCH_APPIMAGETOOL=$tool (unverified, caller's choice)"
elif ! cached_ok "$tool" "$APPIMAGETOOL_SHA256"; then
    echo "    downloading appimagetool ${APPIMAGETOOL_VERSION}"
    fetch_verified \
      "https://github.com/AppImage/appimagetool/releases/download/${APPIMAGETOOL_VERSION}/appimagetool-${ARCH}.AppImage" \
      "$tool" "$APPIMAGETOOL_SHA256"
fi
chmod +x "$tool"

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
if ! cached_ok "$runtime" "$RUNTIME_SHA256"; then
    echo "    downloading AppImage runtime ${TYPE2_RUNTIME_VERSION}"
    fetch_verified \
      "https://github.com/AppImage/type2-runtime/releases/download/${TYPE2_RUNTIME_VERSION}/runtime-${ARCH}" \
      "$runtime" "$RUNTIME_SHA256"
fi

# --no-appstream: the AppStream validator is a second network dependency and
# this AppDir ships no AppStream metadata for it to check.
"$tool" --no-appstream --runtime-file "$runtime" AppDir "dist/Snatch-${ARCH}.AppImage"

out="dist/Snatch-${ARCH}.AppImage"
[ -f "$out" ] || { echo "$out not produced" >&2; exit 1; }
chmod +x "$out"
echo "=== built $out ($(du -h "$out" | cut -f1)) ==="
