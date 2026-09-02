> **Historical — this plan was executed and SNAT-0001 shipped.** Kept as the
> record of how the Windows build was designed, not as work to do. Two things
> have moved since it was written: the package was renamed from `ytdlp_gui` to
> `snatch` (SNAT-0002), so every path below uses the old name; and the build is
> now driven by `scripts/build-windows.sh` called from `.github/workflows/ci.yml`,
> not by a per-platform workflow. Moved here from `docs/superpowers/plans/` on
> 2026-09-02 per CLAUDE.md 14a, which puts a plan at `docs/plans/<ID>-<topic>.md`.

# Windows One-File Build Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a single self-contained `ytdlp-gui.exe` for Windows that bundles Python, all libraries, `yt-dlp.exe`, and `ffmpeg.exe` — runnable on any Windows 10/11 machine with nothing pre-installed.

**Architecture:** Centralize all Linux-specific code (subprocess targets, file-open helpers, app-data paths) into a new `ytdlp_gui/platform_utils.py` module so the rest of the codebase calls platform-aware helpers instead of hardcoded `xdg-open` / `"yt-dlp"` / `__file__`. The Windows build is produced by PyInstaller `--onefile` running on a GitHub Actions `windows-latest` runner; bundled binaries are downloaded by the workflow at build time. App data (config, history, cookies, downloads) lives next to the `.exe` so the friend can move/copy it freely.

**Tech Stack:** Python 3.12, tkinter, Pillow, tkinterdnd2, PyInstaller 6.x, GitHub Actions (`windows-latest`).

**Constraints from `CLAUDE.md`:**
- Surgical edits — no drive-by reformat in untouched files (§11).
- Reuse `script_dir` pattern already in `app.py`; do not invent parallel path-resolution everywhere (§3).
- Shortest correct implementation — no pytest infrastructure added (project has none today); verify with a single smoke-test script (§2).
- Layman-friendly messages in any new dialogs (global CLAUDE.md §0).

---

## File Structure

**Files created:**
- `ytdlp_gui/platform_utils.py` — single source of truth for platform-aware paths and helpers (`app_data_dir`, `resource_path`, `find_ytdlp`, `find_ffmpeg`, `open_path`, `is_windows`, `is_frozen`).
- `ytdlp_gui/__init__.py` — add `__version__` constant (one line).
- `requirements.txt` — pinned runtime deps for reproducible builds.
- `pyinstaller.spec` — PyInstaller one-file spec (icon, hidden imports, bundled binaries, no-console mode).
- `.github/workflows/build-windows.yml` — Windows builder; uploads `.exe` as a workflow artifact, attaches to a release on tag push.
- `scripts/verify_platform_utils.py` — manual smoke-test script for the helpers (prints resolved values for the current platform; no pytest required).
- `docs/windows-build.md` — engineer's guide to triggering and downloading the build.

**Files modified:**
- `ytdlp_gui/app.py` — `script_dir` now sourced from `platform_utils.app_data_dir()`.
- `ytdlp_gui/downloader.py` — `_get_base_cmd()` uses `find_ytdlp()`; pass `--ffmpeg-location` from `find_ffmpeg()`; replace Linux-only JS-runtime install message with a cross-platform one.
- `ytdlp_gui/player.py` — guard `os.getuid()` mpv-socket check behind `is_windows()`; switch `xdg-open` to `open_path()`.
- `ytdlp_gui/version.py` — disable the in-app yt-dlp updater on Windows (the bundled binary is shipped with each release of the GUI).
- `ytdlp_gui/tabs/download.py` — replace three `xdg-open` calls with `open_path()`.
- `ytdlp_gui/tabs/history.py` — replace three `xdg-open` calls with `open_path()`.
- `ytdlp_gui/tabs/search.py` — yt-dlp command uses `find_ytdlp()` + `--ffmpeg-location`.
- `ytdlp_gui/tabs/media_info.py` — yt-dlp command uses `find_ytdlp()` + `--ffmpeg-location`.
- `README.md` — add a "Download for Windows" section pointing at the release artifact.

---

## Phase 1 — Cross-platform code fixes

### Task 1: Create `platform_utils.py` with all platform-aware helpers

**Files:**
- Create: `ytdlp_gui/platform_utils.py`

- [ ] **Step 1: Write the module**

Create `ytdlp_gui/platform_utils.py` with this exact content:

