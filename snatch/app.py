"""Main application class composing all mixins"""

import os
import json
import re
import tkinter as tk
from tkinter import ttk, messagebox

from . import HAS_DND, __version__
from .platform_utils import app_data_dir
from .theme import THEMES, get_theme, set_theme, setup_styles
from .utils import tighten_user_data_permissions, write_private_json
from .player import PlayerMixin
from .version import VersionMixin
from .downloader import DownloaderMixin
from .tabs.download import DownloadTabMixin
from .tabs.search import SearchTabMixin
from .tabs.media_info import MediaInfoTabMixin
from .tabs.history import HistoryTabMixin
from .logging_setup import get_logger

log = get_logger(__name__)


class SnatchApp(DownloadTabMixin, SearchTabMixin, MediaInfoTabMixin,
               HistoryTabMixin, PlayerMixin, VersionMixin, DownloaderMixin):

    def __init__(self, root):
        self.root = root
        self.root.title(f"Snatch v{__version__}")
        self.root.resizable(True, True)
        self.root.minsize(1000, 750)

        # Variables
        self.url_var = tk.StringVar()
        self.progress_var = tk.DoubleVar(value=0)
        self.status_var = tk.StringVar(value="Ready")
        self.version_var = tk.StringVar(value="Checking version...")
        self.formats = []
        self.download_process = None
        self.is_downloading = False
        self.is_searching = False
        self.current_version = None
        self.latest_version = None
        self.browser_var = tk.StringVar(value="none")
        self.merge_audio_var = tk.IntVar(value=1)
        self._base_title = f"Snatch v{__version__}"

        # Paths - use the project root (parent of snatch package)
        self.script_dir = app_data_dir()
        # One-time tightening of user data files that predate the 0o600 write
        # path. atomic_private_write only fixes a file on SAVE; one that is
        # never saved again -- or was copied in from an older install -- keeps
        # its old mode forever. See SNAT-0006.
        tighten_user_data_permissions(self.script_dir)
        self.config_file = os.path.join(self.script_dir, "config.json")
        saved_config = self._load_config()
        self.save_path_var = tk.StringVar(
            value=saved_config.get("save_path", os.path.expanduser("~/Downloads"))
        )
        self.media_file_var = tk.StringVar(
            value=saved_config.get("media_file", "")
        )
        default_cookies = os.path.join(self.script_dir, "cookies.txt")
        self.cookies_file_var = tk.StringVar(
            value=default_cookies if os.path.isfile(default_cookies) else ""
        )

        # Restore dropdowns and toggles from config
        self.browser_var.set(saved_config.get("browser", "none"))
        self.merge_audio_var.set(saved_config.get("merge_audio", 1))

        # State variables
        self.video_title = ""
        self.cookie_fallback_used = False
        self.fetch_notes = []
        self.failed_cookie_args = None
        self.video_thumbnail = None
        self.subtitle_var = tk.IntVar(value=saved_config.get("subtitles", 0))
        self.sponsorblock_var = tk.IntVar(value=saved_config.get("sponsorblock", 0))
        self.speed_limit_var = tk.StringVar(value=saved_config.get("speed_limit", "Unlimited"))
        self.preferred_resolution = saved_config.get("preferred_resolution", "")
        self.preferred_ext = saved_config.get("preferred_ext", "")
        self.download_queue = []
        self.queue_index = 0
        self.is_processing_queue = False
        self.history_file = os.path.join(self.script_dir, "history.json")
        self.filter_res_var = tk.StringVar(value="All")
        self.filter_type_var = tk.StringVar(value="All")
        self.filter_ext_var = tk.StringVar(value="All")
        self.is_playlist = False
        self.playlist_entries = []
        self.last_download_path = ""
        self.last_download_title = ""
        self.last_download_format = ""

        # Search & player state
        self.search_results = []
        self.mpv_process = None
        self.mpv_socket_path = ""
        self._mpv_socket_dir = None
        self.player_update_id = None
        self.player_paused = False
        self._user_seeking = False

        # Theme — restore from config, set before widget creation.
        # set_theme() falls back to Dark for an unknown name but does not say
        # so, so theme_var used to keep the bogus string and _save_config
        # wrote it straight back: a typo'd theme was persisted forever while
        # the app silently ran Dark. Correct it here instead.
        theme_name = saved_config.get("theme", "Dark")
        if theme_name not in THEMES:
            log.warning("Unknown theme %r in config; using Dark", theme_name)
            theme_name = "Dark"
        self.theme_var = tk.StringVar(value=theme_name)
        set_theme(theme_name)

        # Set root background from active theme
        self.root.configure(bg=get_theme().BG)

        # Restore window geometry
        self.root.geometry(self._sanitize_geometry(
            saved_config.get("window_geometry")))

        self._set_icon()
        setup_styles()
        self.create_widgets()

        # Restore last active tab. A config carrying "2" rather than 2 makes
        # the comparison raise TypeError, which happens after the widgets are
        # built but still inside __init__, so the window never appears.
        last_tab = saved_config.get("last_tab", 0)
        if isinstance(last_tab, int) and 0 <= last_tab < self.notebook.index("end"):
            self.notebook.select(last_tab)

        self.check_version()
        self.check_nodejs()

        # Drag & drop support
        if HAS_DND:
            self._setup_drag_drop()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.bind("<Escape>", lambda e: self.cancel_download())
        self._setup_keyboard_shortcuts()

    DEFAULT_GEOMETRY = "1200x900"
    # Tk accepts WxH with an optional origin. root.geometry() always returns
    # the long form, so the long form is what _save_config writes.
    _GEOMETRY_RE = re.compile(r"^(\d+)x(\d+)(?:([+-])(\d+)([+-])(\d+))?$")

    def _sanitize_geometry(self, geometry):
        """Return a geometry string Tk will accept, dropping a dead origin.

        Two failures this guards. A hand-edited or truncated value raises
        TclError out of root.geometry(), which runs before the window exists,
        so the app does not start. And an origin saved on a monitor that is no
        longer attached reopens the window where the user cannot reach it, so
        the offset is kept only while it still lands on a screen that exists
        now. A negative sign anchors to the right or bottom edge, which is
        always present, so those are left alone.
        """
        match = self._GEOMETRY_RE.match(str(geometry or "").strip())
        if not match:
            return self.DEFAULT_GEOMETRY
        width, height, x_sign, x, y_sign, y = match.groups()
        size = f"{width}x{height}"
        if x_sign is None:
            return size
        if x_sign == "+" and int(x) >= self.root.winfo_screenwidth():
            return size
        if y_sign == "+" and int(y) >= self.root.winfo_screenheight():
            return size
        return f"{size}{x_sign}{x}{y_sign}{y}"

    def _load_config(self):
        """Load saved settings from config file"""
        # Nothing here may raise. This runs inside SnatchApp.__init__ before
        # any window exists, so an unreadable or malformed config.json stopped
        # the app launching at all, with no UI route to repair it. Only
        # FileNotFoundError and JSONDecodeError were caught; PermissionError,
        # IsADirectoryError, UnicodeDecodeError and valid-but-wrong-shaped
        # JSON all escaped. Same fix history.json took in _load_history.
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError) as exc:
            log.warning("Could not read %s: %s", self.config_file, exc)
            return {}
        # ValueError above covers JSONDecodeError and UnicodeDecodeError.
        # A bare 5 or a list parses fine and then breaks saved_config.get().
        if not isinstance(data, dict):
            log.warning("Ignoring %s: expected an object, got %s",
                        self.config_file, type(data).__name__)
            return {}
        return data

    def _save_config(self):
        """Save current settings to config file"""
        config = {
            "save_path": self.save_path_var.get(),
            "media_file": self.media_file_var.get(),
            "window_geometry": self.root.geometry(),
            "preferred_resolution": self.preferred_resolution,
            "preferred_ext": self.preferred_ext,
            "browser": self.browser_var.get(),
            "merge_audio": self.merge_audio_var.get(),
            "subtitles": self.subtitle_var.get(),
            "sponsorblock": self.sponsorblock_var.get(),
            "speed_limit": self.speed_limit_var.get(),
            "theme": self.theme_var.get(),
            "last_tab": self.notebook.index(self.notebook.select()),
        }
        try:
            write_private_json(self.config_file, config)
        except OSError:
            log.warning("Could not save config to %s",
                        self.config_file, exc_info=True)

    def _set_icon(self):
        """Set the window icon from the bundled icon file"""
        icon_path = os.path.join(self.script_dir, "icon.png")
        if os.path.isfile(icon_path):
            try:
                self._icon = tk.PhotoImage(file=icon_path)
                self.root.iconphoto(True, self._icon)
            except Exception:
                log.debug("Window icon %s could not be loaded",
                          icon_path, exc_info=True)

    def create_widgets(self):
        # Main container with padding
        self.main_frame = ttk.Frame(self.root, padding="20")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Header with title and version
        header_frame = ttk.Frame(self.main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 15))

        title_label = ttk.Label(header_frame, text="Snatch",
                                style="Title.TLabel")
        title_label.pack(side=tk.LEFT)

        # Version, theme selector, and update section
        version_frame = ttk.Frame(header_frame)
        version_frame.pack(side=tk.RIGHT)

        # Theme selector
        ttk.Label(version_frame, text="Theme:",
                  style="Version.TLabel").pack(side=tk.LEFT, padx=(0, 4))
        self.theme_combo = ttk.Combobox(version_frame, textvariable=self.theme_var,
                                        values=list(THEMES.keys()),
                                        state="readonly", width=10)
        self.theme_combo.pack(side=tk.LEFT, padx=(0, 12))
        self.theme_combo.bind("<<ComboboxSelected>>", lambda e: self._change_theme())

        self.version_label = ttk.Label(version_frame, textvariable=self.version_var,
                                        style="Version.TLabel")
        self.version_label.pack(side=tk.LEFT, padx=(0, 10))

        self.update_btn = ttk.Button(version_frame, text="Up to date",
                                      command=self.update_ytdlp, style="Small.TButton",
                                      state=tk.DISABLED)
        self.update_btn.pack(side=tk.LEFT)

        # Notebook (tabs)
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Tab 1: Download
        download_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(download_tab, text="Download")
        self._create_download_tab(download_tab)

        # Tab 2: Search
        search_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(search_tab, text="Search")
        self._create_search_tab(search_tab)

        # Tab 3: Media Info
        media_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(media_tab, text="Media Info")
        self._create_media_info_tab(media_tab)

        # Tab 4: History
        history_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(history_tab, text="History")
        self._create_history_tab(history_tab)

    def _cleanup_toggles(self):
        """Remove trace callbacks from all ToggleSwitch widgets"""
        for name in ('merge_toggle', 'subtitle_toggle', 'sponsorblock_toggle'):
            widget = getattr(self, name, None)
            if widget:
                widget.cleanup()

    def _change_theme(self):
        """Switch theme and rebuild the UI"""
        theme_name = self.theme_var.get()
        set_theme(theme_name)
        theme = get_theme()

        # Re-apply ttk styles
        setup_styles(theme)

        # Update root background
        self.root.configure(bg=theme.BG)

        # Stop active player and animation before destroying widgets
        self._stop_player()
        self._stop_search_anim()

        # Clean up before destroying widgets
        self._cleanup_toggles()
        self.formats = []
        self.playlist_entries = []
        self.video_thumbnail = None
        self.search_results = []

        # Rebuild UI — destroy and recreate all widgets
        current_tab = self.notebook.index(self.notebook.select())
        self.main_frame.destroy()
        self.create_widgets()
        if 0 <= current_tab < self.notebook.index("end"):
            self.notebook.select(current_tab)

        # Re-apply drag & drop on new widgets
        if HAS_DND:
            self._setup_drag_drop()

        # Re-populate data that was loaded before
        if hasattr(self, 'history_tree'):
            self._load_history_into_tree()

        # Restore the update button. create_widgets rebuilds it as a disabled
        # "Up to date", while version_var survives and keeps showing the old
        # text — so a user with a pending yt-dlp update who changed theme was
        # left with a disabled button contradicting the label and no route to
        # the update until restart.
        if self.latest_version and self.current_version and \
                self._version_compare(self.latest_version, self.current_version) > 0:
            # Deliberately NOT _show_update_available(): that ends in
            # _prompt_update(), which opens a modal dialog. Calling it here
            # would pop an update prompt on every theme switch. Only the
            # button state needs restoring; the user has already been asked.
            self.update_btn.config(text=f"Update to {self.latest_version}",
                                   state=tk.NORMAL)
        else:
            self._refresh_idle_button()

        # Update format tree tag colors
        if hasattr(self, 'format_tree'):
            self.format_tree.tag_configure("video_only", foreground=theme.VIDEO_ONLY)
            self.format_tree.tag_configure("audio_only", foreground=theme.AUDIO_ONLY)
            self.format_tree.tag_configure("muxed", foreground=theme.SUCCESS)

        self._save_config()

    def _setup_keyboard_shortcuts(self):
        """Bind global keyboard shortcuts"""
        self.root.bind("<Control-d>", lambda e: self.download_selected())
        self.root.bind("<Control-Return>", lambda e: self.fetch_formats())
        self.root.bind("<Control-q>", lambda e: self._add_to_queue())
        self.root.bind("<Control-o>", lambda e: self._open_download_folder())
        self.root.bind("<Control-l>", lambda e: self._focus_url_entry())
        self.root.bind("<Control-f>", lambda e: self._focus_search_entry())
        self.root.bind("<Control-Key-1>", lambda e: self.notebook.select(0))
        self.root.bind("<Control-Key-2>", lambda e: self.notebook.select(1))
        self.root.bind("<Control-Key-3>", lambda e: self.notebook.select(2))
        self.root.bind("<Control-Key-4>", lambda e: self.notebook.select(3))

    def _focus_url_entry(self):
        """Focus the URL entry and switch to Download tab"""
        self.notebook.select(0)
        self.url_entry.focus_set()
        self.url_entry.select_range(0, tk.END)

    def _focus_search_entry(self):
        """Focus the search entry and switch to Search tab"""
        self.notebook.select(1)
        self.search_entry.focus_set()
        self.search_entry.select_range(0, tk.END)

    def _update_title_progress(self, percent=None, text=None):
        """Update window title with download progress"""
        if text:
            self.root.title(f"[{text}] {self._base_title}")
        elif percent is not None:
            self.root.title(f"[{percent:.0f}%] {self._base_title}")
        else:
            self.root.title(self._base_title)

    def _on_close(self):
        """Handle window close -- confirm if a download is active"""
        if self.is_downloading:
            if not messagebox.askyesno("Download in Progress",
                                       "A download is still running.\n\n"
                                       "Are you sure you want to quit?"):
                return
            self.cancel_download()
        self._stop_player()
        self._stop_search_anim()
        self._save_config()

        self._cleanup_toggles()

        # Release large data structures
        self.formats = []
        self.search_results = []
        self.playlist_entries = []
        self.download_queue = []
        self.video_thumbnail = None
        HistoryTabMixin._history_cache = None

        self.root.destroy()
