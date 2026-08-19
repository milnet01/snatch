"""Download tab UI construction"""

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from ..theme import get_theme
from ..widgets import ToggleSwitch
from ..utils import zenity_file_dialog
from ..platform_utils import open_path


class DownloadTabMixin:
    """Mixin providing the Download tab UI construction.
    Expects the host class to provide all relevant state variables and methods.
    """

    def _create_download_tab(self, parent):
        """Build the download tab contents — wide two-column layout"""
        theme = get_theme()

        # ── Row 1: URL bar (full width) ──────────────────────────────
        url_frame = ttk.LabelFrame(parent, text="Video URL", padding="12")
        url_frame.pack(fill=tk.X, pady=(0, 8))

        self.url_entry = ttk.Entry(url_frame, textvariable=self.url_var, font=("Helvetica", 10))
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.url_entry.bind("<Return>", lambda e: self.fetch_formats())

        paste_btn = ttk.Button(url_frame, text="Paste", command=self.paste_url,
                               style="Small.TButton")
        paste_btn.pack(side=tk.LEFT, padx=(0, 5))

        add_queue_btn = ttk.Button(url_frame, text="+ Queue", command=self._add_to_queue,
                                   style="Small.TButton")
        add_queue_btn.pack(side=tk.LEFT, padx=(0, 5))

        fetch_btn = ttk.Button(url_frame, text="Fetch Formats", command=self.fetch_formats)
        fetch_btn.pack(side=tk.RIGHT)

        # ── Row 2: Preview (left) | Auth + Save (right) ─────────────
        row2 = ttk.Frame(parent)
        row2.pack(fill=tk.X, pady=(0, 8))
        row2.columnconfigure(0, weight=1, uniform="half")
        row2.columnconfigure(1, weight=1, uniform="half")

        # Left: Video Preview
        self.preview_frame = ttk.LabelFrame(row2, text="Video Preview", padding="12")
        self.preview_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 4))

        self.thumb_label = tk.Label(self.preview_frame, bg=theme.BG,
                                    text="No video loaded", fg=theme.FG_DIM,
                                    font=("Helvetica", 9))
        self.thumb_label.pack(side=tk.LEFT, padx=(0, 12))

        preview_info = ttk.Frame(self.preview_frame)
        preview_info.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.preview_title_var = tk.StringVar(value="")
        self.preview_uploader_var = tk.StringVar(value="")
        self.preview_duration_var = tk.StringVar(value="")

        self.preview_title_label = tk.Label(preview_info, textvariable=self.preview_title_var,
                                            bg=theme.BG, fg=theme.FG,
                                            font=("Helvetica", 10, "bold"),
                                            anchor="w", wraplength=350, justify="left")
        self.preview_title_label.pack(fill=tk.X, pady=(0, 4))

        self.preview_uploader_label = tk.Label(preview_info, textvariable=self.preview_uploader_var,
                                               bg=theme.BG, fg=theme.FG_DIM,
                                               font=("Helvetica", 9), anchor="w")
        self.preview_uploader_label.pack(fill=tk.X, pady=(0, 2))

        self.preview_duration_label = tk.Label(preview_info, textvariable=self.preview_duration_var,
                                               bg=theme.BG, fg=theme.FG_DIM,
                                               font=("Helvetica", 9), anchor="w")
        self.preview_duration_label.pack(fill=tk.X)

        # Right: Auth + Save stacked
        right_col = ttk.Frame(row2)
        right_col.grid(row=0, column=1, sticky="nsew", padx=(4, 0))

        auth_frame = ttk.LabelFrame(right_col, text="Authentication", padding="8")
        auth_frame.pack(fill=tk.X, pady=(0, 6))

        browser_row = ttk.Frame(auth_frame)
        browser_row.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(browser_row, text="Browser cookies:").pack(side=tk.LEFT, padx=(0, 6))
        browsers = ["none", "firefox", "chromium", "brave", "edge", "opera", "vivaldi"]
        browser_combo = ttk.Combobox(browser_row, textvariable=self.browser_var, values=browsers,
                                      state="readonly", width=12)
        browser_combo.pack(side=tk.LEFT, padx=(0, 6))
        browser_combo.bind("<<ComboboxSelected>>", lambda e: self._on_browser_changed())
        self.refresh_cookies_btn = ttk.Button(browser_row, text="Refresh Cookies",
                                                command=self._refresh_cookies, style="Small.TButton")
        self.refresh_cookies_btn.pack(side=tk.LEFT)

        cookies_row = ttk.Frame(auth_frame)
        cookies_row.pack(fill=tk.X)
        ttk.Label(cookies_row, text="Cookies file:").pack(side=tk.LEFT, padx=(0, 6))
        cookies_entry = ttk.Entry(cookies_row, textvariable=self.cookies_file_var, font=("Helvetica", 9))
        cookies_entry.pack(side=tk.LEFT, padx=(0, 5), fill=tk.X, expand=True)
        ttk.Button(cookies_row, text="Browse...", command=self.browse_cookies_file,
                   style="Small.TButton").pack(side=tk.LEFT)

        save_frame = ttk.LabelFrame(right_col, text="Save Location", padding="8")
        save_frame.pack(fill=tk.X)
        save_entry = ttk.Entry(save_frame, textvariable=self.save_path_var, font=("Helvetica", 10))
        save_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        ttk.Button(save_frame, text="Browse...", command=self.browse_folder).pack(side=tk.RIGHT)

        # ── Row 3: Format Filters + Treeview (full width) ───────────
        format_frame = ttk.LabelFrame(parent, text="Available Formats", padding="12")
        format_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        filter_frame = ttk.Frame(format_frame)
        filter_frame.pack(fill=tk.X, pady=(0, 6))

        ttk.Label(filter_frame, text="Filter:", font=("Helvetica", 9, "bold")).pack(side=tk.LEFT, padx=(0, 8))

        ttk.Label(filter_frame, text="Resolution:").pack(side=tk.LEFT, padx=(0, 4))
        self.filter_res_combo = ttk.Combobox(filter_frame, textvariable=self.filter_res_var,
                                             values=["All"], state="readonly", width=10)
        self.filter_res_combo.pack(side=tk.LEFT, padx=(0, 10))
        self.filter_res_combo.bind("<<ComboboxSelected>>", lambda e: self._apply_filters())

        ttk.Label(filter_frame, text="Type:").pack(side=tk.LEFT, padx=(0, 4))
        self.filter_type_combo = ttk.Combobox(filter_frame, textvariable=self.filter_type_var,
                                              values=["All", "Video+Audio", "Video Only", "Audio Only"],
                                              state="readonly", width=12)
        self.filter_type_combo.pack(side=tk.LEFT, padx=(0, 10))
        self.filter_type_combo.bind("<<ComboboxSelected>>", lambda e: self._apply_filters())

        ttk.Label(filter_frame, text="Ext:").pack(side=tk.LEFT, padx=(0, 4))
        self.filter_ext_combo = ttk.Combobox(filter_frame, textvariable=self.filter_ext_var,
                                             values=["All"], state="readonly", width=8)
        self.filter_ext_combo.pack(side=tk.LEFT, padx=(0, 10))
        self.filter_ext_combo.bind("<<ComboboxSelected>>", lambda e: self._apply_filters())

        columns = ("format_id", "ext", "resolution", "fps", "filesize", "note")
        self.format_tree = ttk.Treeview(format_frame, columns=columns, show="headings",
                                         selectmode="browse", height=10)

        self.format_tree.heading("format_id", text="Format ID")
        self.format_tree.heading("ext", text="Ext")
        self.format_tree.heading("resolution", text="Resolution")
        self.format_tree.heading("fps", text="FPS")
        self.format_tree.heading("filesize", text="Size")
        self.format_tree.heading("note", text="Codec Info")

        self.format_tree.column("format_id", width=80, minwidth=60)
        self.format_tree.column("ext", width=60, minwidth=40)
        self.format_tree.column("resolution", width=110, minwidth=80)
        self.format_tree.column("fps", width=50, minwidth=40)
        self.format_tree.column("filesize", width=90, minwidth=60)
        self.format_tree.column("note", width=350, minwidth=200)

        fmt_scrollbar = ttk.Scrollbar(format_frame, orient=tk.VERTICAL,
                                   command=self.format_tree.yview)
        self.format_tree.configure(yscrollcommand=fmt_scrollbar.set)
        self.format_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        fmt_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Pre-configure row color tags (used by _apply_filters)
        self.format_tree.tag_configure("video_only", foreground=theme.VIDEO_ONLY)
        self.format_tree.tag_configure("audio_only", foreground=theme.AUDIO_ONLY)
        self.format_tree.tag_configure("muxed", foreground=theme.SUCCESS)

        # Playlist treeview (hidden by default, shown for playlists)
        self.playlist_frame = ttk.LabelFrame(parent, text="Playlist Videos", padding="12")

        pl_btn_row = ttk.Frame(self.playlist_frame)
        pl_btn_row.pack(fill=tk.X, pady=(0, 8))
        ttk.Button(pl_btn_row, text="Select All", command=self._playlist_select_all,
                   style="Small.TButton").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(pl_btn_row, text="Deselect All", command=self._playlist_deselect_all,
                   style="Small.TButton").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(pl_btn_row, text="Download Selected", command=self._download_playlist_selected,
                   style="Accent.TButton").pack(side=tk.RIGHT)

        pl_columns = ("select", "index", "title", "duration")
        self.playlist_tree = ttk.Treeview(self.playlist_frame, columns=pl_columns,
                                          show="headings", selectmode="extended", height=8)
        self.playlist_tree.heading("select", text="Sel")
        self.playlist_tree.heading("index", text="#")
        self.playlist_tree.heading("title", text="Title")
        self.playlist_tree.heading("duration", text="Duration")
        self.playlist_tree.column("select", width=40, minwidth=30)
        self.playlist_tree.column("index", width=40, minwidth=30)
        self.playlist_tree.column("title", width=500, minwidth=200)
        self.playlist_tree.column("duration", width=80, minwidth=60)
        self.playlist_tree.bind("<ButtonRelease-1>", self._toggle_playlist_select)

        pl_scroll = ttk.Scrollbar(self.playlist_frame, orient=tk.VERTICAL,
                                  command=self.playlist_tree.yview)
        self.playlist_tree.configure(yscrollcommand=pl_scroll.set)
        self.playlist_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        pl_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # ── Row 4: Quick buttons (full width) ───────────────────────
        quick_frame = ttk.Frame(parent)
        quick_frame.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(quick_frame, text="Quick Select:", font=("Helvetica", 9, "bold")).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(quick_frame, text="Best Video+Audio",
                   command=lambda: self.quick_download("best")).pack(side=tk.LEFT, padx=3)
        ttk.Button(quick_frame, text="Best MP4",
                   command=lambda: self.quick_download("bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]")).pack(side=tk.LEFT, padx=3)
        ttk.Button(quick_frame, text="Audio Only (MP3)",
                   command=lambda: self.quick_download("bestaudio", audio_only=True)).pack(side=tk.LEFT, padx=3)

        # ── Row 5: Queue (left) | Progress (right) ──────────────────
        row5 = ttk.Frame(parent)
        row5.pack(fill=tk.X, pady=(0, 8))
        row5.columnconfigure(0, weight=1, uniform="half")
        row5.columnconfigure(1, weight=1, uniform="half")

        # Left: Queue
        queue_frame = ttk.LabelFrame(row5, text="Download Queue", padding="8")
        queue_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 4))

        queue_btn_row = ttk.Frame(queue_frame)
        queue_btn_row.pack(fill=tk.X, pady=(0, 4))
        ttk.Button(queue_btn_row, text="Clear Queue", command=self._clear_queue,
                   style="Small.TButton").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(queue_btn_row, text="Download Queue", command=self._process_queue,
                   style="Small.TButton").pack(side=tk.LEFT, padx=(0, 5))
        self.queue_status_label = ttk.Label(queue_btn_row, text="0 items in queue",
                                            style="Version.TLabel")
        self.queue_status_label.pack(side=tk.RIGHT)

        q_columns = ("num", "url", "status")
        self.queue_tree = ttk.Treeview(queue_frame, columns=q_columns, show="headings", height=3)
        self.queue_tree.heading("num", text="#")
        self.queue_tree.heading("url", text="URL")
        self.queue_tree.heading("status", text="Status")
        self.queue_tree.column("num", width=30, minwidth=25)
        self.queue_tree.column("url", width=300, minwidth=150)
        self.queue_tree.column("status", width=80, minwidth=50)
        self.queue_tree.pack(fill=tk.BOTH, expand=True)

        # Right: Progress + Speed
        progress_frame = ttk.LabelFrame(row5, text="Download Progress", padding="8")
        progress_frame.grid(row=0, column=1, sticky="nsew", padx=(4, 0))

        progress_top = ttk.Frame(progress_frame)
        progress_top.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(progress_top, text="Speed Limit:").pack(side=tk.LEFT, padx=(0, 4))
        speed_combo = ttk.Combobox(progress_top, textvariable=self.speed_limit_var,
                                   values=["Unlimited", "1M", "2M", "5M", "10M", "20M"],
                                   state="readonly", width=10)
        speed_combo.pack(side=tk.LEFT, padx=(0, 10))

        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var,
                                             maximum=100, mode="determinate")
        self.progress_bar.pack(fill=tk.X, pady=(0, 8))

        self.status_label = ttk.Label(progress_frame, textvariable=self.status_var,
                                       style="Status.TLabel")
        self.status_label.pack(fill=tk.X)

        # ── Row 6: Buttons + Toggles (full width) ───────────────────
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X, pady=(5, 0))

        self.download_btn = ttk.Button(btn_frame, text="Download Selected Format",
                                        command=self.download_selected, style="Accent.TButton")
        self.download_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.cancel_btn = ttk.Button(btn_frame, text="Cancel", command=self.cancel_download,
                                      state=tk.DISABLED)
        self.cancel_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.open_folder_btn = ttk.Button(btn_frame, text="Open Folder",
                                          command=self._open_download_folder,
                                          style="Small.TButton")
        self.open_folder_btn.pack(side=tk.LEFT)
        self.open_folder_btn.pack_forget()

        # Toggles on the right
        toggle_outer = ttk.Frame(btn_frame)
        toggle_outer.pack(side=tk.RIGHT)

        sb_frame = ttk.Frame(toggle_outer)
        sb_frame.pack(side=tk.RIGHT, padx=(12, 0))
        self.sponsorblock_toggle = ToggleSwitch(sb_frame, variable=self.sponsorblock_var,
                                                on_text="SponsorBlock On", off_text="SponsorBlock Off",
                                                on_color=theme.SPONSORBLOCK_ON, off_color=theme.BG_LIGHTER)
        self.sponsorblock_toggle.label.pack(side=tk.RIGHT, padx=(6, 0))
        self.sponsorblock_toggle.pack(side=tk.RIGHT)

        sub_frame = ttk.Frame(toggle_outer)
        sub_frame.pack(side=tk.RIGHT, padx=(12, 0))
        self.subtitle_toggle = ToggleSwitch(sub_frame, variable=self.subtitle_var,
                                            on_text="Subtitles On", off_text="Subtitles Off",
                                            on_color=theme.SUBTITLE_ON, off_color=theme.BG_LIGHTER)
        self.subtitle_toggle.label.pack(side=tk.RIGHT, padx=(6, 0))
        self.subtitle_toggle.pack(side=tk.RIGHT)

        merge_frame = ttk.Frame(toggle_outer)
        merge_frame.pack(side=tk.RIGHT)
        self.merge_toggle = ToggleSwitch(merge_frame, variable=self.merge_audio_var)
        self.merge_toggle.label.pack(side=tk.RIGHT, padx=(6, 0))
        self.merge_toggle.pack(side=tk.RIGHT)

    # ── Download tab helpers ────────────────────────────────────────

    def _on_browser_changed(self):
        """Clear cookies file when a browser is selected for extraction"""
        if self.browser_var.get() != "none":
            self.cookies_file_var.set("")

    def paste_url(self):
        """Paste clipboard contents into the URL field"""
        try:
            clipboard = self.root.clipboard_get()
            if clipboard:
                self.url_var.set(clipboard.strip())
        except tk.TclError:
            pass

    def browse_folder(self):
        """Browse for folder - uses zenity if available, falls back to tkinter"""
        initial_dir = self.save_path_var.get()
        path = zenity_file_dialog(directory=True, initial_dir=initial_dir,
                                  title="Select Save Location")
        if path:
            self.save_path_var.set(path)
            return
        folder = filedialog.askdirectory(initialdir=initial_dir)
        if folder:
            self.save_path_var.set(folder)

    def _refresh_cookies(self):
        """Force re-extract cookies from the selected browser"""
        browser = self.browser_var.get()
        if not browser or browser == "none":
            messagebox.showinfo("Info", "Please select a browser first.")
            return
        cached = os.path.join(self.script_dir, "cookies.txt")
        if os.path.isfile(cached):
            os.remove(cached)
        self.cookies_file_var.set("")
        extracted = self._extract_browser_cookies()
        if extracted:
            self.status_var.set("Cookies refreshed from browser")
        else:
            self.status_var.set("Cookie extraction failed")
            messagebox.showwarning("Warning",
                                   f"Could not extract cookies from {browser}.\n\n"
                                   "Make sure you are logged into YouTube in your browser.")

    def browse_cookies_file(self):
        """Browse for a cookies.txt file - uses zenity if available"""
        initial_dir = os.path.expanduser("~")
        path = zenity_file_dialog(
            initial_dir=initial_dir, title="Select cookies.txt file",
            file_filter=["Text files (*.txt) | *.txt", "All files | *"])
        if path:
            self.cookies_file_var.set(path)
            self.browser_var.set("none")
            return
        filepath = filedialog.askopenfilename(
            initialdir=initial_dir, title="Select cookies.txt file",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if filepath:
            self.cookies_file_var.set(filepath)
            self.browser_var.set("none")

    def _open_download_folder(self):
        """Open the folder of the last download"""
        path = self.last_download_path or self.save_path_var.get()
        resolved = os.path.realpath(path)
        if os.path.isdir(resolved):
            open_path(resolved)
        elif os.path.isfile(resolved):
            open_path(os.path.dirname(resolved))
        else:
            fallback = os.path.realpath(self.save_path_var.get())
            if os.path.isdir(fallback):
                open_path(fallback)

    def _setup_drag_drop(self):
        """Register URL entry as drag & drop target"""
        from tkinterdnd2 import DND_TEXT
        try:
            self.url_entry.drop_target_register(DND_TEXT)
            self.url_entry.dnd_bind("<<Drop>>", self._on_url_drop)
        except Exception:
            pass

    def _on_url_drop(self, event):
        """Handle dropped URL - validate before accepting"""
        data = event.data.strip()
        if data.startswith("{") and data.endswith("}"):
            data = data[1:-1]
        data = data.strip()
        if self._is_valid_url(data):
            self.url_var.set(data)
        else:
            self.status_var.set("Dropped text is not a valid URL")