```python
"""Platform-aware helpers — paths, binary resolution, file-open.

When running from source (dev mode), behaves identically to the pre-existing
Linux logic so nothing regresses. When frozen by PyInstaller (Windows .exe),
resolves bundled binaries from sys._MEIPASS and writes user data next to the
.exe itself rather than into the temp-extraction directory.
"""

import os
import shutil
import subprocess
import sys


def is_windows():
    return sys.platform == "win32"


def is_macos():
    return sys.platform == "darwin"


def is_frozen():
    """True when running inside a PyInstaller bundle."""
    return getattr(sys, "frozen", False)


def app_data_dir():
    """Directory for user data (config.json, history.json, cookies.txt, downloads).

    Frozen .exe: the directory containing the .exe — user data lives next to it.
    Dev mode: the project root (same as the previous script_dir behaviour).
    """
    if is_frozen():
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def resource_path(*parts):
    """Locate a bundled read-only resource (icon, binary, data file).

    Frozen: sys._MEIPASS is PyInstaller's runtime extraction dir.
    Dev: project root.
    """
    if is_frozen():
        base = sys._MEIPASS  # noqa: SLF001 — PyInstaller's documented API
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *parts)


def _find_bundled_binary(name):
    """Return the path to a bundled binary if present, else None.

    Looks in <_MEIPASS>/bin/<name>(.exe) when frozen.
    """
    if not is_frozen():
        return None
    candidate = resource_path("bin", name + (".exe" if is_windows() else ""))
    if os.path.isfile(candidate):
        return candidate
    return None


def find_ytdlp():
    """Resolve the yt-dlp binary. Bundled copy wins; otherwise falls back to PATH."""
    bundled = _find_bundled_binary("yt-dlp")
    if bundled:
        return bundled
    on_path = shutil.which("yt-dlp")
    if on_path:
        return on_path
    return "yt-dlp"  # last-resort literal — subprocess will surface FileNotFoundError


def find_ffmpeg():
    """Resolve ffmpeg. Returns None if not found (caller should omit --ffmpeg-location)."""
    bundled = _find_bundled_binary("ffmpeg")
    if bundled:
        return bundled
    return shutil.which("ffmpeg")


def open_path(target):
    """Open a file, folder, or URL in the OS default handler.

    Cross-platform replacement for `subprocess.Popen(["xdg-open", "--", target])`.
    Safe against argument injection — uses os.startfile on Windows (no shell)
    and the dedicated openers on macOS/Linux with `--` separator.
    """
    if is_windows():
        # os.startfile is the Windows-native way; honours file associations.
        os.startfile(target)  # noqa: S606 — intentional, Windows-only API
        return
    if is_macos():
        subprocess.Popen(["open", "--", target])
        return
    subprocess.Popen(["xdg-open", "--", target])
```

- [ ] **Step 2: Run the smoke-test script (created in Task 2) on Linux**

(Skip this verification step for now — script is created in the next task; verify the module compiles instead.)

Run: `python3 -m py_compile ytdlp_gui/platform_utils.py`
Expected: no output (clean compile).

- [ ] **Step 3: Commit**

```bash
git add ytdlp_gui/platform_utils.py
git commit -m "Add platform_utils module for cross-platform paths and binary resolution"
```

---

### Task 2: Add smoke-test script for `platform_utils`

**Files:**
- Create: `scripts/verify_platform_utils.py`

- [ ] **Step 1: Write the smoke-test**

Create `scripts/verify_platform_utils.py` with this content:

