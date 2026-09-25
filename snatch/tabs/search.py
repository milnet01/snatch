"""Search tab UI and YouTube search logic"""

import base64
import json
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from urllib.parse import quote

from ..theme import get_theme
from ..widgets import attach_context_menu
from ..utils import format_duration, format_view_count, clear_treeview
from ..platform_utils import find_mpv
from ..logging_setup import get_logger

log = get_logger(__name__)

# A --flat-playlist search measured 3.3 s for 20 results on 2026-08-19.
# This bounds a search that has stopped answering, not a normal one.
SEARCH_TIMEOUT_SEC = 120
# Duration filter boundaries, in seconds, matching the combobox labels:
# Short (< 4 min), Medium (4-20 min), Long (> 20 min).
SHORT_MAX_SEC = 4 * 60
LONG_MIN_SEC = 20 * 60
# One full extraction, run for the single row a user clicks: measured 4.1 s
# on 2026-09-03. This bounds one that has stopped answering.
DATE_FETCH_TIMEOUT_SEC = 60

# The "Uploaded" filter's labels, in combobox order, with YouTube's own
# upload-date bucket numbers (SNAT-0072). Verified 2026-09-25: each bucket's
# top results, fully extracted, were uploaded inside it. YouTube offers these
# five and no others, so "last 2 weeks" is not expressible.
UPLOADED_BUCKETS = {
    "Any": None,
    "Last hour": 1,
    "Today": 2,
    "This week": 3,
    "This month": 4,
    "This year": 5,
}


def search_filter_code(bucket, sort_by_date):
    """YouTube's sp= value for an upload-date bucket, or None for no filter.

    sp is a base64 protobuf that YouTube publishes no spec for: field 1 is
    the sort (2 = upload date), field 2 a message whose field 1 is the
    upload-date bucket. EgIIAw== decodes to exactly that shape for "this
    week". With a bucket set, YouTube keeps the filter but was measured not
    to order strictly newest-first, so the sort is sent and not relied on.
    """
    if bucket is None:
        return None
    raw = (b"\x08\x02" if sort_by_date else b"") + bytes((0x12, 2, 0x08, bucket))
    return base64.b64encode(raw).decode("ascii")


def build_search_target(query, channel, count, sort, uploaded):
    """Return what yt-dlp is asked to list, or raise ValueError to refuse.

    A channel search goes through /@handle/search, which takes no sp=, so an
    upload-date filter cannot apply there: refused rather than silently
    ignored.
    """
    bucket = UPLOADED_BUCKETS[uploaded]
    if channel:
        if bucket is not None:
            raise ValueError("The Uploaded filter works on a normal search, "
                             "not inside one channel. Clear the Channel box "
                             "or set Uploaded to Any.")
        handle = channel if channel.startswith("@") else f"@{channel}"
        if query:
            return f"https://www.youtube.com/{handle}/search?query={quote(query, safe='')}"
        return f"https://www.youtube.com/{handle}/videos"
    if bucket is not None:
        code = search_filter_code(bucket, sort == "Upload Date")
        return (f"https://www.youtube.com/results?search_query={quote(query, safe='')}"
                f"&sp={quote(code, safe='')}")
    prefix = f"ytsearchdate{count}" if sort == "Upload Date" else f"ytsearch{count}"
    return f"{prefix}:{query}"


def _is_playlist(entry):
    """A flat search row that is a playlist or channel tab, not a video."""
    return entry.get("ie_key") == "YoutubeTab"


def _format_upload_date(value):
    """yt-dlp's YYYYMMDD as YYYY-MM-DD; anything else as blank."""
    value = str(value or "")
    if len(value) == 8 and value.isdigit():
        return f"{value[:4]}-{value[4:6]}-{value[6:]}"
    return ""


