#!/usr/bin/env bash
# Install apt packages on a GitHub runner without hanging.
#
# SNAT-0019: the Tk-runtime step hung for 25+ minutes on two runs in one day,
# intermittently, with the workflow-level needrestart fix already in place --
# so needrestart was not the whole cause. What is left is runner-side apt
# contention: a dpkg lock held by unattended-upgrades, or a mirror connection
# that stalls without ever failing. Neither is reproducible under act, whose
# container runs neither daemon (docs/building.md says the same).
#
# Three bounds, because the cause is not pinned down and each one is cheap:
#   DPkg::Lock::Timeout  wait for a held lock instead of blocking on it
#   Acquire::*           bound and retry a mirror connection that stalls
#   timeout(1)           kill an attempt that hangs anyway, so that the retry
#                        below can actually happen
#
# Both apt call sites in .github/workflows/ci.yml go through this script.
# They are here rather than inline because fixing one of the two and missing
# the other is precisely what happened with needrestart on 2026-08-19.
set -euo pipefail

if [ "$#" -eq 0 ]; then
    echo "usage: ${0##*/} <package>..." >&2
    exit 2
fi

APT_OPTS=(
    -o DPkg::Lock::Timeout=120
    -o Acquire::Retries=3
    -o Acquire::http::Timeout=30
)
ATTEMPT_TIMEOUT=300
ATTEMPTS=2

for attempt in $(seq "$ATTEMPTS"); do
    if timeout "$ATTEMPT_TIMEOUT" sudo apt-get "${APT_OPTS[@]}" update -qq &&
        timeout "$ATTEMPT_TIMEOUT" sudo apt-get "${APT_OPTS[@]}" install \
            -y -qq --no-install-recommends "$@"; then
        exit 0
    fi
    echo "apt attempt ${attempt} of ${ATTEMPTS} failed or stalled" >&2
    sleep 15
done

echo "apt failed after ${ATTEMPTS} attempts: $*" >&2
exit 1
