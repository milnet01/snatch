#!/usr/bin/env bash
# Local CI gate — run this before every push.
#
# It does NOT re-describe the pipeline. It lints and then EXECUTES
# .github/workflows/ci.yml itself, via `act`, so it cannot drift away from
# what GitHub will run. A hand-written mirror of a pipeline goes green on a
# pipeline that will fail; that is the failure mode this avoids.
#
# What it can and cannot do is stated plainly at the end. `act` runs Linux
# containers, so the Windows and macOS jobs are NOT executed here — no tool on
# this machine can run them, and the report says so rather than implying a
# pass. Those two are covered by pushing to a branch and reading CI.
#
# Usage:
#   scripts/local-ci.sh            # lint + run the linux jobs through act
#   scripts/local-ci.sh --lint     # lint only (fast; use for a docs-only push)
#   scripts/local-ci.sh --no-act   # lint + native build, skip the container
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

WORKFLOW=".github/workflows/ci.yml"
MODE="full"
case "${1:-}" in
    --lint)   MODE="lint"   ;;
    --no-act) MODE="no-act" ;;
    "")       ;;
    *) echo "usage: $0 [--lint|--no-act]" >&2; exit 2 ;;
esac

red()   { printf '\033[31m%s\033[0m\n' "$*"; }
green() { printf '\033[32m%s\033[0m\n' "$*"; }
bold()  { printf '\033[1m%s\033[0m\n'  "$*"; }

FAILED=0
step() {
    local label="$1"; shift
    printf '\n'; bold "── $label"
    if "$@"; then
        green "   ok"
    else
        red "   FAILED: $label"
        FAILED=1
    fi
}

need() {
    command -v "$1" >/dev/null 2>&1 || {
        red "missing required tool: $1"
        FAILED=1
        return 1
    }
}

bold "Snatch local CI — mirrors $WORKFLOW by executing it"

# ── Static checks ─────────────────────────────────────────────────────
if need actionlint; then step "actionlint (workflow syntax; NOT action pinning — see SNAT-0035)" \
    actionlint "$WORKFLOW"; fi
if need yamllint; then step "yamllint (workflow YAML)" \
    yamllint -d "{extends: relaxed, rules: {line-length: disable}}" "$WORKFLOW"; fi
if need shellcheck; then step "shellcheck (build scripts)" \
    shellcheck scripts/*.sh; fi
step "python byte-compile (every module)" \
    python3 -m compileall -q snatch.py snatch scripts
step "platform_utils smoke-test" \
    python3 scripts/verify_platform_utils.py
step "user-data permission pass (SNAT-0006)" \
    python3 scripts/verify_permissions.py

if [ "$MODE" = "lint" ]; then
    printf '\n'; bold "lint-only mode — no build was run."
    if [ "$FAILED" -eq 0 ]; then green "LINT PASS"; else red "LINT FAIL"; fi
    exit "$FAILED"
fi

# ── Execute the real workflow ─────────────────────────────────────────
if [ "$MODE" = "full" ]; then
    if command -v act >/dev/null 2>&1; then
        # act below 0.2.86 is vulnerable to CVE-2026-34041 and CVE-2026-34042,
        # and act prints that warning itself. This is a hard failure rather
        # than a warning: the gate runs untrusted workflow code in a container
        # on this machine, and a warning printed 60 lines up a passing run is
        # one nobody reads. openSUSE ships 0.2.84 and calls it current, so
        # `zypper up` does NOT fix this -- install the upstream binary into
        # ~/.local/bin, which precedes /usr/bin on PATH:
        #   curl -fsSLO https://github.com/nektos/act/releases/download/v0.2.89/act_Linux_x86_64.tar.gz
        #   # verify against the published checksums.txt, then:
        #   tar -xzf act_Linux_x86_64.tar.gz act && install -m0755 act ~/.local/bin/act
        act_ver="$(act --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)"
        act_min="0.2.86"
        if [ -n "$act_ver" ] && \
           [ "$(printf '%s\n%s\n' "$act_min" "$act_ver" | sort -V | head -1)" != "$act_min" ]; then
            red "act $act_ver is below $act_min (CVE-2026-34041, CVE-2026-34042)"
            echo "   see the comment above this check in $0 for the upgrade"
            exit 1
        elif [ -z "$act_ver" ]; then
            # Not a silent pass: say the check did not run, rather than
            # letting an unreadable version look like a cleared floor.
            echo "   WARNING: could not read act's version; CVE floor unchecked"
        fi

        # act talks to a Docker-compatible socket; podman provides one.
        if [ -z "${DOCKER_HOST:-}" ] && command -v podman >/dev/null 2>&1; then
            sock="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/podman/podman.sock"
            if [ -S "$sock" ]; then
                export DOCKER_HOST="unix://$sock"
            else
                echo "   starting podman socket service"
                systemctl --user start podman.socket 2>/dev/null || true
                [ -S "$sock" ] && export DOCKER_HOST="unix://$sock"
            fi
        fi
        step "act: static-checks job (the real workflow, in a container)" \
            act push --workflows "$WORKFLOW" --job static-checks \
                --container-architecture linux/amd64 --quiet
        step "act: build-linux job (the real workflow, in a container)" \
            act push --workflows "$WORKFLOW" --job build-linux \
                --container-architecture linux/amd64 --quiet
    else
        red "act not installed — cannot execute the workflow locally."
        echo "   install it, or run with --no-act for a native build instead."
        FAILED=1
    fi
else
    step "native Linux build (scripts/build-linux.sh — same script CI runs)" \
        scripts/build-linux.sh
fi

# ── Report ────────────────────────────────────────────────────────────
printf '\n'
bold "── Coverage of this run"
cat <<'REPORT'
   RAN HERE : static-checks, build-linux  (executed from ci.yml itself)
   NOT RUN  : build-windows, build-macos
              act runs Linux containers only, and this machine is Linux.
              Nothing local can execute those two jobs. They are verified by
              pushing and reading the CI result — a green local run is NOT
              evidence about them.
   NOT RUN  : release  (fires on a v* tag only)

   CAVEAT   : even build-linux is not an exact mirror. act runs
              catthehacker/ubuntu, not GitHub's runner image, so the two
              differ in installed packages. A real case, 2026-08-19: apt-get
              hung for 7 minutes on GitHub against 17 seconds here, because
              the runner has needrestart and this container does not. Green
              here means the BUILD is sound, not that the runner environment
              is.
REPORT

printf '\n'
if [ "$FAILED" -eq 0 ]; then
    green "LOCAL CI PASS — safe to push (Windows/macOS still unverified)"
else
    red "LOCAL CI FAIL — do not push"
fi
exit "$FAILED"
