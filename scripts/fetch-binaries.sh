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
# Pinned to an exact nightly tag, so a build records exactly what it
# shipped. scripts/update-ytdlp-pin.sh re-resolves it to the newest nightly
# and is run before building a release: the app offers the user an update
# only when the latest is newer than the copy in use, so a release that
# bundles anything older asks the user to download on first launch.
YTDLP_VERSION="${YTDLP_VERSION:-2026.08.30.232658}"
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

# ── Expected SHA-256 of every asset (SNAT-0031) ───────────────────────
# HTTPS proves the bytes came from github.com unaltered in transit. It says
# nothing about whether the asset behind a pinned TAG is still the artifact
# that was reviewed: a GitHub release asset can be replaced in place, and an
# account compromise upstream would reach every Snatch user through our own
# release. Pinning the tag does not pin the CONTENT; this does.
#
# Captured 2026-09-02 from the GitHub API's own `digest` field for each asset,
# spot-checked against a real download (qjs-linux-x86_64 matched exactly).
#
# BUMPING A PIN MEANS UPDATING A DIGEST. That is the point -- it makes an
# upstream content change visible instead of automatic. To refresh one:
#   gh api repos/<owner>/<repo>/releases/tags/<tag> \
#     --jq '.assets[] | select(.name=="<asset>") | .digest'
digest_for() {
    case "$1" in
        # yt-dlp ${YTDLP_VERSION}
        yt-dlp)                 echo 3f1b267b4488f3aed3731a9e84a44011ca5569901868532e10ee11fd07d69707 ;;
        yt-dlp_macos)           echo 868c2133b7968a7cfb6daccaad15eaee908077d12d16a58633ddafc7f2e97688 ;;
        yt-dlp.exe)             echo a3a504c66e91f6474cef0be83b16aedfb7b42b9400a962242d0d433e98f67a70 ;;
        # ffmpeg-static ${FFMPEG_STATIC_TAG}
        ffmpeg-linux-x64)       echo e7e7fb30477f717e6f55f9180a70386c62677ef8a4d4d1a5d948f4098aa3eb99 ;;
        ffprobe-linux-x64)      echo 4f231a1960d83e403d08f7971e271707bec278a9ae18e21b8b5b03186668450d ;;
        ffmpeg-linux-arm64)     echo 6bb182d0d75d23028db82e9e4f723ca69b853d055698486e6984ddb2c06fb8ce ;;
        ffprobe-linux-arm64)    echo d17ae9b4c297d48e2521ba14e417bb0537c6ff77c584cdbcd6bb0d8d0307a2e8 ;;
        ffmpeg-darwin-arm64)    echo a90e3db6a3fd35f6074b013f948b1aa45b31c6375489d39e572bea3f18336584 ;;
        ffprobe-darwin-arm64)   echo bb2db6f5d8cef919da12fbf592119a987202a8c060a886f3cab091f9cab90b64 ;;
        ffmpeg-darwin-x64)      echo ebdddc936f61e14049a2d4b549a412b8a40deeff6540e58a9f2a2da9e6b18894 ;;
        ffprobe-darwin-x64)     echo fa3add0ce901f7241abe0dfc0155d958fc834aca3f8ce61f87cc712ae669c1e0 ;;
        ffmpeg-win32-x64)       echo 04e1307997530f9cf2fe35cba2ca7e8875ca91da02f89d6c7243df819c94ad00 ;;
        ffprobe-win32-x64)      echo 3a7e2dc003dc2cd1472827e4c7c4f056ae1ae0ae7c5bbc580c99b49827351ba4 ;;
        # quickjs ${QUICKJS_TAG}
        qjs-linux-x86_64)       echo aae0d428c88bdd30fb490f54e616ebd4009ec279cc2a16ecebf0c3e17f7e76e7 ;;
        qjs-linux-aarch64)      echo c1635453aa60a78ebc7f05b2b559e0e9e9eb7d55b4dfc4a6e71a07d9d10b8a89 ;;
        qjs-darwin-arm64)       echo 9a24e7435036906c098d539daf47bcc8e7e8ad2f3aa084a0bce9313c6c3527e0 ;;
        qjs-darwin-x86_64)      echo 5982a1ebb20e1a9bf6162bafd29d445823616084cfeddee8881f8d69d6e0fd74 ;;
        qjs-windows-x86_64.exe) echo 55a1b69cd4fdb6b0d3f8fdd910d0e89519f5330e408462084140c7b3b964fdae ;;
        # mpv ${MPV_WIN_TAG}. The asset NAME carries a build hash and is
        # resolved from the API at fetch time, so the digest is what pins it.
        mpv-x86_64-20260814-git-7b8915bc1d.7z)
                                echo 1bf3b029da2c98e605e00e85f21ee3142f22a1dcc4ceb5c827b5c51e36e390f9 ;;
        *) return 1 ;;
    esac
}

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