```python
#!/usr/bin/env python3
"""Prints what platform_utils resolves on the current platform.

Run on Linux before pushing: confirms the dev-mode path resolution still
matches the pre-existing behaviour (same project root, same yt-dlp on PATH).
Run inside the GitHub Actions Windows build (post-PyInstaller, against the
.exe via `--add-data`): confirms bundled binaries are found.
"""

import os
import sys

# Allow running from project root without installing the package.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ytdlp_gui import platform_utils as pu


def main():
    print("platform        :", sys.platform)
    print("is_windows      :", pu.is_windows())
    print("is_macos        :", pu.is_macos())
    print("is_frozen       :", pu.is_frozen())
    print("app_data_dir    :", pu.app_data_dir())
    print("resource_path() :", pu.resource_path("icon.png"))
    print("find_ytdlp      :", pu.find_ytdlp())
    print("find_ffmpeg     :", pu.find_ffmpeg())
    print()

    # Sanity asserts — fail loud if something looks wrong.
    assert os.path.isdir(pu.app_data_dir()), "app_data_dir must exist"
    if pu.is_frozen():
        assert pu.find_ytdlp() != "yt-dlp", \
            "frozen build must resolve yt-dlp to a real path (bundled or PATH)"
    print("OK")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run it on Linux to confirm no regression**

```bash
cd /mnt/Games/Scripts/Linux/YT-DLP_FrontEnd
python3 scripts/verify_platform_utils.py
```

Expected output (paths will vary):
```
platform        : linux
is_windows      : False
is_macos        : False
is_frozen       : False
app_data_dir    : /mnt/Games/Scripts/Linux/YT-DLP_FrontEnd
resource_path() : /mnt/Games/Scripts/Linux/YT-DLP_FrontEnd/icon.png
find_ytdlp      : /usr/local/bin/yt-dlp  (or wherever it's installed)
find_ffmpeg     : /usr/bin/ffmpeg  (or None if not installed)

OK
```

If `app_data_dir` doesn't match the project root, stop and re-check `platform_utils.app_data_dir()`.

- [ ] **Step 3: Commit**

```bash
git add scripts/verify_platform_utils.py
git commit -m "Add verify_platform_utils.py smoke-test"
```

---

### Task 3: Switch `app.py` to use `app_data_dir()`

**Files:**
- Modify: `ytdlp_gui/app.py:43`

- [ ] **Step 1: Read the current code**

Open `ytdlp_gui/app.py` and locate the `script_dir` assignment near line 43:

```python
self.script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
```

- [ ] **Step 2: Edit to use the helper**

Add the import (top of file, with the other relative imports):

```python
from .platform_utils import app_data_dir
```

Replace the `script_dir` line with:

```python
self.script_dir = app_data_dir()
```

Leave every downstream `os.path.join(self.script_dir, ...)` exactly as it is — those work unchanged.

- [ ] **Step 3: Verify**

```bash
python3 -m py_compile ytdlp_gui/app.py
python3 scripts/verify_platform_utils.py
python3 ytdlp_gui.py &
# Open the app, click around (Download tab loads, History tab loads, Settings persist).
# Close the app, confirm config.json / history.json are still next to ytdlp_gui.py.
```

Expected: app launches and behaves identically to before. `config.json` and `history.json` modification times update normally.

- [ ] **Step 4: Commit**

```bash
git add ytdlp_gui/app.py
git commit -m "Use platform_utils.app_data_dir() for script_dir"
```

---

### Task 4: Replace all `xdg-open` calls with `open_path()`

**Files:**
- Modify: `ytdlp_gui/player.py:36`
- Modify: `ytdlp_gui/tabs/download.py:375,377,381`
- Modify: `ytdlp_gui/tabs/history.py:129,131,148`

- [ ] **Step 1: Add the import to each file**

In `ytdlp_gui/player.py`, after the existing relative imports, add:
```python
from .platform_utils import open_path
```

In `ytdlp_gui/tabs/download.py` and `ytdlp_gui/tabs/history.py`, add (matching the existing relative-import style — these files are one level deeper):
```python
from ..platform_utils import open_path
```

- [ ] **Step 2: Replace the calls — `player.py`**

Find:
```python
subprocess.Popen(["xdg-open", "--", url])
```
Replace with:
```python
open_path(url)
```

- [ ] **Step 3: Replace the calls — `tabs/download.py`**

Three call sites near lines 375, 377, 381. Each looks like:
```python
subprocess.Popen(["xdg-open", "--", <something>])
```
Replace each with:
```python
open_path(<something>)
```
Preserve the surrounding logic that picks between `resolved`, `os.path.dirname(resolved)`, and `fallback`.

- [ ] **Step 4: Replace the calls — `tabs/history.py`**

Three call sites near lines 129, 131, 148. Same substitution as Step 3.

- [ ] **Step 5: Verify the substitutions are total**

```bash
grep -rn "xdg-open" ytdlp_gui/
```
Expected: no matches.

```bash
python3 -m py_compile ytdlp_gui/player.py ytdlp_gui/tabs/download.py ytdlp_gui/tabs/history.py
```
Expected: no output.

- [ ] **Step 6: Smoke-test on Linux**

Launch the app, download a short clip, click "Open file" and "Open folder" — both should still work via `xdg-open` (because `open_path()` delegates to it on Linux). In the History tab, double-click an entry — same.

- [ ] **Step 7: Commit**

```bash
git add ytdlp_gui/player.py ytdlp_gui/tabs/download.py ytdlp_gui/tabs/history.py
git commit -m "Replace xdg-open calls with cross-platform open_path()"
```

---

### Task 5: Guard `os.getuid()` mpv-socket check on Windows

**Files:**
- Modify: `ytdlp_gui/player.py:49`

- [ ] **Step 1: Read the current code**

The current check (around line 49) is:
```python
if not os.path.isdir(runtime_dir) or os.stat(runtime_dir).st_uid != os.getuid():
    # fall back to xdg-open
```

`os.getuid()` does not exist on Windows — it will raise `AttributeError`. Even reaching this branch on Windows means mpv is on PATH, which is rare; but if it does, we want a clean fallback, not a crash.

- [ ] **Step 2: Edit to guard the uid check**

Add `is_windows` to the existing `platform_utils` import:
```python
from .platform_utils import open_path, is_windows
```

Change the conditional to skip the uid check on Windows (the entire socket-handling block is Linux-only design; on Windows we should fall through to the URL-handler path):

```python
if is_windows() or not os.path.isdir(runtime_dir) or os.stat(runtime_dir).st_uid != os.getuid():
    # fall back to open_path (URL → default handler on Windows, browser on Linux)
```

(Keep the rest of the function body unchanged. The fallback already exists.)

- [ ] **Step 3: Verify Linux behaviour is unchanged**

```bash
python3 -m py_compile ytdlp_gui/player.py
python3 ytdlp_gui.py
# In the Search tab, find a video and click play — mpv should still open if installed.
```
Expected: identical Linux behaviour. (We added `is_windows() or ...` — short-circuit means the uid check still runs on Linux.)

- [ ] **Step 4: Commit**

```bash
git add ytdlp_gui/player.py
git commit -m "Guard os.getuid() mpv-socket check from Windows AttributeError"
```

---

### Task 6: Use `find_ytdlp()` and `--ffmpeg-location` everywhere yt-dlp is invoked

**Files:**
- Modify: `ytdlp_gui/downloader.py:62`
- Modify: `ytdlp_gui/tabs/search.py:273` area
- Modify: `ytdlp_gui/tabs/media_info.py:107` area
- Modify: `ytdlp_gui/version.py:28,143` (read-only `--version` calls only; update block handled in Task 7)

- [ ] **Step 1: Add the helper to `downloader.py`'s base command builder**

In `ytdlp_gui/downloader.py`, add the import:
```python
from .platform_utils import find_ytdlp, find_ffmpeg
```

Replace `_get_base_cmd` (around line 60) with:
```python
def _get_base_cmd(self):
    """Build the base yt-dlp command with JS runtime + ffmpeg detection."""
    cmd = [find_ytdlp(), "--ignore-config", "--remote-components", "ejs:github"]
    ffmpeg = find_ffmpeg()
    if ffmpeg:
        cmd.extend(["--ffmpeg-location", ffmpeg])
    self._ensure_runtime_cache()
    if self._cached_runtimes:
        cmd.extend(["--js-runtimes", ",".join(self._cached_runtimes)])
    return cmd
```

This single change flows through to every yt-dlp invocation that uses `_get_base_cmd()` (download, format-fetch).

- [ ] **Step 2: Update `tabs/search.py`**

Find the yt-dlp command construction near line 273. It currently begins:
```python
cmd = ["yt-dlp", ...]
```
Add the import at the top of the file:
```python
from ..platform_utils import find_ytdlp
```
And replace the literal `"yt-dlp"` with `find_ytdlp()`.

(Search doesn't need ffmpeg — it only fetches JSON metadata.)

- [ ] **Step 3: Update `tabs/media_info.py`**

Find the yt-dlp command construction near line 107. Same substitution as Step 2:
```python
from ..platform_utils import find_ytdlp
# ...
cmd = [find_ytdlp(), ...]
```

- [ ] **Step 4: Update `version.py` (version-check only — update logic handled in Task 7)**

In `ytdlp_gui/version.py`, add:
```python
from .platform_utils import find_ytdlp
```
Replace both `subprocess.run(["yt-dlp", "--version"], ...)` (lines ~28 and ~143) with:
```python
subprocess.run([find_ytdlp(), "--version"], ...)
```

- [ ] **Step 5: Verify**

```bash
grep -rn '"yt-dlp"\|'\''yt-dlp'\''' ytdlp_gui/
```
Expected: zero matches (every literal has been replaced).

```bash
python3 -m py_compile ytdlp_gui/downloader.py ytdlp_gui/tabs/search.py ytdlp_gui/tabs/media_info.py ytdlp_gui/version.py
python3 ytdlp_gui.py
# Smoke test: paste a URL, fetch formats, download one.
```
Expected: identical Linux behaviour. (On Linux, `find_ytdlp()` returns the same `shutil.which("yt-dlp")` path as before.)

- [ ] **Step 6: Commit**

```bash
git add ytdlp_gui/downloader.py ytdlp_gui/tabs/search.py ytdlp_gui/tabs/media_info.py ytdlp_gui/version.py
git commit -m "Resolve yt-dlp/ffmpeg via platform_utils for bundled-binary support"
```

---

### Task 7: Disable in-app yt-dlp updater on Windows

**Files:**
- Modify: `ytdlp_gui/version.py` — `_update_ytdlp_thread` and surrounding update-button wiring.
- Modify: `ytdlp_gui/version.py` — `_show_update_available` (skip prompting on Windows).

The Windows .exe ships with a fixed `yt-dlp.exe` baked into the bundle. Users update yt-dlp by downloading a new release of the GUI. The Linux update path (download + `pkexec install`) doesn't translate to Windows and shouldn't try.

- [ ] **Step 1: Add the import**

In `ytdlp_gui/version.py`:
```python
from .platform_utils import find_ytdlp, is_windows
```
(extend the existing platform_utils import from Task 6).

- [ ] **Step 2: Guard the update-prompt at the entry point**

Replace `_show_update_available` (around the existing definition) with:
```python
def _show_update_available(self):
    """Show update available button and prompt user (Linux only)."""
    if is_windows():
        # Bundled yt-dlp.exe is shipped with each GUI release — the user
        # updates by downloading a new ytdlp-gui.exe. Show a passive label
        # only; don't prompt or wire the update button to run pkexec/curl.
        self.update_btn.config(
            text=f"v{self.latest_version} available — download new GUI",
            state=tk.DISABLED,
        )
        self.status_var.set(
            f"yt-dlp {self.latest_version} is out — grab the latest "
            f"ytdlp-gui.exe from GitHub Releases to update."
        )
        return

    self.update_btn.config(text=f"Update to {self.latest_version}", state=tk.NORMAL)
    self.status_var.set(f"Update available: {self.current_version} -> {self.latest_version}")

    if messagebox.askyesno("Update Available",
                           f"A new version of yt-dlp is available!\n\n"
                           f"Current: {self.current_version}\n"
                           f"Latest: {self.latest_version}\n\n"
                           f"Would you like to update now?"):
        self._do_update()
```

- [ ] **Step 3: Guard `update_ytdlp` (the button callback) too**

Defensive — even if the button somehow becomes clickable on Windows, the callback should refuse. Replace `update_ytdlp` with:
```python
def update_ytdlp(self):
    """Update yt-dlp to latest version (called from button)."""
    if is_windows():
        messagebox.showinfo(
            "Update via GUI download",
            "On Windows, yt-dlp is bundled inside this app.\n\n"
            "To update, download the latest ytdlp-gui.exe from\n"
            "https://github.com/milnet01/ytdlp-gui/releases"
        )
        return
    if self.latest_version:
        if messagebox.askyesno("Update yt-dlp",
                               f"Update yt-dlp to version {self.latest_version}?\n\n"
                               f"You may be prompted for your password."):
            self._do_update()
```

- [ ] **Step 4: Verify Linux behaviour**

```bash
python3 -m py_compile ytdlp_gui/version.py
python3 ytdlp_gui.py
# Click "Check version" — the update prompt should appear exactly as before.
```

- [ ] **Step 5: Commit**

```bash
git add ytdlp_gui/version.py
git commit -m "Skip pkexec/curl update flow on Windows; surface 'download new GUI' instead"
```

---

### Task 8: Cross-platform JS-runtime warning

**Files:**
- Modify: `ytdlp_gui/downloader.py:89-101` — `_warn_no_jsruntime`

The current warning gives `curl … sh` and `apt install` install commands. Those are Linux-only. On Windows yt-dlp.exe usually solves YouTube challenges without a separate runtime, but if the warning does fire (mostly on older Windows machines), we should not tell the user to run `apt`.

- [ ] **Step 1: Add import**

In `ytdlp_gui/downloader.py`, extend the existing `platform_utils` import:
```python
from .platform_utils import find_ytdlp, find_ffmpeg, is_windows
```

- [ ] **Step 2: Edit the warning**

Replace `_warn_no_jsruntime` with:
```python
def _warn_no_jsruntime(self):
    """Show warning about missing JavaScript runtime."""
    self.status_var.set("No JS runtime found - required for YouTube downloads")
    if is_windows():
        body = (
            "No JavaScript runtime found.\n\n"
            "YouTube may require Node.js or Deno to solve challenges.\n\n"
            "If YouTube downloads fail with a 'sig' or 'nsig' error, install\n"
            "Node.js from https://nodejs.org/ (the LTS installer is fine),\n"
            "then restart this app."
        )
    else:
        body = (
            "No JavaScript runtime found.\n\n"
            "YouTube requires Deno or Node.js to solve challenges.\n\n"
            "Install Deno (recommended):\n"
            "curl -fsSL https://deno.land/install.sh | sh\n\n"
            "Or install Node.js:\n"
            "sudo apt install nodejs\n\n"
            "Then restart this app."
        )
    messagebox.showwarning("JavaScript Runtime Required", body)
```

- [ ] **Step 3: Verify**

```bash
python3 -m py_compile ytdlp_gui/downloader.py
```
Expected: no output.

- [ ] **Step 4: Commit**

```bash
git add ytdlp_gui/downloader.py
git commit -m "Cross-platform JS-runtime warning text"
```

---

### Task 9: Set `__version__` and run full Linux smoke-test

**Files:**
- Modify: `ytdlp_gui/__init__.py`

- [ ] **Step 1: Add the version constant**

In `ytdlp_gui/__init__.py`, after the existing `HAS_DND` / `HAS_MPV` block, add:
```python
__version__ = "0.1.0"
```

(This is referenced by the PyInstaller spec in Task 11 and surfaced as the .exe's file-version metadata.)

- [ ] **Step 2: Full regression smoke-test on Linux**

```bash
python3 ytdlp_gui.py
```
- Download tab: paste a YouTube URL, fetch formats, download MP3-only and best-video — both succeed.
- Search tab: search a term, click play on a result — mpv plays it (or falls back to browser if mpv not installed).
- Media Info tab: open an existing video file, metadata loads.
- History tab: previously downloaded item shows; double-click opens it.
- Theme switcher: toggle between Dark/Nord/Monokai — no crashes, no stale colours.
- Close the app: `config.json` and `history.json` are intact next to `ytdlp_gui.py`.

If anything regresses, stop and bisect — do not proceed to Phase 2.

- [ ] **Step 3: Commit**

```bash
git add ytdlp_gui/__init__.py
git commit -m "Add __version__ = 0.1.0 for PyInstaller metadata"
```

---

## Phase 2 — Windows build pipeline

### Task 10: Create `requirements.txt`

**Files:**
- Create: `requirements.txt`

- [ ] **Step 1: Write the file**

```
# Runtime dependencies pinned for reproducible PyInstaller builds.
# Bump these together and rebuild the .exe; do not float versions.
Pillow==11.0.0
tkinterdnd2==0.4.2
yt-dlp==2024.11.18
```

Versions above are the latest stable at plan-write time (2026-05-27). Before
committing, run `pip index versions <pkg>` for each and bump to current if a
newer stable exists — per global CLAUDE.md §5/5c.

- [ ] **Step 2: Verify the pins install cleanly in a fresh venv**

```bash
python3 -m venv /tmp/yt-venv && source /tmp/yt-venv/bin/activate
pip install -r requirements.txt
python3 -c "import PIL, tkinterdnd2, yt_dlp; print('ok')"
deactivate && rm -rf /tmp/yt-venv
```
Expected: `ok`.

- [ ] **Step 3: Commit**

```bash
git add requirements.txt
git commit -m "Pin runtime deps in requirements.txt for reproducible builds"
```

---

### Task 11: Create the PyInstaller spec

**Files:**
- Create: `pyinstaller.spec`

PyInstaller `.spec` files are Python scripts that PyInstaller exec()s. This spec produces a single-file Windows .exe with bundled yt-dlp.exe + ffmpeg.exe (placed under `bin/` so `platform_utils.find_ytdlp()` finds them), the app icon, and all tkinter/Pillow/tkinterdnd2 modules.

- [ ] **Step 1: Write the spec**

Create `pyinstaller.spec` with this content:

```python
# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the Windows one-file build.

Invoked by .github/workflows/build-windows.yml after it downloads
yt-dlp.exe and ffmpeg.exe into the ./bin/ directory of the build checkout.
The .exe extracts everything to a temp dir at runtime; user data goes
next to the .exe itself via platform_utils.app_data_dir().
"""

import os
import sys

# ── Inputs ────────────────────────────────────────────────────────────
APP_NAME = "ytdlp-gui"
ENTRY = "ytdlp_gui.py"
ICON = "icon.png"  # PyInstaller converts PNG → .ico automatically on Windows.

# Bundled binaries are downloaded by the CI workflow into ./bin/ before
# this spec runs. If they're missing locally, the build still succeeds
# but produces a non-self-contained .exe that needs PATH-installed
# yt-dlp/ffmpeg — useful for dev/test, not for distribution.
BIN_DIR = "bin"
binaries = []
for name in ("yt-dlp.exe", "ffmpeg.exe"):
    path = os.path.join(BIN_DIR, name)
    if os.path.isfile(path):
        binaries.append((path, "bin"))

# Data files (icons, etc.) bundled into the .exe.
datas = [
    ("icon.png", "."),
    ("icon_48.png", "."),
    ("icon_64.png", "."),
]

# ── Analysis ──────────────────────────────────────────────────────────
a = Analysis(
    [ENTRY],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=[
        "tkinterdnd2",
        "PIL._tkinter_finder",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        # Trim unused stdlib heavyweights that PyInstaller pulls in
        # speculatively — saves ~5 MB.
        "test",
        "unittest",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,           # UPX often trips Windows Defender; not worth it.
    runtime_tmpdir=None,
    console=False,        # No console window — pure GUI.
    disable_windowed_traceback=False,
    icon="icon.png",
    version=None,         # Could embed a Windows version-info resource later.
)
```

- [ ] **Step 2: Verify the spec compiles (syntax only — full build runs in CI)**

```bash
python3 -m py_compile pyinstaller.spec
```
Expected: no output.

- [ ] **Step 3: Commit**

```bash
git add pyinstaller.spec
git commit -m "Add PyInstaller one-file spec for Windows build"
```

---

### Task 12: Create the GitHub Actions Windows-build workflow

**Files:**
- Create: `.github/workflows/build-windows.yml`

This workflow runs on every push to `main`, every tag, and on manual `workflow_dispatch`. It:
1. Checks out the repo on a `windows-latest` runner.
2. Sets up Python 3.12.
3. Installs `requirements.txt` + PyInstaller.
4. Downloads pinned `yt-dlp.exe` and `ffmpeg.exe` into `bin/`.
5. Runs PyInstaller against `pyinstaller.spec`.
6. Uploads `dist/ytdlp-gui.exe` as a workflow artifact (retained 30 days).
7. On a `v*` tag push, attaches the .exe to a GitHub Release.

- [ ] **Step 1: Write the workflow**

Create `.github/workflows/build-windows.yml`:

```yaml
name: build-windows

on:
  push:
    branches: [main]
    tags: ["v*"]
  workflow_dispatch:

jobs:
  build:
    runs-on: windows-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: "pip"

      - name: Install build dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pyinstaller==6.11.1

      - name: Download bundled yt-dlp.exe and ffmpeg.exe
        shell: pwsh
        run: |
          New-Item -ItemType Directory -Force -Path bin | Out-Null
          # yt-dlp.exe — pinned release matching requirements.txt yt-dlp version.
          $ytdlpVersion = "2024.11.18"
          Invoke-WebRequest -UseBasicParsing `
            -Uri "https://github.com/yt-dlp/yt-dlp/releases/download/$ytdlpVersion/yt-dlp.exe" `
            -OutFile "bin/yt-dlp.exe"
          # ffmpeg — pinned essentials build from gyan.dev (smaller than full).
          Invoke-WebRequest -UseBasicParsing `
            -Uri "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip" `
            -OutFile "ffmpeg.zip"
          Expand-Archive -Path ffmpeg.zip -DestinationPath ffmpeg-extract -Force
          $ffmpegExe = Get-ChildItem -Path ffmpeg-extract -Recurse -Filter ffmpeg.exe | Select-Object -First 1
          Copy-Item -Path $ffmpegExe.FullName -Destination "bin/ffmpeg.exe"
          Remove-Item -Recurse -Force ffmpeg-extract, ffmpeg.zip

      - name: Run platform_utils smoke-test
        run: python scripts/verify_platform_utils.py

      - name: Build .exe with PyInstaller
        run: pyinstaller pyinstaller.spec --clean --noconfirm

      - name: Smoke-test the built .exe (import-only — full GUI needs a desktop)
        shell: pwsh
        run: |
          if (-not (Test-Path "dist/ytdlp-gui.exe")) {
            Write-Error "dist/ytdlp-gui.exe not produced"
            exit 1
          }
          $size = (Get-Item "dist/ytdlp-gui.exe").Length / 1MB
          Write-Host ("Built ytdlp-gui.exe: {0:N1} MB" -f $size)

      - name: Upload .exe as workflow artifact
        uses: actions/upload-artifact@v4
        with:
          name: ytdlp-gui-windows
          path: dist/ytdlp-gui.exe
          retention-days: 30

      - name: Attach to GitHub Release (tag pushes only)
        if: startsWith(github.ref, 'refs/tags/v')
        uses: softprops/action-gh-release@v2
        with:
          files: dist/ytdlp-gui.exe
          fail_on_unmatched_files: true
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

- [ ] **Step 2: Verify the YAML parses**

```bash
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/build-windows.yml'))"
```
Expected: no output (clean parse).

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/build-windows.yml
git commit -m "Add GitHub Actions Windows build workflow (PyInstaller --onefile)"
```

---

### Task 13: Add Windows install docs and update README

**Files:**
- Create: `docs/windows-build.md`
- Modify: `README.md`

- [ ] **Step 1: Write `docs/windows-build.md`**

```markdown
# Building the Windows .exe

The Windows binary is produced automatically by GitHub Actions
(`.github/workflows/build-windows.yml`). You don't need a Windows machine.

## Triggering a build

- **Automatic** — every push to `main` and every `v*` tag triggers a build.
- **Manual** — go to the Actions tab on GitHub, pick "build-windows",
  click "Run workflow", choose the branch.

## Downloading the artifact

After the workflow finishes (~3-5 minutes):

1. Open the run page (Actions tab → click the latest "build-windows" run).
2. Scroll to "Artifacts" → click `ytdlp-gui-windows`.
3. A `ytdlp-gui-windows.zip` downloads; inside is `ytdlp-gui.exe`.

Artifacts are kept 30 days. Tagged releases attach the .exe to the
GitHub Release page permanently.

## What's inside the .exe

- Python 3.12 runtime (embedded)
- tkinter, Pillow, tkinterdnd2
- `bin/yt-dlp.exe` and `bin/ffmpeg.exe` (PyInstaller extracts to a temp dir at runtime)
- App icons (icon.png, icon_48.png, icon_64.png)

Expected size: ~80-120 MB.

## First-run user instructions

Send your friend the .exe and these two lines:

> Double-click `ytdlp-gui.exe`. Windows SmartScreen may show a "Windows protected your PC" dialog the first time — click **More info** → **Run anyway**. The app will create `config.json`, `history.json`, and a `Downloads` folder in the same folder as the .exe.

The SmartScreen warning is normal for unsigned binaries from small open-source projects. Removing it requires a paid code-signing certificate (~$100/year), which is overkill for personal distribution.

## Updating yt-dlp

The bundled `yt-dlp.exe` is fixed at build time. To update, push a commit that bumps `yt-dlp` in `requirements.txt` (and the matching `$ytdlpVersion` in the workflow) — the next build ships the new yt-dlp.

The in-app "Check version" button on Windows shows the latest yt-dlp release but disables the auto-update (the bundled copy can't update itself while the .exe is running; the user must download a new `ytdlp-gui.exe`).
```

- [ ] **Step 2: Add a "Download for Windows" section to README.md**

Open `README.md` and add this section after the first paragraph (before "## Features"):

```markdown
## Download for Windows

A single-file `ytdlp-gui.exe` is published on the [Releases page](https://github.com/milnet01/ytdlp-gui/releases) — no Python install needed. Double-click to run; user data is created next to the .exe. See [docs/windows-build.md](docs/windows-build.md) for build internals.
```

- [ ] **Step 3: Commit**

```bash
git add docs/windows-build.md README.md
git commit -m "Document Windows build pipeline and friend-distribution flow"
```

---

### Task 14: Trigger the first build and verify the artifact

This is the only step that requires network access and CI runtime — keep it last so it isn't repeated for every code change in Phase 1.

- [ ] **Step 1: Push the branch and trigger the workflow**

```bash
git status                          # confirm everything from Tasks 1-13 is committed
git push origin main                # public repo, no minute concern (global CLAUDE.md §6)
```

Watch the run:
```bash
gh run watch
```

Expected: green check after ~3-5 minutes.

- [ ] **Step 2: Download the artifact**

```bash
mkdir -p /tmp/ytdlp-windows && cd /tmp/ytdlp-windows
gh run download --name ytdlp-gui-windows
ls -lh ytdlp-gui.exe
file ytdlp-gui.exe
```

Expected:
- File present, ~80-120 MB.
- `file` reports `PE32+ executable for MS Windows ... GUI`.

- [ ] **Step 3: Hand off to friend for real-Windows verification**

Send the .exe to the friend (or copy to a Windows machine if available) and confirm:
1. Double-click runs the GUI with no errors.
2. Paste a YouTube URL; format dropdown populates.
3. Download a short clip — completes; `config.json`, `history.json`, downloaded file all appear next to the .exe.
4. SmartScreen warning is dismissable (More info → Run anyway).

If the friend reports a crash:
- Ask for a screenshot of any error dialog.
- Re-run the build with `console=True` in `pyinstaller.spec` temporarily and ship a debug .exe — tracebacks then print to a console window.

- [ ] **Step 4: Tag a release once verified**

```bash
git tag v0.1.0
git push origin v0.1.0
```

The workflow re-runs on the tag and attaches the .exe to a new GitHub Release at https://github.com/milnet01/ytdlp-gui/releases/tag/v0.1.0 — that's the URL to send the friend permanently.

---

## Self-Review

**Spec coverage:** Every Linux-ism found by the pre-plan grep (`xdg-open`, `os.getuid`, hardcoded `"yt-dlp"`, `pkexec`/`/usr/local/bin/yt-dlp`, `script_dir` via `__file__`, mpv socket check) has a corresponding task. The build pipeline (requirements, spec, workflow, docs) maps to Tasks 10-13, and end-to-end verification to Task 14.

**Placeholder scan:** No TBDs, no "implement later", no "handle edge cases" without code, no "similar to Task N" references. Every edit shows the exact replacement text or full block.

**Type/name consistency:** `platform_utils` helper names (`app_data_dir`, `resource_path`, `find_ytdlp`, `find_ffmpeg`, `open_path`, `is_windows`, `is_macos`, `is_frozen`) are used identically across Tasks 1, 3, 4, 5, 6, 7, 8. The PyInstaller spec drops binaries into `bin/<name>.exe` and `find_ytdlp()` / `find_ffmpeg()` look for them under `<_MEIPASS>/bin/<name>.exe` — matched.

**Risk notes:**
- ffmpeg "essentials" build from gyan.dev is a community-maintained source. If the URL breaks, swap to https://github.com/BtbN/FFmpeg-Builds (also pinned, also community).
- SmartScreen warning is a known UX wart; the README explicitly tells the friend how to dismiss it. Code-signing is deferred (out of scope for a personal-distribution build).
- PyInstaller --onefile has a ~1-2s startup delay on first launch (extracting to temp dir). Acceptable for a GUI app; not acceptable for a CLI. If startup feels too slow, switch to `--onedir` mode (folder of files instead of single .exe) in a follow-up — same spec, change `EXE(...)` to `EXE(... ) + COLLECT(...)`.
