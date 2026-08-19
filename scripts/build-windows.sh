#!/usr/bin/env bash
# Build the self-contained Windows executable: dist/snatch.exe
#
# Runs under bash on Windows (Git Bash, or the GitHub windows-latest runner,
# which provides bash). The workflow calls this same script.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

case "$(uname -s)" in
    MINGW*|MSYS*|CYGWIN*|Windows_NT) : ;;
    *) echo "build-windows.sh must run on Windows; got $(uname -s)" >&2; exit 1 ;;
esac

echo "=== 1/4 fetch bundled binaries ==="
scripts/fetch-binaries.sh

echo "=== 2/4 smoke-test platform_utils ==="
python scripts/verify_platform_utils.py

echo "=== 3/4 PyInstaller one-file build ==="
rm -rf build dist
pyinstaller pyinstaller.spec --clean --noconfirm

echo "=== 4/4 verify output ==="
[ -f dist/snatch.exe ] || { echo "dist/snatch.exe not produced" >&2; exit 1; }
echo "=== built dist/snatch.exe ($(du -h dist/snatch.exe | cut -f1)) ==="
