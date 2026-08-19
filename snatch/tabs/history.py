"""History tab UI and download history management"""

import os
import json
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

from ..utils import clear_treeview
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
        try:
            with open(self.history_file, "r") as f:
                self._history_cache = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self._history_cache = []
        return self._history_cache

    def _save_history(self, history):
        """Save history list to JSON file and update cache"""
        self._history_cache = history
        try:
            fd = os.open(self.history_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w") as f:
                json.dump(history, f, indent=2)
        except OSError:
            pass

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
