#!/usr/bin/env bash
# Download the yt-dlp, ffmpeg and ffprobe binaries this platform needs into
# ./bin/, ready for PyInstaller to bundle. Shared by all three build scripts
# and by the GitHub workflow, so there is exactly one copy of these URLs.
#
# platform_utils._find_bundled_binary() looks for <_MEIPASS>/bin/<stem> (plus
# .exe on Windows), so the filenames written here are a contract with the app.
set -euo pipefail

# ── Pinned versions ───────────────────────────────────────────────────
# yt-dlp comes from the NIGHTLY channel, pinned to one tag.
#
# This is deliberate and was measured on 2026-08-19. YouTube playback through
# mpv failed on 4 of 5 sampled videos with the stable release -- 403 Forbidden
# on the DASH stream URLs -- and on 5 of 5 with the version pinned here
# before. The current STABLE release (2026.07.04) does NOT fix it. The nightly
# does: 5/5 play, with no other change. YouTube breaks yt-dlp faster than the
# stable channel ships, so a stable pin here means a player that does not
# play.
#
# Pinned to an exact nightly tag, so the build stays reproducible; bump it
# when playback or downloads start failing.
YTDLP_VERSION="${YTDLP_VERSION:-2026.08.18.122307}"
YTDLP_REPO="${YTDLP_REPO:-yt-dlp/yt-dlp-nightly-builds}"
# One source for all three platforms, so there is one pin to bump.
FFMPEG_STATIC_TAG="${FFMPEG_STATIC_TAG:-b6.1.1}"
# QuickJS is the JavaScript runtime yt-dlp needs to solve YouTube's nsig
# challenges. Without one, YouTube extraction is deprecated and some formats
# go missing. quickjs is ~2 MB against Deno's ~40 MB, and yt-dlp supports it
# directly; it is enabled explicitly because only deno is enabled by default.
QUICKJS_TAG="${QUICKJS_TAG:-v0.16.1}"
# mpv powers the in-app video player. It is NOT one binary like the others:
# the Windows build is an archive of mpv.exe plus a set of DLLs, so it is
# unpacked into bin/mpv/ as a directory. The release tag is pinned; the asset
# filename inside it carries a build hash and is resolved at fetch time.
MPV_WIN_TAG="${MPV_WIN_TAG:-20260814}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN_DIR="$REPO_ROOT/bin"

# ── Platform detection ────────────────────────────────────────────────
uname_s="$(uname -s)"
uname_m="$(uname -m)"
case "$uname_s" in
    Linux)
        exe_suffix=""
        ytdlp_asset="yt-dlp"
        case "$uname_m" in
            x86_64|amd64) ffmpeg_slug="linux-x64";   qjs_asset="qjs-linux-x86_64"  ;;
            aarch64|arm64) ffmpeg_slug="linux-arm64"; qjs_asset="qjs-linux-aarch64" ;;
            *) echo "unsupported Linux arch: $uname_m" >&2; exit 1 ;;
        esac
        ;;
    Darwin)
        exe_suffix=""
        ytdlp_asset="yt-dlp_macos"
        case "$uname_m" in
            arm64) ffmpeg_slug="darwin-arm64"; qjs_asset="qjs-darwin-arm64"  ;;
            x86_64) ffmpeg_slug="darwin-x64";  qjs_asset="qjs-darwin-x86_64" ;;
            *) echo "unsupported macOS arch: $uname_m" >&2; exit 1 ;;
        esac
        ;;
    MINGW*|MSYS*|CYGWIN*|Windows_NT)
        exe_suffix=".exe"
        ytdlp_asset="yt-dlp.exe"
        ffmpeg_slug="win32-x64"
        qjs_asset="qjs-windows-x86_64.exe"
        ;;
    *)
        echo "unsupported platform: $uname_s" >&2; exit 1 ;;
esac

echo "==> fetching binaries for $uname_s/$uname_m (ffmpeg: $ffmpeg_slug)"
mkdir -p "$BIN_DIR"