class SearchTabMixin:
    """Mixin providing the Search tab UI and logic.
    Expects the host class to provide root, _get_base_cmd(),
    _get_cookie_args(), _cookie_state(), _play_in_mpv(), url_var, notebook,
    and other shared state.
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
        attach_context_menu(self.search_entry)

        ttk.Label(search_bar, text="Channel:").pack(side=tk.LEFT, padx=(0, 4))
        self.search_channel_var = tk.StringVar()
        self.search_channel_entry = ttk.Entry(search_bar,
                                              textvariable=self.search_channel_var,
                                              font=("Helvetica", 10), width=20)
        self.search_channel_entry.pack(side=tk.LEFT, padx=(0, 10))
        self.search_channel_entry.bind("<Return>", lambda e: self._perform_search())
        attach_context_menu(self.search_channel_entry)

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

        ttk.Label(filter_row, text="Uploaded:").pack(side=tk.LEFT, padx=(0, 4))
        self.search_uploaded_var = tk.StringVar(value="Any")
        ttk.Combobox(filter_row, textvariable=self.search_uploaded_var,
                     values=list(UPLOADED_BUCKETS),
                     state="readonly", width=11).pack(side=tk.LEFT, padx=(0, 10))

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

        # "uploaded" replaced a Resolution column the flat search never
        # filled (SNAT-0071). The date is fetched for a row when it is clicked.
        r_columns = ("num", "title", "channel", "duration", "views", "uploaded")
        self.search_tree = ttk.Treeview(results_frame, columns=r_columns,
                                         show="headings", selectmode="browse",
                                         height=8)
        self.search_tree.heading("num", text="#")
        self.search_tree.heading("title", text="Title")
        self.search_tree.heading("channel", text="Channel")
        self.search_tree.heading("duration", text="Duration")
        self.search_tree.heading("views", text="Views")
        self.search_tree.heading("uploaded", text="Uploaded")
        self.search_tree.column("num", width=30, minwidth=25)
        self.search_tree.column("title", width=380, minwidth=200)
        self.search_tree.column("channel", width=140, minwidth=80)
        self.search_tree.column("duration", width=70, minwidth=45)
        self.search_tree.column("views", width=90, minwidth=50)
        self.search_tree.column("uploaded", width=90, minwidth=70)

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

        # Without mpv there is no in-app player and the click opens the
        # system browser instead. Say so on the button rather than looking
        # like playback that silently does something else.
        play_label = "Play" if find_mpv() else "Open in Browser"
        ttk.Button(results_btn_frame, text=play_label,
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
        # Double-click the video area to toggle fullscreen, the convention
        # every other player uses.
        self.player_frame.bind("<Double-Button-1>", lambda e: self._toggle_fullscreen())

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
                   command=self._stop_player).pack(side=tk.LEFT, padx=(0, 3))

        self.fullscreen_btn = ttk.Button(controls_frame, text="Fullscreen", width=10,
                                          command=self._toggle_fullscreen)
        self.fullscreen_btn.pack(side=tk.LEFT, padx=(0, 8))

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

        # Where mpv's IPC transport is not reachable, say so rather than
        # shipping controls that quietly do nothing. On Windows mpv serves
        # --input-ipc-server over a named pipe, not a filesystem socket, so
        # every _mpv_command returns None there. Stop and Fullscreen do not
        # use IPC and stay live.
        if not self._ipc_supported():
            for widget in (self.play_pause_btn, self.volume_scale,
                           self.seek_scale):
                widget.state(["disabled"])
            self.player_time_var.set("transport controls unavailable "
                                     "on this platform")

        # Same authority as the Play button and the player itself: a packaged
        # build ships mpv, which shutil.which() cannot see.
        if not find_mpv():
            from ..player import _no_player_message
            self.player_status_label.config(text=_no_player_message(),
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
        # Cancel any loop already running. _tick_search_anim overwrites
        # _search_anim_id, so a second loop makes the first uncancellable and
        # it rewrites the status label every 400 ms forever -- overwriting the
        # "N results" line the search finishes with. See SNAT-0049.
        self._stop_search_anim()
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
        # Without this, two clicks start two yt-dlp subprocesses, and the tree
        # can end up showing one search's rows while self.search_results holds
        # the other's -- so Download and Play act on a different video from the
        # one highlighted. Same guard start_download already uses (SNAT-0049).
        if self.is_searching:
            messagebox.showwarning("Busy", "A search is already in progress")
            return

        query = self.search_var.get().strip()
        channel = self.search_channel_var.get().strip()
        if not query and not channel:
            messagebox.showwarning("Warning", "Please enter a search query or channel")
            return

        category = self.search_category_var.get()
        if category != "Any" and query:
            query = f"{query} {category.lower()}"

        count = int(self.search_count_var.get())
        try:
            search_target = build_search_target(
                query, channel, count, self.search_sort_var.get(),
                self.search_uploaded_var.get())
        except ValueError as exc:
            messagebox.showwarning("Search", str(exc))
            return

        # A date fetch still running for the previous search must not write
        # into this one's rows; it checks this number before it does.
        self._search_generation = getattr(self, "_search_generation", 0) + 1
        self.search_results = []  # Free old results before new search
        clear_treeview(self.search_tree)
        self._start_search_anim()

        self.is_searching = True
        # Read on this thread and passed in. Depending on the _tkinter build,
        # a .get() from a worker either takes the Tcl lock or raises
        # RuntimeError; STANDARDS.md 4.1 rule 2 forbids it either way, and
        # search_target and count are already passed this way (SNAT-0048).
        thread = threading.Thread(
            target=self._search_thread,
            args=(search_target, count, self.search_duration_var.get(),
                  self._cookie_state()))
        thread.daemon = True
        thread.start()

    def _search_thread(self, search_target, max_results, duration_filter,
                       cookie_state):
        """Run yt-dlp search in background"""
        try:
            cmd = self._get_base_cmd()
            cmd.extend(self._get_cookie_args(cookie_state))
            # --flat-playlist lists the results without fully extracting every
            # video. Measured 2026-08-19 on a 20-result search: 3.3s / 23 KB
            # with it, ~40s / 11.5 MB without. The slow path made the UI look
            # hung behind a "Searching..." label with no output for most of a
            # minute. The cost is that entries carry no height/resolution, so
            # that column stays blank; everything else the results table and
            # the Play/Download buttons need (title, channel, duration,
            # view_count, url) is present.
            # Checked 2026-09-02 against both channel forms this builds
            # (/@handle/videos and /@handle/search?query=): each returns flat
            # `_type: url` video entries, not a nested tab playlist, so the
            # one-level walk below is right for every target it is given.
            cmd.extend(["-J", "--flat-playlist", "--playlist-end", str(max_results),
                        "--", search_target])

            result = subprocess.run(cmd, capture_output=True, text=True,
                                    timeout=SEARCH_TIMEOUT_SEC)

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

            # yt-dlp emits JSON null here for a playlist with no listable
            # children, so a [] default does not help: `for entry in entries`
            # raises TypeError. Individual elements are null for deleted,
            # private and region-blocked videos, and entry.get() then raises
            # AttributeError -- in _display_search_results that is an
            # unhandled Tk traceback with the tree half-populated (SNAT-0050).
            entries = [e for e in (data.get("entries") or [])
                       if isinstance(e, dict)]
            del data  # Free large JSON response

            if not entries and result.returncode != 0:
                self.root.after(0, lambda: self._search_error(result.stderr))
                return

            if duration_filter != "Any":
                filtered = []
                for entry in entries:
                    dur = entry.get("duration") or 0
                    if duration_filter.startswith("Short") and dur < SHORT_MAX_SEC:
                        filtered.append(entry)
                    elif (duration_filter.startswith("Medium")
                          and SHORT_MAX_SEC <= dur <= LONG_MIN_SEC):
                        filtered.append(entry)
                    elif duration_filter.startswith("Long") and dur > LONG_MIN_SEC:
                        filtered.append(entry)
                entries = filtered

            # search_results is assigned in _display_search_results instead of
            # here, so it lands on the main thread in the same step as the tree
            # rows. Assigned here, a theme switch could clear it between this
            # line and the callback, leaving a populated tree whose every row
            # reported "Select a search result first" (SNAT-0049).
            self.root.after(0, lambda: self._display_search_results(entries))

        except subprocess.TimeoutExpired:
            self.root.after(0, lambda: self._search_error("Search timed out"))
        except Exception as e:
            log.exception("Search failed")
            self.root.after(0, lambda e=e: self._search_error(str(e)))

    def _display_search_results(self, entries):
        """Populate search results treeview"""
        self.is_searching = False
        self._stop_search_anim()
        self.search_results = entries
        clear_treeview(self.search_tree)

        for i, entry in enumerate(entries, 1):
            title = entry.get("title", "Unknown")
            if _is_playlist(entry):
                # The flat search gives a playlist no channel, duration or
                # views, and "?" in all three read as a fault (SNAT-0077).
                values = (i, title, "", "Playlist", "", "")
            else:
                values = (i, title,
                          entry.get("channel") or entry.get("uploader") or "",
                          format_duration(entry.get("duration")),
                          format_view_count(entry.get("view_count")),
                          _format_upload_date(entry.get("upload_date")))
            self.search_tree.insert("", tk.END, iid=str(i), values=values)

        self.search_status_var.set(f"{len(entries)} results")

    def _search_error(self, message):
        self.is_searching = False
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
        self._search_generation = getattr(self, "_search_generation", 0) + 1
        self.search_results = []
        self.search_status_var.set("")

    def _on_search_select(self, event):
        """Update now-playing label with selected result title"""
        sel = self.search_tree.selection()
        if not sel:
            return
        idx = int(sel[0]) - 1
        if idx < len(self.search_results):
            entry = self.search_results[idx]
            title = entry.get("title", "")
            self.now_playing_var.set(f"Selected: {title[:50]}")
            self._fetch_upload_date(idx, entry)

    def _fetch_upload_date(self, idx, entry):
        """Fill one row's Uploaded cell, off the GUI thread (SNAT-0071).

        The flat search returns no dates, and a full extraction costs about
        4 s a video, so it is paid only for a row someone clicks. Playlists
        are skipped: extracting one reads every video in it.
        """
        if _is_playlist(entry) or entry.get("upload_date") or entry.get("_date_pending"):
            return
        url = entry.get("url") or entry.get("webpage_url") or ""
        if not url.startswith("http"):
            return
        entry["_date_pending"] = True
        self.search_tree.set(str(idx + 1), "uploaded", "…")
        generation = getattr(self, "_search_generation", 0)
        cookie_state = self._cookie_state()  # read here, on the GUI thread

        def worker():
            date = ""
            try:
                cmd = self._get_base_cmd()
                cmd.extend(self._get_cookie_args(cookie_state))
                cmd.extend(["--skip-download", "--print", "%(upload_date)s",
                            "--", url])
                done = subprocess.run(cmd, capture_output=True, text=True,
                                      timeout=DATE_FETCH_TIMEOUT_SEC)
                lines = done.stdout.strip().splitlines()
                date = lines[-1] if lines else ""
            except subprocess.TimeoutExpired:
                log.warning("Upload date fetch timed out for %s", url)
            except Exception:
                log.exception("Upload date fetch failed for %s", url)
            self.root.after(0, lambda: self._show_upload_date(
                generation, idx, entry, date))

        threading.Thread(target=worker, daemon=True).start()

    def _show_upload_date(self, generation, idx, entry, date):
        """Main-thread half of _fetch_upload_date."""
        entry.pop("_date_pending", None)
        if generation != getattr(self, "_search_generation", 0):
            return  # a newer search replaced these rows
        if idx >= len(self.search_results) or self.search_results[idx] is not entry:
            return
        entry["upload_date"] = date if date.isdigit() else ""
        if self.search_tree.exists(str(idx + 1)):
            self.search_tree.set(str(idx + 1), "uploaded",
                                 _format_upload_date(entry["upload_date"]) or "unknown")

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