# Cache stamps. The cache used to be keyed on the DESTINATION FILENAME, which
# carries no version -- so bumping a pin above and re-running silently reused
# the old binary while printing "cached", and a maintainer verifying a bump
# tested the version they were replacing. CI never saw it: a fresh checkout
# has no bin/, so this only ever failed where nobody was watching.
#
# Each fetch now records the URL it satisfied and re-fetches when that URL
# changes. Keyed on the URL rather than on the version variable, so a repo or
# asset-name change invalidates it too.
STAMP_DIR="$BIN_DIR/.stamps"
mkdir -p "$STAMP_DIR"

stamp_path() { printf '%s/%s.url' "$STAMP_DIR" "$(basename "$1")"; }

# True when $1 exists AND was fetched from $2.
stamp_matches() {
    local dest="$1" url="$2" stamp
    stamp="$(stamp_path "$dest")"
    [ -e "$dest" ] && [ -f "$stamp" ] && [ "$(cat "$stamp")" = "$url" ]
}

# True when $1 already exists with the SHA-256 $2 -- the cache is keyed on
# CONTENT, so a tampered or truncated cached file is re-fetched rather than
# trusted because a stamp file happens to agree.
cached_ok() {
    [ -s "$1" ] && [ "$(sha256sum "$1" | cut -d' ' -f1)" = "$2" ]
}

fetch() {
    local url="$1" dest="$2" want got asset
    asset="$(basename "$url")"

    # An asset with no recorded digest is a hard stop, never a skipped check.
    # Adding a platform means adding its hashes; silently downloading an
    # unverified binary is the failure this whole table exists to prevent.
    if ! want="$(digest_for "$asset")"; then
        echo "no recorded SHA-256 for asset '$asset'" >&2
        echo "add it to digest_for() above rather than removing the check" >&2
        exit 1
    fi

    if cached_ok "$dest" "$want"; then
        echo "    cached: $(basename "$dest")"
        return
    fi
    if [ -e "$dest" ]; then
        echo "    re-fetching $(basename "$dest") (pin or content changed)"
    else
        echo "    downloading $(basename "$dest")"
    fi
    curl --fail --location --silent --show-error --retry 3 --retry-delay 2 \
         --proto '=https' --proto-redir '=https' \
         --max-time 300 -o "$dest.part" "$url"

    # Verified BEFORE chmod +x: an unverified file never becomes executable.
    got="$(sha256sum "$dest.part" | cut -d' ' -f1)"
    if [ "$got" != "$want" ]; then
        rm -f "$dest.part"
        echo "checksum mismatch for $url" >&2
        echo "  expected $want" >&2
        echo "  got      $got" >&2
        exit 1
    fi
    mv "$dest.part" "$dest"
    chmod +x "$dest"
    printf '%s' "$url" > "$(stamp_path "$dest")"
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
    if ! stamp_matches "$BIN_DIR/mpv/mpv.exe" "mpv:${MPV_WIN_TAG}"; then
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
        mpv_asset="$(basename "$mpv_url")"
        if ! mpv_want="$(digest_for "$mpv_asset")"; then
            echo "no recorded SHA-256 for mpv asset '$mpv_asset'" >&2
            echo "the tag resolved to an asset this script has not pinned;" >&2
            echo "add its digest to digest_for() rather than skipping the check" >&2
            exit 1
        fi
        echo "    downloading $mpv_asset"
        curl --fail --location --silent --show-error --retry 3 --max-time 600 \
             --proto '=https' --proto-redir '=https' \
             -o "$BIN_DIR/mpv.7z.part" "$mpv_url"
        # Verified before it is unpacked: 7z x on an unverified archive is
        # already executing attacker-chosen paths.
        mpv_got="$(sha256sum "$BIN_DIR/mpv.7z.part" | cut -d' ' -f1)"
        if [ "$mpv_got" != "$mpv_want" ]; then
            rm -f "$BIN_DIR/mpv.7z.part"
            echo "checksum mismatch for $mpv_url" >&2
            echo "  expected $mpv_want" >&2
            echo "  got      $mpv_got" >&2
            exit 1
        fi
        mv "$BIN_DIR/mpv.7z.part" "$BIN_DIR/mpv.7z"
        mkdir -p "$BIN_DIR/mpv"
        # 7z ships with the GitHub windows runner and with Git for Windows.
        7z x -y -o"$BIN_DIR/mpv" "$BIN_DIR/mpv.7z" > /dev/null
        rm -f "$BIN_DIR/mpv.7z"
        printf '%s' "mpv:${MPV_WIN_TAG}" > "$(stamp_path "$BIN_DIR/mpv/mpv.exe")"
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
