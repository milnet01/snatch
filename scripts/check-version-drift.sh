#!/usr/bin/env bash
# Every version-bearing file must say the same thing.
#
# This is the `post_check` for .claude/bump.json, and it is the only
# mechanical answer to "did the bump reach every file?". releases.md section 1
# requires the version-bearing files to be enumerated once and recorded; the
# recipe is that list and this asserts the list agrees.
#
# It reads the version from snatch/__init__.py -- the same file the recipe
# names as version_source -- and compares every other surface against it.
# Nothing is hardcoded, so this does not need editing when the version moves.
#
# Adding a version-bearing file means adding it to BOTH the recipe's files[]
# and the check below. A file in the recipe but not here bumps unverified; a
# file here but not in the recipe fails this check on the next release, which
# is the direction that fails loudly.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

fail=0

version="$(sed -n 's/^__version__ = "\([0-9]*\.[0-9]*\.[0-9]*\)"$/\1/p' snatch/__init__.py)"
if [ -z "$version" ]; then
    echo "could not read __version__ from snatch/__init__.py" >&2
    echo "  that file is the version_source; the bump cannot be verified" >&2
    exit 1
fi
echo "version_source: snatch/__init__.py -> $version"

# Each entry is "<file>:<grep -E pattern>", where the pattern must match a
# line carrying $version. The pattern is anchored on the KEY so a match
# proves that key holds the version, not merely that the version appears
# somewhere in the file.
check() {
    local path="$1" label="$2" pattern="$3"
    if [ ! -f "$path" ]; then
        echo "  MISSING  $path ($label)" >&2
        fail=1
        return
    fi
    if grep -Eq "$pattern" "$path"; then
        echo "  ok       $path ($label)"
    else
        echo "  DRIFTED  $path ($label) does not carry $version" >&2
        grep -nE "${pattern%\"*}" "$path" | head -3 >&2 || true
        fail=1
    fi
}

check pyinstaller.spec "CFBundleShortVersionString" \
      "\"CFBundleShortVersionString\": \"${version}\""
check pyinstaller.spec "CFBundleVersion" \
      "\"CFBundleVersion\": \"${version}\""

# The changelog section is checked here because the recipe performs the cut
# itself (a changelog_log op:"release" todo). cut-release's Phase 0e passes
# when a recipe does that, and hands the check to this script -- so without
# the block below nothing would verify the section exists at all.
if grep -Eq "^## \\[${version}\\] - [0-9]{4}-[0-9]{2}-[0-9]{2}" CHANGELOG.md; then
    # No pipe here on purpose. Piping awk into `head -1` closes the pipe
    # early, awk dies on SIGPIPE, and under `set -o pipefail` the whole
    # script exits 141 having checked nothing -- which is what happened the
    # first time this ran. awk does the filtering itself instead.
    body="$(awk -v v="## [${version}] -" '
        index($0, v) == 1 {f=1; next}
        f && /^## \[/ {f=0}
        f && NF && $0 !~ /^### / {print}
    ' CHANGELOG.md)"
    if [ -n "$body" ]; then
        echo "  ok       CHANGELOG.md (dated [$version] section with content)"
    else
        echo "  EMPTY    CHANGELOG.md [$version] section has no entries" >&2
        fail=1
    fi
else
    echo "  MISSING  CHANGELOG.md has no dated [$version] section" >&2
    fail=1
fi

if [ "$fail" -ne 0 ]; then
    echo >&2
    echo "version drift: the files above disagree with snatch/__init__.py" >&2
    echo "re-run the bump, or fix .claude/bump.json if a pattern stopped matching" >&2
    exit 1
fi

echo "all version-bearing files agree on $version"
