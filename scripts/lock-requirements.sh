#!/usr/bin/env bash
# Regenerate the hash-locked requirement files CI installs from (SNAT-0066).
#
# A version pin resolves to whatever PyPI serves under that version today; a
# hash pin does not. So CI installs with --require-hashes from these locks,
# which carry a SHA-256 for every distribution of every package, transitive
# ones included. --universal writes one lock valid on Linux, macOS and
# Windows, with platform-only packages behind environment markers.
#
# Run after changing requirements.txt, requirements-build.in or
# requirements-ci.in, and commit the regenerated .txt files with the change.
#
# Usage:
#   scripts/lock-requirements.sh           rewrite both locks
#   scripts/lock-requirements.sh --check   exit 1 if either lock is stale
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Every CI job pins this in actions/setup-python.
PYTHON_VERSION="3.12"

check_only=0
if [ "${1:-}" = "--check" ]; then
    check_only=1
elif [ -n "${1:-}" ]; then
    echo "usage: $(basename "$0") [--check]" >&2
    exit 2
fi

command -v uv >/dev/null || { echo "uv is required: https://docs.astral.sh/uv/" >&2; exit 1; }

stale=0
for name in build ci; do
    out="requirements-${name}.txt"
    tmp="$(mktemp)"
    # uv's own header records the temp path, so it would differ every run;
    # ours names the file's source instead.
    {
        echo "# Generated from requirements-${name}.in by scripts/lock-requirements.sh."
        echo "# Do not edit by hand."
        uv pip compile --quiet --universal --generate-hashes \
            --python-version "$PYTHON_VERSION" --no-header \
            "requirements-${name}.in"
    } > "$tmp"
    if cmp -s "$tmp" "$out"; then
        rm -f "$tmp"
        echo "  $out: up to date"
    elif [ "$check_only" -eq 1 ]; then
        rm -f "$tmp"
        echo "  $out: STALE -- run scripts/lock-requirements.sh" >&2
        stale=1
    else
        mv "$tmp" "$out"
        echo "  $out: rewritten"
    fi
done
exit "$stale"
