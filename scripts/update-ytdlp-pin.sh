#!/usr/bin/env bash
# Bump the bundled yt-dlp pin to the newest nightly.
#
# Why this exists. The app only offers the user an update when the latest
# nightly is NEWER than the copy in use, so a build that bundles the latest
# asks the user for nothing on first launch. Bumping the pin by hand is what
# put a freshly downloaded release a fortnight behind and made that prompt
# appear immediately -- the update machinery was working correctly on a
# stale input.
#
# The pin itself stays: it records exactly what a given build shipped, so a
# build remains reproducible. What changes is that publishing re-resolves it
# instead of trusting whoever last remembered.
#
# Usage:
#   scripts/update-ytdlp-pin.sh           bump the pin to the latest nightly
#   scripts/update-ytdlp-pin.sh --check   report only; exit 1 if behind
#
# Run it BEFORE building the artefacts for a release, so the build fetches
# what the pin now names.
#
# It moves the version AND the three yt-dlp digests in digest_for(), from the
# same API response. Moving the version alone was SNAT-0067: the cache is
# keyed on content under a version-independent filename, so on a machine with
# a populated bin/ the old binary still matched the unchanged digest, nothing
# was fetched, and a local build went green shipping the previous nightly.
set -euo pipefail

REPO="${YTDLP_REPO:-yt-dlp/yt-dlp-nightly-builds}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PIN_FILE="$ROOT/scripts/fetch-binaries.sh"
DOC_FILE="$ROOT/docs/building.md"

check_only=0
if [ "${1:-}" = "--check" ]; then
    check_only=1
elif [ -n "${1:-}" ]; then
    echo "usage: $(basename "$0") [--check]" >&2
    exit 2
fi

# The ${...} here is literal text in the pin line being matched, not an
# expansion, so the pattern must stay single-quoted.
# shellcheck disable=SC2016
current="$(sed -n 's/^YTDLP_VERSION="\${YTDLP_VERSION:-\(.*\)}"$/\1/p' "$PIN_FILE")"
if [ -z "$current" ]; then
    echo "could not read YTDLP_VERSION from $PIN_FILE" >&2
    exit 1
fi

# The nightly channel's own "latest" release. Resolved rather than guessed,
# because the tag is a build timestamp and cannot be derived from a date.
# One response carries both the tag and each asset's `digest`, so the version
# and its digests cannot come from two different releases.
release_json="$(curl --fail --location --silent --show-error \
                     --proto '=https' --proto-redir '=https' --max-time 30 \
                     "https://api.github.com/repos/${REPO}/releases/latest")"

# Prints the tag, then "<asset> <sha256>" for each asset fetch-binaries.sh
# pins. A missing asset or digest is an error, never a blank to write.
resolved="$(printf '%s' "$release_json" | python3 -c '
import json, sys
release = json.load(sys.stdin)
print(release["tag_name"])
digests = {a["name"]: a.get("digest") or "" for a in release["assets"]}
for name in ("yt-dlp", "yt-dlp_macos", "yt-dlp.exe"):
    digest = digests.get(name, "")
    if not digest.startswith("sha256:"):
        sys.exit(f"no sha256 digest for asset {name!r}")
    print(name, digest[len("sha256:"):])
')" || { echo "could not resolve the latest nightly from ${REPO}" >&2; exit 1; }
latest="$(printf '%s\n' "$resolved" | head -n 1)"

echo "  bundled pin    : $current"
echo "  latest nightly : $latest"

if [ "$current" = "$latest" ]; then
    echo "  already the latest nightly — nothing to do"
    exit 0
fi

if [ "$check_only" -eq 1 ]; then
    echo "PIN IS BEHIND — run scripts/update-ytdlp-pin.sh before publishing" >&2
    exit 1
fi

sed -i "s/^YTDLP_VERSION=.*/YTDLP_VERSION=\"\${YTDLP_VERSION:-${latest}}\"/" "$PIN_FILE"
# The digest lines read `        <asset>)   echo <sha256> ;;`. The asset name is
# matched literally (the dot in yt-dlp.exe escaped), so no other line moves.
while read -r asset sha; do
    pattern="$(printf '%s' "$asset" | sed 's/\./\\./g')"
    sed -i "s/^\([[:space:]]*${pattern})[[:space:]]*echo \)[0-9a-f]\{64\}/\1${sha}/" "$PIN_FILE"
    if ! grep -Eq "^[[:space:]]*${pattern}\)[[:space:]]*echo ${sha} ;;" "$PIN_FILE"; then
        echo "rewrite failed: digest for ${asset} in $PIN_FILE is not ${sha}" >&2
        exit 1
    fi
done < <(printf '%s\n' "$resolved" | tail -n +2)
# The docs table names the same version; rewritten here so the two cannot
# drift into disagreeing about what a build ships.
# Backticks are literal markdown in the row being rewritten; only the
# version is interpolated, via the double-quoted middle section.
# shellcheck disable=SC2016
sed -i 's/\(| yt-dlp (bundled binary) .*nightly `\)[^`]*\(`\)/\1'"$latest"'\2/' "$DOC_FILE"

# shellcheck disable=SC2016
written="$(sed -n 's/^YTDLP_VERSION="\${YTDLP_VERSION:-\(.*\)}"$/\1/p' "$PIN_FILE")"
if [ "$written" != "$latest" ]; then
    echo "rewrite failed: $PIN_FILE still reads '$written'" >&2
    exit 1
fi
if ! grep -q "nightly \`${latest}\`" "$DOC_FILE"; then
    echo "rewrite failed: $DOC_FILE was not updated to ${latest}" >&2
    exit 1
fi

echo "  bumped $current -> $latest (version and yt-dlp digests)"
echo "  rebuild so the bundled binary matches the pin"
