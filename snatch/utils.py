"""Shared utility functions"""

import contextlib
import os
import json
import stat
import subprocess
import tempfile

from .platform_utils import is_windows

# zenity blocks until the user picks a file or cancels, so this bounds how
# long a dialog may sit open, not any work Snatch is doing.
ZENITY_DIALOG_TIMEOUT_SEC = 300


@contextlib.contextmanager
def atomic_private_write(path):
    """Write `path` atomically, owner-only (0o600), yielding a text handle.

    Replaces `os.open(path, O_WRONLY | O_CREAT | O_TRUNC, 0o600)`, which was
    used for config.json, cookies.txt and history.json and does not deliver
    what those three need.

    The mode argument applies ONLY when the file is created. An existing file
    -- from an older build, a restore, a copy -- keeps whatever bits it
    already had, so the 0o600 that CLAUDE.md states as a guarantee for all
    user data files was merely usual. Here the content is written to a fresh
    temp file whose mode is set explicitly, and os.replace installs that
    inode, so the permissions hold whatever the target was.

    O_TRUNC also empties the target before the new content arrives, so a
    failure part-way (disk full, quota) left a truncated file where a
    complete one had been -- and for history.json that truncation then read
    back as "no history" and was overwritten on the next save. Nothing is
    destroyed here until a complete file is ready to take its place.

    The temp file is created in the target's own directory because os.replace
    is atomic only within one filesystem. Encoding is explicit: the callers
    were text-mode with no `encoding=`, so the locale decided, and a non-ASCII
    cookie value raised UnicodeEncodeError under LC_ALL=C.
    """
    directory = os.path.dirname(os.path.abspath(path)) or "."
    fd, tmp = tempfile.mkstemp(
        prefix="." + os.path.basename(path) + "-", dir=directory)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            yield handle
        os.replace(tmp, path)
        tmp = None
    finally:
        if tmp is not None:
            try:
                os.unlink(tmp)
            except OSError:
                pass


def write_private_json(path, data):
    """Serialise `data` to `path` via atomic_private_write. Raises on failure."""
    with atomic_private_write(path) as handle:
        json.dump(data, handle, indent=2)


# Files inside app_data_dir() that hold user data and must be owner-only.
PRIVATE_DATA_FILES = ("config.json", "history.json", "cookies.txt")
PRIVATE_MODE = 0o600


def tighten_user_data_permissions(directory):
    """Chmod the user data files in `directory` to 0o600. Returns names fixed.

    atomic_private_write guarantees the mode only for a file that is SAVED.
    A file that is never written again keeps whatever bits it already had --
    which is how these got loose: the original os.open form set a mode that
    applies only on creation, so every file that predates it stayed 0o644 or
    0o664 forever. It also catches a file copied in from an older install,
    which is how the ones measured on 2026-08-19 arrived.

    Skipped on Windows: POSIX mode bits are not the access-control mechanism
    there, S_IMODE never reads back 0o600, so the pass would chmod on every
    startup and never converge.

    Symlinks are skipped rather than followed -- chmod follows a link, so
    following one would re-mode a file outside the data directory.

    Never raises: this runs at startup, and a permission pass that stops the
    app launching is worse than the mode it was fixing.
    """
    if is_windows():
        return []
    fixed = []
    for name in PRIVATE_DATA_FILES:
        path = os.path.join(directory, name)
        try:
            info = os.lstat(path)
        except OSError:
            continue
        if not stat.S_ISREG(info.st_mode):
            continue
        if stat.S_IMODE(info.st_mode) == PRIVATE_MODE:
            continue
        try:
            os.chmod(path, PRIVATE_MODE)
        except OSError:
            continue
        fixed.append(name)
    return fixed

def format_duration(seconds):
    """Format seconds into H:MM:SS or M:SS string"""
    if not seconds:
        return "?"
    total = int(seconds)
    mins, secs = divmod(total, 60)
    hours, mins = divmod(mins, 60)
    if hours:
        return f"{hours}:{mins:02d}:{secs:02d}"
    return f"{mins}:{secs:02d}"


def format_filesize(size_bytes):
    """Format byte count into human-readable string"""
    if not size_bytes:
        return "Unknown"
    if size_bytes > 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
    if size_bytes > 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    if size_bytes > 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes} B"


def format_view_count(views):
    """Format view count into compact string (e.g. 1.2M, 3.4K)"""
    if not views:
        return "?"
    if views >= 1_000_000:
        return f"{views / 1_000_000:.1f}M"
    if views >= 1_000:
        return f"{views / 1_000:.1f}K"
    return str(views)


def zenity_file_dialog(*, directory=False, initial_dir="", title="", file_filter=None):
    """Show a zenity file dialog, returns selected path or None.
    Falls back to None if zenity is not available (caller should use tkinter fallback).
    """
    cmd = ["zenity", "--file-selection", "--filename", initial_dir + "/", "--title", title]
    if directory:
        cmd.append("--directory")
    if file_filter:
        for f in file_filter:
            cmd.extend(["--file-filter", f])
    try:
        result = subprocess.run(cmd, capture_output=True, text=True,
                                timeout=ZENITY_DIALOG_TIMEOUT_SEC)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def clear_treeview(tree):
    """Bulk-delete all items from a ttk.Treeview"""
    children = tree.get_children()
    if children:
        tree.delete(*children)
