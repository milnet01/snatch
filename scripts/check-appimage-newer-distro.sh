#!/usr/bin/env bash
# Run a built AppImage's self-test on a current distro (SNAT-0089).
#
# Usage: scripts/check-appimage-newer-distro.sh dist/Snatch-x86_64.AppImage
#
# The AppImage is built on Ubuntu 22.04, the oldest base it supports, and
# that is where build-linux.sh's own smoke test runs it. 1.3.0 broke only on
# newer systems: the bundle's OpenSSL leaked into yt-dlp (SNAT-0087) and HTTPS
# looked for certificates where Ubuntu keeps them (SNAT-0088). This runs the
# same self-test inside openSUSE Tumbleweed, which is always current, with its
# HTTPS check switched on.
#
# The container gets what any desktop has: the X libraries and a python3,
# which the bundled yt-dlp runs on. It never gets a display.
#
# The image is not pinned on purpose: "current" is the point. It only runs
# the finished AppImage; nothing from it is shipped.
#
# On GitHub Actions a missing container runtime fails the build. Anywhere
# else -- a desktop without one, or act's job container -- it says the check
# was skipped and why, because nothing else would.
set -euo pipefail

IMAGE="docker.io/opensuse/tumbleweed:latest"
# Any HTTPS address that always answers. The update check talks to GitHub,
# so this is the TLS the app really depends on.
HTTPS_URL="https://github.com/"
# Pulling the image and installing the packages dominate; the self-test
# itself takes seconds.
TIMEOUT_SEC=600
PACKAGES="python3 libX11-6 libxcb1 libXft2 libXss1 libXcursor1 libXrandr2 libXinerama1 libXi6 fontconfig"

appimage="${1:?usage: $0 path/to/Snatch.AppImage}"
[ -f "$appimage" ] || { echo "no AppImage at $appimage" >&2; exit 1; }

skip_or_fail() {
    if [ "${GITHUB_ACTIONS:-}" = true ] && [ -z "${ACT:-}" ]; then
        echo "newer-distro check cannot run: $1" >&2
        exit 1
    fi
    echo "    SKIPPED newer-distro check: $1"
    echo "    Run it by hand on a machine with podman or docker:"
    echo "      scripts/check-appimage-newer-distro.sh $appimage"
    exit 0
}

runtime=""
for candidate in podman docker; do
    if command -v "$candidate" >/dev/null && "$candidate" info >/dev/null 2>&1; then
        runtime="$candidate"
        break
    fi
done
[ -n "$runtime" ] || skip_or_fail "no working podman or docker here"

# create + cp + start, not a bind mount: the daemon may be on another
# machine or outside this container, where this path does not exist.
container="$("$runtime" create \
    -e APPIMAGE_EXTRACT_AND_RUN=1 \
    -e SNATCH_SELFTEST_HTTPS_URL="$HTTPS_URL" \
    "$IMAGE" sh -c "
        zypper -nq install --no-recommends $PACKAGES >/dev/null || exit 3
        chmod +x /snatch.AppImage
        /snatch.AppImage --selftest /tmp/report.txt >/dev/null
        status=\$?
        cat /tmp/report.txt 2>/dev/null || echo '(no report written)'
        exit \$status")"
trap '"$runtime" rm -f "$container" >/dev/null 2>&1 || true' EXIT

"$runtime" cp "$appimage" "$container:/snatch.AppImage"
echo "    $runtime, $IMAGE, HTTPS check against $HTTPS_URL"
status=0
timeout "$TIMEOUT_SEC" "$runtime" start -a "$container" || status=$?

case "$status" in
    0) echo "    the AppImage passes its self-test on a current distro" ;;
    3) echo "installing the desktop packages in $IMAGE failed" >&2; exit 1 ;;
    124) echo "the newer-distro check did not finish in ${TIMEOUT_SEC}s" >&2; exit 1 ;;
    *) echo "the AppImage failed its self-test on $IMAGE" >&2; exit 1 ;;
esac
