"""History tab UI and download history management"""

import os
import json
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

from ..utils import clear_treeview, write_private_json
from ..platform_utils import open_path


class HistoryTabMixin:
    """Mixin providing the History tab UI and logic."""

    MAX_HISTORY_ENTRIES = 200
    _history_cache = None  # In-memory cache to avoid repeated disk reads

    def _create_history_tab(self, parent):
        """Build the download history tab"""
        # Buttons
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X, pady=(0, 12))

        ttk.Button(btn_frame, text="Open File", command=self._history_open_file,
                   style="Small.TButton").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_frame, text="Open Folder", command=self._history_open_folder,
                   style="Small.TButton").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_frame, text="Clear History", command=self._clear_history,
                   style="Small.TButton").pack(side=tk.RIGHT)

        # History Treeview
        h_columns = ("date", "title", "format", "path")
        self.history_tree = ttk.Treeview(parent, columns=h_columns, show="headings", height=20)
        self.history_tree.heading("date", text="Date")
        self.history_tree.heading("title", text="Title")
        self.history_tree.heading("format", text="Format")
        self.history_tree.heading("path", text="Path")
        self.history_tree.column("date", width=140, minwidth=100)
        self.history_tree.column("title", width=300, minwidth=150)
        self.history_tree.column("format", width=80, minwidth=50)
        self.history_tree.column("path", width=250, minwidth=100)

        self.history_tree.bind("<Double-1>", lambda e: self._history_open_file())

        h_scroll = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=h_scroll.set)

        self.history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        h_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Load existing history
        self._load_history_into_tree()

    # ── History helpers ──────────────────────────────────────────────

    def _load_history(self):
        """Load history from cache or JSON file"""
        if self._history_cache is not None:
            return self._history_cache
        # Nothing here may raise. _load_history_into_tree calls this from
        # _create_history_tab, which runs inside SnatchApp.__init__ — so an
        # unreadable or malformed history.json used to stop the app launching
        # at all, with no UI route to repair it. Only FileNotFoundError and
        # JSONDecodeError were caught; PermissionError, UnicodeDecodeError,
        # IsADirectoryError and valid-but-wrong-shaped JSON all escaped.
        self._history_cache = []
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            return self._history_cache
        # ValueError above covers JSONDecodeError and UnicodeDecodeError.
        # A bare 5 or {"a": 1} parses fine and then breaks the consumers, so
        # the shape is checked rather than assumed.
        if isinstance(data, list):
            self._history_cache = [e for e in data if isinstance(e, dict)]
        return self._history_cache

    def _save_history(self, history):
        """Save history to disk, then update the cache. Reports a failure.

        The order matters: the cache used to be assigned first, so a failed
        write left memory and disk disagreeing and the user looking at a
        healthy list that was not saved. And the failure was swallowed
        entirely, so both callers reported success.
        """
        try:
            write_private_json(self.history_file, history)
        except OSError as exc:
            if hasattr(self, "status_var"):
                self.status_var.set(f"Could not save history: {exc.strerror or exc}")
            return
        self._history_cache = history

    def _add_history_entry(self, title, url, fmt, path):
        """Add a new download to history"""
        history = self._load_history()
        entry = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "title": title or "Unknown",
            "url": url,
            "format": fmt,
            "path": path,
        }
        history.insert(0, entry)
        history = history[:self.MAX_HISTORY_ENTRIES]
        self._save_history(history)
        self._load_history_into_tree()

    def _load_history_into_tree(self):
        """Populate the history treeview from cached history"""
        if not hasattr(self, "history_tree"):
            return
        clear_treeview(self.history_tree)
        history = self._load_history()
        for entry in history:
            self.history_tree.insert("", tk.END, values=(
                entry.get("date", ""),
                entry.get("title", ""),
                entry.get("format", ""),
                entry.get("path", ""),
            ))

    @staticmethod
    def _safe_resolve_path(path):
        """Resolve a path to its real location, rejecting suspicious paths"""
        if not path:
            return None
        resolved = os.path.realpath(path)
        # Reject paths that resolve outside the filesystem root (shouldn't happen)
        # or contain null bytes
        if "\x00" in resolved:
            return None
        return resolved

    def _history_open_file(self):
        """Open the selected history entry's location"""
        sel = self.history_tree.selection()
        if not sel:
            messagebox.showinfo("Info", "Select a history entry first")
            return
        item = self.history_tree.item(sel[0])
        path = str(item["values"][3]) if len(item["values"]) > 3 else ""
        resolved = self._safe_resolve_path(path)
        if resolved and os.path.isfile(resolved):
            open_path(resolved)
        elif resolved and os.path.isdir(resolved):
            open_path(resolved)
        else:
            messagebox.showwarning("Not Found", f"Path not found:\n{path}")

    def _history_open_folder(self):
        """Open folder for selected history entry"""
        sel = self.history_tree.selection()
        if not sel:
            messagebox.showinfo("Info", "Select a history entry first")
            return
        item = self.history_tree.item(sel[0])
        path = str(item["values"][3]) if len(item["values"]) > 3 else ""
        resolved = self._safe_resolve_path(path)
        # path may be a file or directory — get the containing folder if it's a file
        if resolved and os.path.isfile(resolved):
            resolved = os.path.dirname(resolved)
        if resolved and os.path.isdir(resolved):
            open_path(resolved)
        else:
            messagebox.showwarning("Not Found", f"Folder not found:\n{path}")

    def _clear_history(self):
        """Clear all download history"""
        if messagebox.askyesno("Clear History", "Delete all download history?"):
            self._save_history([])  # Also updates cache
            self._load_history_into_tree()
