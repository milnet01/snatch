"""Search tab UI and YouTube search logic"""

import json
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from urllib.parse import quote

from ..theme import get_theme
from ..utils import format_duration, format_view_count, clear_treeview
from .. import HAS_MPV


class SearchTabMixin:
    """Mixin providing the Search tab UI and logic.
    Expects the host class to provide root, _get_base_cmd(), _get_cookie_args(),
    _play_in_mpv(), url_var, notebook, and other shared state.
    """

    def _create_search_tab(self, parent):
        """Build the YouTube search tab with embedded player"""
        theme = get_theme()

        # ── Search bar ──────────────────────────────────────────────
        search_bar = ttk.LabelFrame(parent, text="YouTube Search", padding="12")
        search_bar.pack(fill=tk.X, pady=(0, 8))

        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_bar, textvariable=self.search_var,
                                      font=("Helvetica", 10))
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.search_entry.bind("<Return>", lambda e: self._perform_search())

        ttk.Label(search_bar, text="Channel:").pack(side=tk.LEFT, padx=(0, 4))
        self.search_channel_var = tk.StringVar()
        self.search_channel_entry = ttk.Entry(search_bar,
                                              textvariable=self.search_channel_var,
                                              font=("Helvetica", 10), width=20)
        self.search_channel_entry.pack(side=tk.LEFT, padx=(0, 10))
        self.search_channel_entry.bind("<Return>", lambda e: self._perform_search())

        ttk.Button(search_bar, text="Search",
                   command=self._perform_search).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(search_bar, text="Clear", command=self._clear_search,
                   style="Small.TButton").pack(side=tk.LEFT)

        # ── Filters row ────────────────────────────────────────────
        filter_row = ttk.Frame(parent)
        filter_row.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(filter_row, text="Category:",
                  font=("Helvetica", 9, "bold")).pack(side=tk.LEFT, padx=(0, 6))
        self.search_category_var = tk.StringVar(value="Any")
        for cat in ["Any", "Trailer", "Gameplay", "Review", "Walkthrough"]:
            ttk.Radiobutton(filter_row, text=cat,
                            variable=self.search_category_var, value=cat,
                            style="Dark.TRadiobutton").pack(side=tk.LEFT, padx=(0, 4))

        ttk.Label(filter_row, text="|",
                  foreground=theme.BORDER).pack(side=tk.LEFT, padx=6)

        ttk.Label(filter_row, text="Duration:").pack(side=tk.LEFT, padx=(0, 4))
        self.search_duration_var = tk.StringVar(value="Any")
        ttk.Combobox(filter_row, textvariable=self.search_duration_var,
                     values=["Any", "Short (< 4 min)", "Medium (4-20 min)",
                             "Long (> 20 min)"],
                     state="readonly", width=16).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Label(filter_row, text="Sort:").pack(side=tk.LEFT, padx=(0, 4))
        self.search_sort_var = tk.StringVar(value="Relevance")
        ttk.Combobox(filter_row, textvariable=self.search_sort_var,
                     values=["Relevance", "Upload Date"],
                     state="readonly", width=12).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Label(filter_row, text="Results:").pack(side=tk.LEFT, padx=(0, 4))
        self.search_count_var = tk.StringVar(value="20")
        ttk.Combobox(filter_row, textvariable=self.search_count_var,
                     values=["10", "20", "50"],
                     state="readonly", width=5).pack(side=tk.LEFT)

        # ── Main content: Results (top) | Player (bottom) ─────────
        content = ttk.Frame(parent)
        content.pack(fill=tk.BOTH, expand=True)
        content.columnconfigure(0, weight=1)
        content.rowconfigure(0, weight=1)
        content.rowconfigure(2, weight=1)

        # Top: Search Results
        results_frame = ttk.LabelFrame(content, text="Search Results", padding="8")
        results_frame.grid(row=0, column=0, sticky="nsew")

        r_columns = ("num", "title", "channel", "duration", "views", "resolution")
        self.search_tree = ttk.Treeview(results_frame, columns=r_columns,
                                         show="headings", selectmode="browse",
                                         height=8)
        self.search_tree.heading("num", text="#")
        self.search_tree.heading("title", text="Title")
        self.search_tree.heading("channel", text="Channel")
        self.search_tree.heading("duration", text="Duration")
        self.search_tree.heading("views", text="Views")
        self.search_tree.heading("resolution", text="Resolution")
        self.search_tree.column("num", width=30, minwidth=25)
        self.search_tree.column("title", width=380, minwidth=200)
        self.search_tree.column("channel", width=140, minwidth=80)
        self.search_tree.column("duration", width=70, minwidth=45)
        self.search_tree.column("views", width=90, minwidth=50)
        self.search_tree.column("resolution", width=80, minwidth=50)

        self.search_tree.bind("<<TreeviewSelect>>", self._on_search_select)
        self.search_tree.bind("<Double-1>", lambda e: self._play_search_result())

        r_scroll = ttk.Scrollbar(results_frame, orient=tk.VERTICAL,
                                 command=self.search_tree.yview)
        self.search_tree.configure(yscrollcommand=r_scroll.set)
        self.search_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        r_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Action buttons + status
        results_btn_frame = ttk.Frame(content)
        results_btn_frame.grid(row=1, column=0, sticky="ew", pady=(4, 4))

        ttk.Button(results_btn_frame, text="Play",
                   command=self._play_search_result).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(results_btn_frame, text="Download",
                   command=self._download_search_result,
                   style="Accent.TButton").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(results_btn_frame, text="Load in Download Tab",
                   command=self._load_search_to_download,
                   style="Small.TButton").pack(side=tk.LEFT)

        self.search_status_var = tk.StringVar(value="")
        ttk.Label(results_btn_frame, textvariable=self.search_status_var,
                  style="Version.TLabel").pack(side=tk.RIGHT)

        # Bottom: Player
        player_outer = ttk.LabelFrame(content, text="Player", padding="8")
        player_outer.grid(row=2, column=0, sticky="nsew")

        self.player_frame = tk.Frame(player_outer, bg=theme.PLAYER_BG, width=480, height=270)
        self.player_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
        self.player_frame.pack_propagate(False)

        self.player_status_label = tk.Label(self.player_frame,
                                            text="No video loaded",
                                            bg=theme.PLAYER_BG, fg=theme.FG_DIM,
                                            font=("Helvetica", 11))
        self.player_status_label.place(relx=0.5, rely=0.5, anchor="center")

        # Player controls
        controls_frame = ttk.Frame(player_outer)
        controls_frame.pack(fill=tk.X, pady=(0, 4))

        self.play_pause_btn = ttk.Button(controls_frame, text="Play", width=5,
                                          command=self._toggle_play_pause)
        self.play_pause_btn.pack(side=tk.LEFT, padx=(0, 3))

        ttk.Button(controls_frame, text="Stop", width=5,
                   command=self._stop_player).pack(side=tk.LEFT, padx=(0, 8))

        ttk.Label(controls_frame, text="Vol:").pack(side=tk.LEFT, padx=(0, 4))
        self.volume_var = tk.IntVar(value=80)
        self.volume_scale = ttk.Scale(controls_frame, from_=0, to=100,
                                       variable=self.volume_var,
                                       orient=tk.HORIZONTAL, length=80,
                                       command=self._on_volume_change)
        self.volume_scale.pack(side=tk.LEFT, padx=(0, 8))

        self.now_playing_var = tk.StringVar(value="")
        tk.Label(controls_frame, textvariable=self.now_playing_var,
                 bg=theme.BG, fg=theme.FG_DIM,
                 font=("Helvetica", 8), anchor="w").pack(side=tk.LEFT,
                                                          fill=tk.X, expand=True)

        # Seek bar
        seek_frame = ttk.Frame(player_outer)
        seek_frame.pack(fill=tk.X)

        self.seek_var = tk.DoubleVar(value=0)
        self.seek_scale = ttk.Scale(seek_frame, from_=0, to=100,
                                     variable=self.seek_var,
                                     orient=tk.HORIZONTAL)
        self.seek_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        self.seek_scale.bind("<Button-1>",
                             lambda e: self._on_seek_press())
        self.seek_scale.bind("<ButtonRelease-1>", self._on_seek_release)

        self.player_time_var = tk.StringVar(value="--:-- / --:--")
        ttk.Label(seek_frame, textvariable=self.player_time_var,
                  style="Version.TLabel").pack(side=tk.RIGHT)

        if not HAS_MPV:
            self.player_status_label.config(
                text="mpv not installed\n\nInstall with:\nsudo apt install mpv",
                fg=theme.ACCENT)

    def _on_seek_press(self):
        """Mark that the user is dragging the seek bar"""
        self._user_seeking = True

    # ── Search animation ─────────────────────────────────────────────

    _SEARCH_ANIM_FRAMES = ("Searching.", "Searching..", "Searching...",
                           "Searching....", "Searching.....", "Searching......")
    _SEARCH_ANIM_MS = 400

    def _start_search_anim(self):
        """Start cycling-dots animation in the status label"""
        self._search_anim_step = 0
        self._search_anim_id = self.root.after(0, self._tick_search_anim)

    def _tick_search_anim(self):
        """Advance one animation frame"""
        frames = self._SEARCH_ANIM_FRAMES
        self.search_status_var.set(frames[self._search_anim_step % len(frames)])
        self._search_anim_step += 1
        self._search_anim_id = self.root.after(self._SEARCH_ANIM_MS,
                                               self._tick_search_anim)

    def _stop_search_anim(self):
        """Cancel the animation loop"""
        anim_id = getattr(self, "_search_anim_id", None)
        if anim_id is not None:
            self.root.after_cancel(anim_id)
            self._search_anim_id = None

    # ── Search logic ────────────────────────────────────────────────

    def _perform_search(self):
        """Search YouTube using yt-dlp"""
        query = self.search_var.get().strip()
        channel = self.search_channel_var.get().strip()
        if not query and not channel:
            messagebox.showwarning("Warning", "Please enter a search query or channel")
            return

        category = self.search_category_var.get()
        if category != "Any" and query:
            query = f"{query} {category.lower()}"

        count = int(self.search_count_var.get())
        sort = self.search_sort_var.get()

        # Build search target based on channel filter
        if channel:
            # Normalize channel name to @handle format
            handle = channel if channel.startswith("@") else f"@{channel}"
            if query:
                search_target = f"https://www.youtube.com/{handle}/search?query={quote(query, safe='')}"
            else:
                search_target = f"https://www.youtube.com/{handle}/videos"
        else:
            prefix = f"ytsearchdate{count}" if sort == "Upload Date" else f"ytsearch{count}"
            search_target = f"{prefix}:{query}"

        self.search_results = []  # Free old results before new search
        clear_treeview(self.search_tree)
        self._start_search_anim()

        thread = threading.Thread(target=self._search_thread,
                                  args=(search_target, count))
        thread.daemon = True
        thread.start()

    def _search_thread(self, search_target, max_results):
        """Run yt-dlp search in background"""
        try:
            cmd = self._get_base_cmd()
            cmd.extend(self._get_cookie_args())
            cmd.extend(["-J", "--playlist-end", str(max_results),
                        "--", search_target])

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

            # Try parsing results even on non-zero exit (partial failures
            # like age-restricted videos still yield valid JSON output)
            if not result.stdout or not result.stdout.strip():
                self.root.after(0, lambda: self._search_error(result.stderr))
                return

            try:
                data = json.loads(result.stdout)
            except json.JSONDecodeError:
                self.root.after(0, lambda: self._search_error(result.stderr))
                return

            entries = data.get("entries", [])
            del data  # Free large JSON response

            if not entries and result.returncode != 0:
                self.root.after(0, lambda: self._search_error(result.stderr))
                return

            duration_filter = self.search_duration_var.get()
            if duration_filter != "Any":
                filtered = []
                for entry in entries:
                    dur = entry.get("duration") or 0
                    if duration_filter.startswith("Short") and dur < 240:
                        filtered.append(entry)
                    elif duration_filter.startswith("Medium") and 240 <= dur <= 1200:
                        filtered.append(entry)
                    elif duration_filter.startswith("Long") and dur > 1200:
                        filtered.append(entry)
                entries = filtered

            self.search_results = entries
            self.root.after(0, lambda: self._display_search_results(entries))

        except subprocess.TimeoutExpired:
            self.root.after(0, lambda: self._search_error("Search timed out"))
        except Exception as e:
            self.root.after(0, lambda: self._search_error(str(e)))

    def _display_search_results(self, entries):
        """Populate search results treeview"""
        self._stop_search_anim()
        clear_treeview(self.search_tree)

        for i, entry in enumerate(entries, 1):
            title = entry.get("title", "Unknown")
            channel = entry.get("channel", entry.get("uploader", "?"))
            duration = entry.get("duration")
            views = entry.get("view_count")
            height = entry.get("height")
            resolution = f"{height}p" if height else entry.get("resolution", "")

            dur_str = format_duration(duration)
            views_str = format_view_count(views)

            self.search_tree.insert("", tk.END, iid=str(i), values=(
                i, title, channel, dur_str, views_str, resolution
            ))

        self.search_status_var.set(f"{len(entries)} results")

    def _search_error(self, message):
        self._stop_search_anim()
        self.search_status_var.set("Search failed")
        # Show only ERROR lines; fall back to full message if none found
        raw = str(message)
        errors = [ln for ln in raw.splitlines() if "ERROR" in ln]
        display = "\n".join(errors) if errors else raw
        messagebox.showerror("Search Error", display[:500])

    def _clear_search(self):
        """Clear search field and results"""
        self._stop_search_anim()
        self.search_var.set("")
        self.search_channel_var.set("")
        clear_treeview(self.search_tree)
        self.search_results = []
        self.search_status_var.set("")

    def _on_search_select(self, event):
        """Update now-playing label with selected result title"""
        sel = self.search_tree.selection()
        if not sel:
            return
        idx = int(sel[0]) - 1
        if idx < len(self.search_results):
            title = self.search_results[idx].get("title", "")
            self.now_playing_var.set(f"Selected: {title[:50]}")

    def _get_selected_search_url(self):
        """Get URL and title of the selected search result"""
        sel = self.search_tree.selection()
        if not sel:
            return None, None
        idx = int(sel[0]) - 1
        if idx < len(self.search_results):
            entry = self.search_results[idx]
            url = entry.get("url") or entry.get("webpage_url", "")
            title = entry.get("title", "Unknown")
            if url and not url.startswith("http"):
                url = f"https://www.youtube.com/watch?v={url}"
            return url, title
        return None, None

    def _download_search_result(self):
        """Download the selected search result with best format"""
        url, title = self._get_selected_search_url()
        if not url:
            messagebox.showinfo("Info", "Select a search result first")
            return
        self.url_var.set(url)
        self.notebook.select(0)
        self.last_download_title = title
        self.quick_download("best")

    def _load_search_to_download(self):
        """Load selected result into Download tab and fetch formats"""
        url, title = self._get_selected_search_url()
        if not url:
            messagebox.showinfo("Info", "Select a search result first")
            return
        self.url_var.set(url)
        self.notebook.select(0)
        self.fetch_formats()

    def _play_search_result(self):
        """Play the selected search result in the embedded player"""
        url, title = self._get_selected_search_url()
        if not url:
            messagebox.showinfo("Info", "Select a search result first")
            return
        self._play_in_mpv(url, title)
