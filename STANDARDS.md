# Snatch — Standards Document

## 1. Project Overview

A modular tkinter GUI frontend for [yt-dlp](https://github.com/yt-dlp/yt-dlp), providing video downloading, YouTube search with embedded playback, media file inspection, and download history management.

**Entry point:** `snatch.py` (thin launcher) or `python -m snatch`

---

## 2. Architecture

### 2.1 Package Structure

```
snatch.py                  # Thin launcher (imports __main__.main)
snatch/
├── __init__.py                # Package init, HAS_DND; HAS_MPV is legacy, unread
├── __main__.py                # CLI entry point, creates root Tk window
├── app.py                     # SnatchApp class — composes all mixins
├── theme.py                   # Theme definitions + style setup
├── widgets.py                 # Custom widgets (ToggleSwitch)
├── utils.py                   # Shared utilities (formatting, dialogs, treeview)
├── cookies.py                 # Browser cookie extraction (Firefox SQLite)
├── player.py                  # PlayerMixin — embedded mpv via IPC
├── version.py                 # VersionMixin — yt-dlp version check + update
├── downloader.py              # DownloaderMixin — downloads, queue, format logic
├── platform_utils.py          # Platform-aware paths, bundled-binary lookup, open_path
└── tabs/
    ├── __init__.py             # Empty module marker
    ├── download.py             # DownloadTabMixin — Download tab UI
    ├── search.py               # SearchTabMixin — Search tab UI + logic
    ├── media_info.py           # MediaInfoTabMixin — Media Info tab + ffprobe
    └── history.py              # HistoryTabMixin — History tab + management
```

### 2.2 Mixin Composition

The main class `SnatchApp` (in `app.py`) composes functionality via mixin inheritance:

```python
class SnatchApp(DownloadTabMixin, SearchTabMixin, MediaInfoTabMixin,
               HistoryTabMixin, PlayerMixin, VersionMixin, DownloaderMixin):
```

**MRO:** `SnatchApp → DownloadTabMixin → SearchTabMixin → MediaInfoTabMixin → HistoryTabMixin → PlayerMixin → VersionMixin → DownloaderMixin → object`

**Rules for mixins:**
- Mixins must not define `__init__` — all initialization happens in `SnatchApp.__init__`
- Mixins may access `self.*` attributes set by `SnatchApp.__init__` or other mixins
- Each mixin should document its expected attributes/methods in a class docstring
- Tab mixins expose a single `_create_*_tab(parent)` method called by `create_widgets()`

### 2.3 Tab Architecture

| Tab | Mixin | Purpose |
|-----|-------|---------|
| Download | `DownloadTabMixin` | URL input, format selection, queue, progress |
| Search | `SearchTabMixin` | YouTube search, results, embedded player |
| Media Info | `MediaInfoTabMixin` | Local file analysis via ffprobe |
| History | `HistoryTabMixin` | Download history browsing |

---

## 3. UI & Theme System

### 3.1 Theme Architecture

Themes are defined as classes with color constants in `theme.py`. **Obtain the
active theme by calling `theme.get_theme()` at the point of use — never capture
it at import.** A theme bound at import keeps its colours after `set_theme()`
and the widget stops following the theme switch.

**Theme class contract — required color attributes.** Nothing enforces this
list: §13 runs no conformance check over `THEMES`, so a theme missing an
attribute passes every verification here and surfaces as an `AttributeError`
the first time that widget is drawn in that state.

| Attribute | Purpose | Example |
|-----------|---------|---------|
| `BG` | Main background | `#1a1a2e` |
| `BG_LIGHT` | Secondary background (headings, tabs) | `#16213e` |
| `BG_LIGHTER` | Tertiary background (buttons, hover) | `#1f3460` |
| `FG` | Primary foreground text | `#eaeaea` |
| `FG_DIM` | Secondary/dimmed text | `#a0a0a0` |
| `ACCENT` | Primary accent color | `#e94560` |
| `ACCENT_HOVER` | Accent hover state | `#ff6b6b` |
| `SUCCESS` | Success/positive color | `#4ecca3` |
| `ENTRY_BG` | Entry field background | `#0f0f1a` |
| `BORDER` | Border color | `#2a2a4a` |
| `TREEVIEW_BG` | Treeview background | `#0f0f1a` |
| `TREEVIEW_SELECT` | Treeview selection highlight | `#e94560` |
| `BUTTON_BG` | Button background | `#e94560` |
| `BUTTON_FG` | Button foreground | `#ffffff` |
| `PLAYER_BG` | Video player background | `#000000` |
| `VIDEO_ONLY` | Video-only format indicator | `#ffaa00` |
| `AUDIO_ONLY` | Audio-only format indicator | `#66bbff` |
| `SUBTITLE_ON` | Subtitle toggle active color | `#66bbff` |
| `SPONSORBLOCK_ON` | SponsorBlock toggle active color | `#2ecc71` |
| `KNOB` | Toggle switch knob color | `#ffffff` |
| `ACCENT_BUTTON_FG` | Accent button text color | `#000000` |
| `ACCENT_BUTTON_HOVER` | Accent button hover | `#6ee6b8` |

### 3.2 Widget Guidelines

**Prefer ttk widgets** — they inherit theme styles automatically:
```python
# Good: uses theme via ttk.Style
frame = ttk.LabelFrame(parent, text="Section", padding="12")
entry = ttk.Entry(parent, textvariable=var)
button = ttk.Button(parent, text="Click", style="Accent.TButton")
```

**Use tk widgets only when ttk lacks the feature** (Canvas, embedded player, rich labels):
```python
# When tk widgets are necessary, always reference theme colors
theme = get_theme()        # at point of use — never bound at import
label = tk.Label(parent, bg=theme.BG, fg=theme.FG, font=("Helvetica", 10))
canvas = tk.Canvas(parent, bg=theme.BG, highlightthickness=0)
```

**Never hardcode hex colors in widget constructors.** Always reference theme attributes.

### 3.3 Style Names

| Style | Widget | Purpose |
|-------|--------|---------|
| `TButton` | Button | Default button (accent bg) |
| `Accent.TButton` | Button | Primary action (green bg) |
| `Small.TButton` | Button | Compact button |
| `Title.TLabel` | Label | Main title (18pt bold accent) |
| `Version.TLabel` | Label | Version/status text (9pt dim) |
| `Status.TLabel` | Label | Status bar text (9pt success) |
| `Dark.TCheckbutton` | Checkbutton | Themed checkbox |
| `Dark.TRadiobutton` | Radiobutton | Themed radio button |

### 3.4 Layout Patterns

- **Full-width rows:** `frame.pack(fill=tk.X)`
- **Two-column rows:** Use `columnconfigure(uniform="half")` to prevent dynamic resizing
- **Expanding content:** `frame.pack(fill=tk.BOTH, expand=True)`
- **Padding:** LabelFrames use `padding="12"` or `padding="8"` for compact sections
- **Spacing:** `pady=(0, 8)` between rows, `padx=(0, 5)` between buttons

---

## 4. Threading Model

### 4.1 Rules

1. **All blocking operations run in daemon threads** — format fetching, downloads, searches, ffprobe, version checks
2. **Never modify GUI from a thread** — always use `self.root.after(0, callback)` for thread-safe updates
3. **Thread creation pattern:**
   ```python
   thread = threading.Thread(target=self._method_thread, args=(arg,))
   thread.daemon = True
   thread.start()
   ```
4. **Progress updates** from threads use `root.after(0, lambda p=value: self.var.set(p))` to avoid closure issues
5. **Bind every value the lambda reads** with a default argument, not just progress values. `root.after` runs the lambda later, on the main thread, and a bare `lambda:` reads the variable at that point rather than at scheduling time. The `except ... as e` case is the sharp one: Python unbinds `e` when the `except` block ends, so `lambda: f"{e}"` raises `NameError` and the user sees no error dialog at all. Write `lambda e=e: ...`.

### 4.2 Thread-Safe Update Pattern

```python
def _background_operation(self):
    """Start a background task"""
    self.status_var.set("Working...")  # OK: called from main thread
    thread = threading.Thread(target=self._bg_thread)
    thread.daemon = True
    thread.start()

def _bg_thread(self):
    """Background thread — NO direct GUI access"""
    try:
        result = expensive_operation()
        # Schedule GUI update on main thread
        self.root.after(0, lambda result=result: self._bg_complete(result))
    except Exception as e:
        # e=e is required, not stylistic: e is unbound when this block ends.
        self.root.after(0, lambda e=e: self._bg_error(str(e)))

def _bg_complete(self, result):
    """Callback on main thread — safe to update GUI"""
    self.status_var.set("Done!")
    self.some_widget.config(text=result)
```

---

## 5. Security

### 5.1 URL Validation

All URLs are validated before passing to subprocess commands:
```python
@staticmethod
def _is_valid_url(url):
    if not url:
        return False
    if re.match(r'^ytsearch\w*:', url):  # yt-dlp search prefix
        return True
    return url.startswith("http://") or url.startswith("https://")
```

### 5.2 Subprocess Safety

- **Always use `--` separator** before URL/path arguments to prevent flag injection:
  ```python
  cmd.extend(["--", url])
  platform_utils.open_path(path)   # never a bare xdg-open — see below
  ```
- **Never use `shell=True`** in subprocess calls
- **Never use `sh -c`** — pass arguments as list items, not shell strings
- **Use list-form commands**, not string concatenation
- **No privilege escalation** — the app never invokes `pkexec` or `sudo`. Updates
  are written into `platform_utils.user_bin_dir()`, inside the user's own data
  directory, so nothing outside the app is ever modified
- **HTTPS-only** for network fetches. Route app-side downloads through
  `version._open_https`, which checks the requested URL **and**
  `resp.geturl()` afterwards — urllib follows redirects and permits an
  https -> http downgrade, so a prefix check alone asserts what was asked
  for rather than what arrived. (`--proto '=https'` is curl's equivalent
  guard in the build scripts; it is not available to the app.)
- **Never leak sensitive paths** (cookie file locations) in status bar output

### 5.3 File Permissions

Sensitive files are written through `utils.atomic_private_write`, or
`utils.write_private_json` for JSON:

```python
from .utils import write_private_json
write_private_json(filepath, data)          # config.json, history.json

from .utils import atomic_private_write
with atomic_private_write(path) as f:       # cookies.txt, or any text file
    f.write(...)
```

**Do not use `os.open(path, O_WRONLY | O_CREAT | O_TRUNC, 0o600)`,** which is
what this section used to show. It does not deliver the guarantee above. The
mode argument applies ONLY when the file is created, so an existing file keeps
whatever bits it already had — measured 2026-08-31: a 0644 file rewritten
through that call stays 0644, on all three of the files listed below. And
`O_TRUNC` empties the target before the new content is written, so a failure
part-way leaves a truncated file where a complete one was. The helper writes to
a temp file in the same directory with an explicit mode and `os.replace`s it
into place, so both properties hold whatever the target was. It also sets
`encoding="utf-8"` rather than letting the locale decide.

**A new sensitive file must be registered in two places, not one.** Writing it
through the helper covers the file from then on; it does nothing for a copy that
already exists with looser bits. Add its name to `utils.PRIVATE_DATA_FILES`,
which `utils.tighten_user_data_permissions()` walks at startup — called from
`SnatchApp.__init__` — to repair files predating the private write path or
carried in from an older install. **That walk is a no-op on Windows** (see
§14), so the legacy-copy problem is closed on macOS and Linux only.

Then update `scripts/verify_permissions.py`, whose fixture pairs
`PRIVATE_DATA_FILES` with a fixed tuple of loose modes and asserts every entry
was tightened. CI runs it, so a name added in one place and not the other turns
the pipeline red.

**Files with restricted permissions:**
- `config.json` — user preferences
- `cookies.txt` — browser cookies
- `history.json` — download history
- Temp cookie DB copies (`os.chmod(tmp_path, 0o600)` after copy)

### 5.4 Player Socket

The mpv IPC socket is placed in `XDG_RUNTIME_DIR` (user-private) instead of `/tmp`:
```python
runtime_dir = os.environ.get("XDG_RUNTIME_DIR", tempfile.gettempdir())
# Validate ownership before trusting the directory
runtime_dir = os.path.realpath(runtime_dir)
if is_windows() or not os.path.isdir(runtime_dir) or os.stat(runtime_dir).st_uid != os.getuid():
    runtime_dir = tempfile.gettempdir()
```

### 5.5 Path Validation

- **Resolve symlinks** with `os.path.realpath()` before opening files/folders
- **Validate dropped URLs** at drop time, not just at processing time
- **Reject null bytes** in file paths
- **Verify directory ownership** for security-sensitive paths (e.g. socket directory)

---

## 6. Performance & Memory Management

### 6.1 Caching

- **Cache `shutil.which()` lookups** in class-level variables — PATH rarely changes during a session
- **Cache history data** in memory (`_history_cache`) — only read from disk on first access, update cache on writes
- **Pre-compute derived data** during fetch (e.g. `video_only`, `audio_only`, `height` flags on formats) to avoid redundant parsing in hot paths

### 6.2 UI Update Throttling

- **Throttle rapid UI updates** (e.g. download progress) to max ~150ms intervals using `time.monotonic()` — never update per-line from subprocess output
- **Use adaptive polling** — poll less frequently when idle (e.g. 1000ms when paused vs 500ms when playing)
- **Guard widget redraws** — skip redraws if the visual state hasn't changed (e.g. ToggleSwitch `_last_drawn_value`)

### 6.3 Memory Leak Prevention

**Mandatory practices:**

1. **ToggleSwitch trace cleanup:** Always call `cleanup()` before destroying ToggleSwitch widgets (theme switch, app close) to remove `trace_add` callbacks. Accumulated traces hold references to destroyed widgets.
2. **PhotoImage references:** Store all `tk.PhotoImage` objects as instance attributes (`self._icon`, `self.video_thumbnail`). Local-only references get garbage collected while tkinter still uses them.
3. **Subprocess pipes:** Always close `stdout`/`stderr` pipes in a `finally` block after reading. On cancel, `terminate()` + `wait(timeout)` + `kill()` as fallback.
4. **Socket cleanup:** Close sockets in `finally` blocks. Cap recv buffers (`while len(data) < 65536`).
5. **Free large intermediates:** `del data` after extracting fields from large JSON responses. Close PIL Images after converting to PhotoImage.
6. **Clear stale data on rebuild:** When theme switching destroys/recreates widgets, clear `formats`, `playlist_entries`, `video_thumbnail`, and `search_results`.
7. **Release on close:** `_on_close()` must release all large data structures, clean up trace callbacks, and clear caches.

**Patterns to avoid:**
- Trace callbacks without stored IDs — always store the return value of `trace_add()` for later `trace_remove()`
- Unbounded buffers in network recv loops — always cap with a maximum size
- Holding references to subprocess `Popen` objects after the process exits — set to `None` in `_reset_ui()`

### 6.4 Constants

Define magic numbers as named constants at module or class level:

```python
PROGRESS_THROTTLE_SEC = 0.15
PLAYER_POLL_PLAYING_MS = 500
PLAYER_POLL_PAUSED_MS = 1000
SOCKET_RECV_CAP = 65536
SOCKET_CHUNK_SIZE = 4096
THUMBNAIL_SIZE = (160, 120)
MAX_HISTORY_ENTRIES = 200
```

---

## 7. Configuration

### 7.1 Config File

**Location:** `platform_utils.app_data_dir()/config.json` — see §14
**Permissions:** `0o600`

**Persisted settings:**

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `save_path` | string | `~/Downloads` | Download output directory |
| `media_file` | string | `""` | Last analyzed media file path |
| `window_geometry` | string | `"1200x900"` | Whatever `root.geometry()` returns — `WxH+X+Y`, so position too. The default seeds size only |
| `preferred_resolution` | string | `""` | Last-used format resolution |
| `preferred_ext` | string | `""` | Last-used format extension |
| `browser` | string | `"none"` | Browser for cookie extraction |
| `merge_audio` | int | `1` | Auto-merge audio with video-only |
| `subtitles` | int | `0` | Download subtitles |
| `sponsorblock` | int | `0` | Enable SponsorBlock segment removal |
| `speed_limit` | string | `"Unlimited"` | Download speed limit |
| `theme` | string | `"Dark"` | Active theme name |
| `last_tab` | int | `0` | Index of the notebook tab to reopen on launch |

### 7.2 History File

**Location:** `platform_utils.app_data_dir()/history.json` — see §14
**Permissions:** `0o600`
**Max entries:** 200 (oldest trimmed on overflow)

Each entry:
```json
{
  "date": "2026-03-10 14:30",
  "title": "Video Title",
  "url": "https://...",
  "format": "1080p mp4",
  "path": "/home/user/Downloads"
}
```

### 7.3 Save/Load Lifecycle

- **Load:** `_load_config()` called in `__init__`, before widget creation
- **Save:** `_save_config()` is called from exactly two places — the theme
  change handler and `_on_close()`. **Nothing saves after a download
  completes**, so a value that must survive a kill rather than a clean quit
  needs its own save call
- **Graceful fallback:** Returns `{}` on missing/corrupt config

---

## 8. Dependencies

### 8.1 Required

| Dependency | Purpose |
|------------|---------|
| Python 3.10+ | Runtime |
| tkinter | GUI framework (usually bundled with Python) |
| yt-dlp | Video downloading engine |

### 8.2 Recommended

| Dependency | Purpose | Detection |
|------------|---------|-----------|
| Deno, Node.js, QuickJS or Bun | YouTube JS challenge solving | bundled copy **and** every one on PATH — all enabled, yt-dlp chooses |
| ffmpeg/ffprobe | Media merging + analysis | Subprocess call |
| mpv | Embedded video player | `platform_utils.find_mpv()` — prefers the bundled copy. **Not `HAS_MPV`**, which nothing reads |
| Pillow (PIL) | Thumbnail display | `import PIL` → `HAS_PIL` |

### 8.3 Optional Enhancements

| Dependency | Purpose | Detection |
|------------|---------|-----------|
| tkinterdnd2 | Drag & drop URL support | `import tkinterdnd2` → `HAS_DND` |
| zenity | Native file dialogs | `zenity_file_dialog()` fallback |

### 8.4 Feature Detection Pattern

```python
# In __init__.py — an optional import, resolved once at import time
try:
    from tkinterdnd2 import TkinterDnD
    HAS_DND = True
except ImportError:
    HAS_DND = False
```

**A binary on PATH is not detected this way.** `HAS_MPV` is still defined in
`__init__.py` and nothing reads it: `shutil.which` at import time misses the
copy bundled into a packaged build. Use `platform_utils.find_mpv()` — and the
`find_*` helpers generally — which check the bundled copy first.

---

## 9. Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+D` | Download selected format |
| `Ctrl+Return` | Fetch formats for URL |
| `Ctrl+Q` | Add URL to queue |
| `Ctrl+O` | Open download folder |
| `Ctrl+L` | Focus URL entry (Download tab) |
| `Ctrl+F` | Focus search entry (Search tab) |
| `Ctrl+1/2/3/4` | Switch to tab 1/2/3/4 |
| `Escape` | Cancel current download |

---

## 10. Coding Standards

### 10.1 General

- **Python 3.10+** compatibility, matching the floor `README.md` promises.
  Nothing enforces it: CI builds on 3.12 only, so any lower version is
  unverified rather than known good
- **PEP 8** style with 100-char line limit (soft)
- **Docstrings** on all public methods and classes (one-line or multi-line)
- **Type hints** not required but welcomed on utility functions
- **No mutable state shared across modules.** Instance state lives on `self`.
  A process-wide cache is a class variable inside a mixin (§6.1), or — in the
  class-free helper modules — a module-private value set through the module's
  own accessor: `theme.active_theme` via `set_theme()`, and
  `platform_utils._USER_BIN_DIR` via `user_bin_dir()`. Never a module value a
  caller mutates directly

### 10.2 Naming Conventions

| Type | Convention | Example |
|------|-----------|---------|
| Classes | PascalCase | `SnatchApp`, `ToggleSwitch` |
| Mixins | PascalCase + "Mixin" suffix | `PlayerMixin`, `DownloaderMixin` |
| Public methods | snake_case | `fetch_formats()`, `cancel_download()` |
| Private methods | `_` prefix | `_download_thread()`, `_apply_filters()` |
| Thread targets | `_*_thread` suffix | `_search_thread()`, `_fetch_formats_thread()` |
| tk variables | `*_var` suffix | `url_var`, `status_var`, `progress_var` |
| Widgets stored on self | descriptive name | `self.format_tree`, `self.download_btn` |
| Constants | UPPER_SNAKE | `DarkTheme.BG`, `ToggleSwitch.WIDTH` |

### 10.3 Error Handling

- **User-facing errors:** `messagebox.showerror()` / `messagebox.showwarning()`
- **Thread errors:** Catch in thread, report via `root.after(0, callback)`
- **Config/file I/O:** `try/except` with graceful fallback, never crash
- **Subprocess:** Always use `timeout` parameter; handle `TimeoutExpired`
- **External tools:** Check availability before use (`shutil.which()`, `HAS_*` flags)

### 10.4 Imports

Order: stdlib → third-party → local (separated by blank lines)

```python
import os
import json
import threading
import tkinter as tk
from tkinter import ttk, messagebox

from ..theme import get_theme
from ..utils import format_duration, clear_treeview
```

---

## 11. Custom Widgets

### 11.1 ToggleSwitch

A Canvas-based toggle switch in `widgets.py`.

**Constructor:**
```python
ToggleSwitch(parent, variable,
             on_text="Label On", off_text="Label Off",
             on_color=theme.SUCCESS, off_color=theme.BG_LIGHTER)
```

**Key properties:**
- `WIDTH=50`, `HEIGHT=26`, `PAD=3`
- `variable` — `tk.IntVar` (0=off, 1=on)
- `label` — separate `tk.Label` widget (must be packed separately)
- Knob color follows `theme.KNOB`

**Usage:**
```python
toggle = ToggleSwitch(frame, variable=self.my_var,
                      on_text="Enabled", off_text="Disabled")
toggle.pack(side=tk.RIGHT)
toggle.label.pack(side=tk.RIGHT, padx=(6, 0))
```

---

## 12. Subprocess Patterns

### 12.1 yt-dlp Command Building

```python
cmd = self._get_base_cmd()          # ["yt-dlp", "--ignore-config", ...]
cmd.extend(self._get_cookie_args()) # ["--cookies-from-browser", b], ["--cookies", path], or []
cmd.extend(["-f", format_spec, ...])
cmd.extend(["--", url])             # URL always after "--" separator
```

### 12.2 Base Command

```python
def _get_base_cmd(self):
    cmd = [find_ytdlp(), "--ignore-config", "--remote-components", "ejs:github"]
    ffmpeg = find_ffmpeg()
    if ffmpeg:
        cmd.extend(["--ffmpeg-location", ffmpeg])
    # ONE FLAG PER RUNTIME. --js-runtimes takes a single RUNTIME[:PATH] and is
    # repeatable; a comma-joined list is read as ONE runtime with a nonsense
    # path, which leaves yt-dlp with no JS runtime at all and silently drops
    # every format behind YouTube's n challenge.
    self._ensure_runtime_cache()
    for runtime in self._cached_runtimes:
        cmd.extend(["--js-runtimes", runtime])
    return cmd
```

The comma-joined form `",".join(runtimes)` is what this section used to show,
and SNAT-0043 measured it as broken: `quickjs:<path>,node` yielded 4 formats
and 0 with video, against 37 and 25 for the repeated-flag form. The runtimes
this project probes are `deno`, `node`, `quickjs` and `bun`, and the bundled
`qjs` is passed as `quickjs:<path>` — `scripts/fetch-binaries.sh` and
`pyinstaller.spec` both ship it on the strength of that mechanism working.

### 12.3 Cookie Strategy

Priority order, as `cookies.get_cookie_args` implements it:
1. A selected browser wins — `--cookies-from-browser <browser>`, for **every**
   browser including Firefox.
2. Only when no browser is selected (`"none"`) is the cached `cookies.txt`
   used, via `--cookies <path>`.
3. Otherwise no cookie arguments at all.

Firefox SQLite extraction is not a step in this chain. `extract_browser_cookies`
is the explicit "refresh cookies" action, which *writes* `cookies.txt`; that
file is then ignored until the browser selection is set back to `none`.

---

## 13. Testing & Verification

### 13.1 Compilation Check

```bash
python -m py_compile snatch/app.py
python -m py_compile snatch/theme.py
# ... etc for each module
```

### 13.2 Import Verification

```python
from snatch.app import SnatchApp
print([c.__name__ for c in SnatchApp.__mro__])
# ['SnatchApp', 'DownloadTabMixin', 'SearchTabMixin', ...]
```

### 13.3 Runtime Verification

```bash
python snatch.py   # Launch the GUI
```

---

## 14. File I/O Conventions

| File | Location | Permissions | Format |
|------|----------|-------------|--------|
| `config.json` | See below | `0o600` | JSON (2-space indent) |
| `history.json` | See below | `0o600` | JSON array (2-space indent) |
| `cookies.txt` | See below | `0o600` | Netscape cookie format |

**Location is decided by `platform_utils.app_data_dir()`, not by this table.**
Running from source it is the project root. In a packaged build it is not:

| Build | Directory | Why |
|-------|-----------|-----|
| Windows `.exe` | Alongside the executable | Keeps the app portable. |
| macOS `.app` | `~/Library/Application Support/Snatch` | Writing inside the bundle breaks on upgrade and on a read-only mount. |
| Linux AppImage | `$XDG_DATA_HOME/snatch` | `sys.executable` is a temp dir that is deleted on exit. |

**Never treat the containing directory as private.** `_ensure_dir` passes
`mode=0o700` to `os.makedirs`, which applies only when the directory is
created — a directory that already exists keeps its mode, which is the normal
case after first launch. The Windows and source branches do not call it at all.
So the per-file `0o600` is the only permission guarantee on every branch, and
on Windows not even that: POSIX mode bits are not the access-control mechanism
there, and a file that must be private on Windows needs ACL work this document
does not cover.
