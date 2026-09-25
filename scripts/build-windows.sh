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
python scripts/verify_platform_utils.py --require-bundled

echo "=== 3/4 PyInstaller one-file build ==="
rm -rf build dist
pyinstaller pyinstaller.spec --clean --noconfirm

echo "=== 4/4 verify output ==="
[ -f dist/snatch.exe ] || { echo "dist/snatch.exe not produced" >&2; exit 1; }

# Start what was built (SNAT-0024). A bundle can build cleanly and still die
# on launch -- a lost import, a binary left out, a platform call the frozen
# Python lacks -- and until this ran, nothing started one. --selftest opens
# no window; the report file carries the detail because the .exe has no console for stdout.
echo "=== smoke-test dist/snatch.exe ==="
report="dist/selftest.txt"
if ! dist/snatch.exe --selftest "$report" >/dev/null; then
    cat "$report" 2>/dev/null || echo "(no report written)"
    echo "dist/snatch.exe failed its self-test" >&2
    exit 1
fi
cat "$report"
echo "=== built dist/snatch.exe ($(du -h dist/snatch.exe | cut -f1)) ==="
