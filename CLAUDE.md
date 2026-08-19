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
- **All subprocess calls need `timeout`** — handle `TimeoutExpired`

## Quick Reference
- Config: `config.json` (project root, 0o600)
- History: `history.json` (project root, 0o600, max 200 entries)
- Themes: `theme.py` — Dark, Nord, Monokai, YouTube, Dracula, Gruvbox, Solarized (registry: `THEMES`)
- Feature flags: `HAS_DND`, `HAS_MPV`, `HAS_PIL` (detected at import)
- Verify changes: `python3 -m py_compile snatch/<file>.py`
