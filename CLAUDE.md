# CLAUDE.md — Snatch

## Project
Modular tkinter GUI frontend for yt-dlp. Entry point: `snatch.py`. Package: `snatch/`.

## Architecture
- Mixin-based composition: `SnatchApp` in `app.py` inherits from 7 mixins
- Tabs: Download | Search | Media Info | History
- All blocking work runs in daemon threads; GUI updates via `root.after(0, callback)`
- See `STANDARDS.md` for full architecture docs

## Mandatory Rules

### Security (see STANDARDS.md Section 5)
- **Always validate URLs** before subprocess calls (`_is_valid_url()` — http/https only)
- **Always use `--` separator** before URL/path args in subprocess commands
- **Never use `shell=True`** or `sh -c` in subprocess calls
- **0o600 permissions** on all user data files (config, cookies, history)
- **HTTPS-only** for network fetches (thumbnails, updates)
- **Resolve symlinks** with `os.path.realpath()` before opening files/folders
- **Validate directory ownership** for security-sensitive paths (mpv socket)

### Memory Management (see STANDARDS.md Section 6.3)
- **Clean up ToggleSwitch traces** — call `cleanup()` before destroying widgets (theme switch, app close)
- **Store PhotoImage references** as instance attrs — local refs get GC'd while tkinter uses them
- **Close subprocess pipes** in `finally` blocks — never leave stdout/stderr open
- **Close sockets** in `finally` blocks — cap recv buffers at 64KB
- **Free large JSON** with `del data` after extracting needed fields
- **Clear stale data** on theme switch: `formats`, `playlist_entries`, `video_thumbnail`
- **Release everything on close** — data structures, caches, trace callbacks

### Performance (see STANDARDS.md Section 6.1-6.2)
- **Throttle UI updates** from threads — max every 150ms, never per-line
- **Cache expensive lookups** — `shutil.which()` results in class variables
- **Pre-compute derived data** during fetch to avoid redundant parsing in filters
- **Guard redraws** — skip if visual state hasn't changed

### Code Quality (see STANDARDS.md Section 10)
- **Never hardcode hex colors** — always reference `theme.*` attributes
- **Use named constants** for magic numbers (timeouts, buffer sizes, thresholds)
- **Extract duplicated logic** into helper methods
- **PEP 8 import ordering** — stdlib, third-party, local (separated by blank lines)
- **Every `subprocess.run` needs `timeout`** — handle `TimeoutExpired`. The one
  carve-out is the download itself: `Popen` plus an unbounded `wait()`, because
  its duration is the user's file size and any fixed value would be wrong.
  Cancellation is what bounds it — `terminate()`, `wait(timeout=3)`, then
  `kill()` and `wait(timeout=2)`

## Before Pushing

**Run `scripts/local-ci.sh` before every push.** It executes the real
`.github/workflows/ci.yml` through `act` rather than imitating it — a
hand-written mirror of a pipeline goes green on a pipeline that will fail, so
the gate runs the actual file.

- **Documentation-only change** — `scripts/local-ci.sh --lint` is enough. No
  build job acts on `*.md`, so a full run buys nothing.
- **Any code, workflow, spec or script change** — run it in full.
- **It cannot run the Windows or macOS jobs.** `act` runs Linux containers and
  this machine is Linux; nothing local can execute those two. The script says
  so in its own report. A green local run is NOT evidence about them — they
  are verified by pushing and reading CI.

**The workflow and the local gate call the same scripts** (`scripts/build-*.sh`),
so what runs locally and what runs in CI cannot drift. When changing how a
platform builds, change the script — never the workflow step that calls it.

## Quick Reference
- Config: `config.json` (in `platform_utils.app_data_dir()`, 0o600)
- History: `history.json` (same dir, 0o600, max 200 entries)
- **`app_data_dir()` decides where those live, not the project root.** From
  source it *is* the project root; in a packaged build it is not — see
  STANDARDS.md 14.
- Themes: `theme.py` — Dark, Nord, Monokai, YouTube, Dracula, Gruvbox, Solarized (registry: `THEMES`)
- Feature flags: `HAS_DND` (`snatch/__init__.py`), `HAS_PIL` (`snatch/downloader.py`)
- **mpv is gated by `platform_utils.find_mpv()`, not by `HAS_MPV`** — that
  constant still exists in `__init__.py` and nothing reads it (SNAT-0055)
- Diagnostic log: off unless `SNATCH_LOG` is set; module is
  `snatch/logging_setup.py`, file is `snatch.log` in `app_data_dir()` (0o600,
  rotating). Modules use `log = get_logger(__name__)`
- Verify changes: `python3 -m py_compile snatch/<file>.py`
- Pre-push gate: `scripts/local-ci.sh` (`--lint` for docs-only)
- Roadmap: `ROADMAP.md`, ants-v1 format, store-backed (project `snatch`)
- **Never predict the next roadmap ID.** `append`/`append_batch` allocate with
  gaps — a batch jumped SNAT-0031 to SNAT-0035 on 2026-08-20, and 0032-0034
  were never issued. To make two new bullets cite each other, write the batch,
  read the returned `ids`, then patch the references with `roadmap_log
  op:amend_body`. Guessing put wrong cross-references in two pushed commits.
