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

**And even the Linux job is not an exact mirror.** `act` runs
`catthehacker/ubuntu`, not GitHub's runner image; the two carry different
packages. On 2026-08-19 an `apt-get install` that took 17 seconds locally hung
for 7 minutes on GitHub, because the runner ships `needrestart` and the
container does not. A green local run says the build is sound. It does not say
the runner environment is.

Artifact-upload steps are skipped under act (`if: ${{ !env.ACT }}`) because
there is no artifact service outside GitHub; without the guard they fail every
local run and hide the real build result.

## What gets bundled, and where the versions live

| Component | Pinned in | Current |
|---|---|---|
| yt-dlp (bundled binary) | `scripts/fetch-binaries.sh` | nightly `2026.08.30.232658` (SHA-256 pinned) |
| yt-dlp (Python library) | `requirements.txt` | 2026.7.4 |
| ffmpeg + ffprobe | `scripts/fetch-binaries.sh` | ffmpeg-static `b6.1.1` (SHA-256 pinned) |
| QuickJS | `scripts/fetch-binaries.sh` | `v0.16.1` (SHA-256 pinned) |
| mpv (Windows only) | `scripts/fetch-binaries.sh` | `MPV_WIN_TAG=20260814` (SHA-256 pinned) |
| AppImage type2 runtime | `scripts/build-linux.sh` | `20251108` (SHA-256 pinned) |
| appimagetool | `scripts/build-linux.sh` | `1.9.1` (SHA-256 pinned) |
| PyInstaller | `.github/workflows/ci.yml` | 6.11.1 |
| ruff (lint gate only, not bundled) | `.github/workflows/ci.yml` | 0.16.4 |

**Every bundled binary is pinned by CONTENT, not just by tag (SNAT-0031).**
`scripts/fetch-binaries.sh` carries the expected SHA-256 of each asset in
`digest_for()` and verifies it before the file is made executable; the mpv
archive is verified before it is unpacked. A tag pin does not pin content — a
GitHub release asset can be replaced in place — so **bumping a version means
updating its digest too**, and an asset with no recorded digest stops the build
rather than being fetched unverified. Refresh one with:

```bash
gh api repos/<owner>/<repo>/releases/tags/<tag> \
  --jq '.assets[] | select(.name=="<asset>") | .digest'
```

The runtime self-update is verified separately, against the `SHA2-256SUMS`
manifest each nightly publishes (`snatch/version.py`).

**The two yt-dlp pins are deliberately different versions, and do NOT move
together.** The bundled binary is the one the app actually runs, and it comes
from the NIGHTLY channel because stable does not play YouTube (SNAT-0014).
The `requirements.txt` entry is not imported as a library at all — the header
of that file explains why it is there — so it tracks stable and lags. Bumping
one because the other moved is the mistake this note exists to prevent.

### Before publishing a release: bump the bundled yt-dlp

Run `scripts/update-ytdlp-pin.sh`, then build. It re-resolves the pin to the
newest nightly and rewrites both `scripts/fetch-binaries.sh` and the table
above, so the two cannot drift into disagreeing about what a build ships.
`--check` reports without writing and exits non-zero when the pin is behind.

The reason it is a release step rather than an occasional chore: the app
offers the user an update only when the latest nightly is newer than the copy
in use. A release bundling the latest therefore asks the user for nothing on
first launch, while one bundling anything older prompts immediately. Leaving
the bump to whoever remembered is what shipped a build a fortnight behind.

The bundled binary only. The `requirements.txt` entry stays on stable, for
the reason in the note above.

One source (`eugeneware/ffmpeg-static`) provides ffmpeg and ffprobe for all
three platforms, so there is a single pin to move.

### The bundled yt-dlp is a floor, not the last word

Since SNAT-0016 a packaged build can fetch a newer nightly for itself, into
`app_data_dir()/bin/` — `app_data_dir()/bin/updated/` when running from
source — and `find_ytdlp()` prefers that copy. The bundled binary stays as the
fallback, so a failed or half-written download can never leave the app with no
yt-dlp. The `updated/` split exists because from source `app_data_dir()` is the
repo root, so the plain path is the same `bin/` that `fetch-binaries.sh` fills
with the pinned copy: before 2026-09-01 a self-update overwrote the pin and
there was no floor left, while this sentence said otherwise.

Downloads are verified against the `SHA2-256SUMS` file the same yt-dlp release
publishes, before the file is made executable and before it is run. `snatch/version.py` holds the channel
constants, and they must name the same repo `fetch-binaries.sh` does — a
self-update that pulled stable would be a downgrade.

## Where user data goes

`snatch/platform_utils.py:app_data_dir()` owns this, and it differs per
platform for a reason:

| Platform | Location | Why |
|---|---|---|
| Windows | next to `snatch.exe` | Keeps the app portable — move the .exe and settings follow. |
| macOS | `~/Library/Application Support/Snatch` | Writing inside a `.app` bundle breaks on upgrade and on a read-only mount. |
| Linux | `$XDG_DATA_HOME/snatch` | An AppImage's `sys.executable` is a temp directory that is deleted on exit. |

`user_bin_dir()` adds a `bin/` subdirectory to that location, holding binaries
the app has fetched for itself. Windows is the one case that can fall back
elsewhere: keeping user data next to the .exe is right for a USB stick and
wrong under `C:\Program Files`, where writing needs admin rights, so an
unwritable directory sends *only* `bin/` to `%LOCALAPPDATA%\Snatch\bin`.
Config and history stay put, because moving them would strand the settings of
someone who already has them.

## Releasing

Push a `v*` tag. The `release` job needs all three builds to succeed, so a
release can never be published with a platform missing or broken.

```bash
git tag -a v1.2.3 -m "v1.2.3"
git push --follow-tags origin main
```

## Known rough edges

- **The AppImage runtime and `appimagetool` are pinned and checksummed**
  (type2-runtime `20251108`, appimagetool `1.9.1`), with a per-arch SHA-256 in
  `build-linux.sh`. Both used to track `continuous` — this entry previously
  said the runtime was the only unpinned thing, and `appimagetool` was
  unpinned too. To move a pin, change the version, run the build, and replace
  the digest with the one the mismatch message prints. An architecture with no
  recorded digest exits rather than skipping the check.
- **`appimagetool` will hang forever** if left to download that runtime
  itself — observed blocked in a futex at 0% CPU with no output. `build-linux.sh`
  fetches it up front and passes `--runtime-file` so a network problem fails
  fast and visibly instead.
- **The macOS app is unsigned and un-notarised.** Gatekeeper blocks the first
  double-click; the README documents the right-click → Open workaround. Signing
  needs a paid Apple Developer account.
