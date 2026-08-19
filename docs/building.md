# Building the downloadable files

Snatch ships three self-contained downloads — a Windows `.exe`, a Linux
AppImage and a macOS `.dmg`. This describes how they are produced.

## One script per platform, called by both CI and you

```
scripts/fetch-binaries.sh   shared: downloads yt-dlp, ffmpeg and ffprobe into bin/
scripts/build-linux.sh      -> dist/Snatch-<arch>.AppImage
scripts/build-windows.sh    -> dist/snatch.exe
scripts/build-macos.sh      -> dist/Snatch.app and dist/Snatch-<arch>.dmg
```

`.github/workflows/ci.yml` calls exactly these scripts. That is the point: a
workflow that re-implements the build in YAML drifts away from the script, and
then a local pass stops meaning anything. **When changing how a platform is
built, change the script, not the workflow step that calls it.**

Each script must run on its own platform — `build-macos.sh` refuses to run
anywhere but macOS, and so on.

## Before you push

```bash
scripts/local-ci.sh          # lint, then execute ci.yml's Linux jobs via act
scripts/local-ci.sh --lint   # lint only; enough for a documentation-only change
scripts/local-ci.sh --no-act # lint, then build natively instead of in a container
```

`local-ci.sh` does not describe the pipeline — it **runs** `ci.yml` through
[`act`](https://github.com/nektos/act), in a container, so it cannot drift from
what GitHub will do.

**It cannot run the Windows or macOS jobs.** `act` runs Linux containers. No
tool on a Linux machine can execute those two jobs, and the script says so in
its own output rather than implying a pass. They are covered by pushing and
reading the CI result.

Artifact-upload steps are skipped under act (`if: ${{ !env.ACT }}`) because
there is no artifact service outside GitHub; without the guard they fail every
local run and hide the real build result.

## What gets bundled, and where the versions live

| Component | Pinned in | Current |
|---|---|---|
| yt-dlp (Python library) | `requirements.txt` | 2026.3.17 |
| yt-dlp (bundled binary) | `scripts/fetch-binaries.sh` | 2026.03.17 |
| ffmpeg + ffprobe | `scripts/fetch-binaries.sh` | ffmpeg-static `b6.1.1` |
| PyInstaller | `.github/workflows/ci.yml` | 6.11.1 |

The two yt-dlp versions must be bumped together. They are spelled differently
on purpose: GitHub tags zero-pad the month (`2026.03.17`), PyPI does not
(`2026.3.17`).

One source (`eugeneware/ffmpeg-static`) provides ffmpeg and ffprobe for all
three platforms, so there is a single pin to move.

## Where user data goes

`snatch/platform_utils.py:app_data_dir()` owns this, and it differs per
platform for a reason:

| Platform | Location | Why |
|---|---|---|
| Windows | next to `snatch.exe` | Keeps the app portable — move the .exe and settings follow. |
| macOS | `~/Library/Application Support/Snatch` | Writing inside a `.app` bundle breaks on upgrade and on a read-only mount. |
| Linux | `$XDG_DATA_HOME/snatch` | An AppImage's `sys.executable` is a temp directory that is deleted on exit. |

## Releasing

Push a `v*` tag. The `release` job needs all three builds to succeed, so a
release can never be published with a platform missing or broken.

```bash
git tag -a v1.2.3 -m "v1.2.3"
git push --follow-tags origin main
```

## Known rough edges

- **The AppImage runtime tracks `continuous`**, not a fixed version, while
  everything else is pinned (SNAT-0009).
- **`appimagetool` will hang forever** if left to download that runtime
  itself — observed blocked in a futex at 0% CPU with no output. `build-linux.sh`
  fetches it up front and passes `--runtime-file` so a network problem fails
  fast and visibly instead.
- **The macOS app is unsigned and un-notarised.** Gatekeeper blocks the first
  double-click; the README documents the right-click → Open workaround. Signing
  needs a paid Apple Developer account.