fetch() {
    local url="$1" dest="$2"
    if [ -f "$dest" ]; then
        echo "    cached: $(basename "$dest")"
        return
    fi
    echo "    downloading $(basename "$dest")"
    curl --fail --location --silent --show-error --retry 3 --retry-delay 2 \
         --max-time 300 -o "$dest.part" "$url"
    mv "$dest.part" "$dest"
    chmod +x "$dest"
}

fetch "https://github.com/${YTDLP_REPO}/releases/download/${YTDLP_VERSION}/${ytdlp_asset}" \
      "$BIN_DIR/yt-dlp${exe_suffix}"

# NOTE: ffmpeg-static names its assets WITHOUT a file extension on every
# platform — the Windows asset is "ffmpeg-win32-x64", not
# "ffmpeg-win32-x64.exe". So exe_suffix belongs on the DESTINATION filename
# (which platform_utils does expect to end in .exe) and never on the URL.
# Appending it to both 404'd the Windows build on 2026-08-19.
for stem in ffmpeg ffprobe; do
    fetch "https://github.com/eugeneware/ffmpeg-static/releases/download/${FFMPEG_STATIC_TAG}/${stem}-${ffmpeg_slug}" \
          "$BIN_DIR/${stem}${exe_suffix}"
done

# QuickJS ships one bare binary per platform; rename it to a stable "qjs"
# so platform_utils._find_bundled_binary() has a single name to look for.
fetch "https://github.com/quickjs-ng/quickjs/releases/download/${QUICKJS_TAG}/${qjs_asset}" \
      "$BIN_DIR/qjs${exe_suffix}"

# mpv, Windows only for now. Linux and macOS keep using a system mpv; see
# SNAT-0013 for why those two are harder (nested AppImage / .app bundle).
if [ "$exe_suffix" = ".exe" ]; then
    if [ ! -x "$BIN_DIR/mpv/mpv.exe" ]; then
        echo "    resolving mpv asset for tag ${MPV_WIN_TAG}"
        mpv_url="$(curl --fail --location --silent --show-error --max-time 60 \
            "https://api.github.com/repos/shinchiro/mpv-winbuild-cmake/releases/tags/${MPV_WIN_TAG}" \
            | python -c "
import json,sys
d = json.load(sys.stdin)
for a in d['assets']:
    n = a['name']
    if n.startswith('mpv-x86_64-') and '-v3-' not in n and not n.startswith('mpv-dev'):
        print(a['browser_download_url']); break
else:
    sys.exit('no mpv asset found in tag')
")"
        [ -n "$mpv_url" ] || { echo "could not resolve mpv asset" >&2; exit 1; }
        echo "    downloading $(basename "$mpv_url")"
        curl --fail --location --silent --show-error --retry 3 --max-time 600 \
             -o "$BIN_DIR/mpv.7z" "$mpv_url"
        mkdir -p "$BIN_DIR/mpv"
        # 7z ships with the GitHub windows runner and with Git for Windows.
        7z x -y -o"$BIN_DIR/mpv" "$BIN_DIR/mpv.7z" > /dev/null
        rm -f "$BIN_DIR/mpv.7z"
    else
        echo "    cached: mpv/mpv.exe"
    fi
    [ -x "$BIN_DIR/mpv/mpv.exe" ] || { echo "mpv.exe not produced" >&2; exit 1; }
fi

echo "==> bin/ contents:"
ls -lh "$BIN_DIR"

# Prove each binary actually executes on this host, rather than trusting that a
# 200 response meant we got the right architecture. Windows binaries under a
# Linux checkout obviously cannot be run, so this only fires natively.
if [ "$exe_suffix" = "" ] || [ "$uname_s" != "Linux" ]; then
    for stem in yt-dlp ffmpeg ffprobe qjs; do
        b="$BIN_DIR/${stem}${exe_suffix}"
        printf "    %-10s " "$stem"
        if "$b" -version >/dev/null 2>&1 || "$b" --version >/dev/null 2>&1; then
            echo "runs OK"
        else
            echo "FAILED to execute" >&2
            exit 1
        fi
    done
fi
