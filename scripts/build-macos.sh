#!/usr/bin/env bash
# Build the self-contained macOS app and disk image:
#   dist/Snatch.app  and  dist/Snatch-<arch>.dmg
#
# Run natively on macOS. The workflow calls this same script.
#
# The app is unsigned and un-notarised, so Gatekeeper blocks a first
# double-click. README documents the right-click -> Open workaround; do not
# "fix" that here by disabling anything on the user's machine.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

ARCH="$(uname -m)"
[ "$(uname -s)" = "Darwin" ] || { echo "build-macos.sh must run on macOS" >&2; exit 1; }

echo "=== 1/5 fetch bundled binaries ==="
scripts/fetch-binaries.sh

echo "=== 2/5 smoke-test platform_utils ==="
python3 scripts/verify_platform_utils.py --require-bundled

echo "=== 3/5 PyInstaller .app build ==="
rm -rf build dist
pyinstaller pyinstaller.spec --clean --noconfirm
[ -d dist/Snatch.app ] || { echo "dist/Snatch.app not produced" >&2; exit 1; }

echo "=== 4/5 ad-hoc sign so the bundle at least loads ==="
# An ad-hoc signature is not notarisation and does not clear Gatekeeper, but an
# unsigned arm64 bundle will not launch at all on Apple Silicon.
codesign --force --deep --sign - dist/Snatch.app
codesign --verify --deep --strict dist/Snatch.app

echo "=== 5/5 package .dmg ==="
dmg="dist/Snatch-${ARCH}.dmg"
rm -f "$dmg"
staging="$(mktemp -d)"
cp -R dist/Snatch.app "$staging/"
ln -s /Applications "$staging/Applications"
hdiutil create -volname "Snatch" -srcfolder "$staging" -ov -format UDZO "$dmg"
rm -rf "$staging"

[ -f "$dmg" ] || { echo "$dmg not produced" >&2; exit 1; }
echo "=== built $dmg ($(du -h "$dmg" | cut -f1)) ==="
