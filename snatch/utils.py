"""Shared utility functions"""

import subprocess


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
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
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
