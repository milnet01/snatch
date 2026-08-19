"""Theme definitions and ttk style configuration"""

from tkinter import ttk


class DarkTheme:
    """Deep blue/purple dark theme with red accent"""
    NAME = "Dark"
    BG = "#1a1a2e"
    BG_LIGHT = "#16213e"
    BG_LIGHTER = "#1f3460"
    FG = "#eaeaea"
    FG_DIM = "#a0a0a0"
    ACCENT = "#e94560"
    ACCENT_HOVER = "#ff6b6b"
    SUCCESS = "#4ecca3"
    ENTRY_BG = "#0f0f1a"
    BORDER = "#2a2a4a"
    TREEVIEW_BG = "#0f0f1a"
    TREEVIEW_SELECT = "#e94560"
    BUTTON_BG = "#e94560"
    BUTTON_FG = "#ffffff"
    PLAYER_BG = "#000000"
    VIDEO_ONLY = "#ffaa00"
    AUDIO_ONLY = "#66bbff"
    SUBTITLE_ON = "#66bbff"
    SPONSORBLOCK_ON = "#2ecc71"
    KNOB = "#ffffff"
    ACCENT_BUTTON_FG = "#000000"
    ACCENT_BUTTON_HOVER = "#6ee6b8"


class NordTheme:
    """Nord-inspired dark theme with cool blue tones"""
    NAME = "Nord"
    BG = "#2e3440"
    BG_LIGHT = "#3b4252"
    BG_LIGHTER = "#434c5e"
    FG = "#eceff4"
    FG_DIM = "#8892a4"
    ACCENT = "#88c0d0"
    ACCENT_HOVER = "#8fbcbb"
    SUCCESS = "#a3be8c"
    ENTRY_BG = "#272c36"
    BORDER = "#4c566a"
    TREEVIEW_BG = "#272c36"
    TREEVIEW_SELECT = "#5e81ac"
    BUTTON_BG = "#5e81ac"
    BUTTON_FG = "#eceff4"
    PLAYER_BG = "#000000"
    VIDEO_ONLY = "#ebcb8b"
    AUDIO_ONLY = "#81a1c1"
    SUBTITLE_ON = "#81a1c1"
    SPONSORBLOCK_ON = "#a3be8c"
    KNOB = "#eceff4"
    ACCENT_BUTTON_FG = "#2e3440"
    ACCENT_BUTTON_HOVER = "#b5d1a5"


class MonokaiTheme:
    """Monokai-inspired dark theme with vibrant accents"""
    NAME = "Monokai"
    BG = "#272822"
    BG_LIGHT = "#2d2e27"
    BG_LIGHTER = "#3e3d32"
    FG = "#f8f8f2"
    FG_DIM = "#90908a"
    ACCENT = "#f92672"
    ACCENT_HOVER = "#ff5c8d"
    SUCCESS = "#a6e22e"
    ENTRY_BG = "#1e1f1c"
    BORDER = "#49483e"
    TREEVIEW_BG = "#1e1f1c"
    TREEVIEW_SELECT = "#49483e"
    BUTTON_BG = "#f92672"
    BUTTON_FG = "#f8f8f2"
    PLAYER_BG = "#000000"
    VIDEO_ONLY = "#e6db74"
    AUDIO_ONLY = "#66d9ef"
    SUBTITLE_ON = "#66d9ef"
    SPONSORBLOCK_ON = "#a6e22e"
    KNOB = "#f8f8f2"
    ACCENT_BUTTON_FG = "#272822"
    ACCENT_BUTTON_HOVER = "#bef05a"


class YouTubeTheme:
    """YouTube dark mode colour scheme"""
    NAME = "YouTube"
    BG = "#0f0f0f"
    BG_LIGHT = "#1a1a1a"
    BG_LIGHTER = "#272727"
    FG = "#f1f1f1"
    FG_DIM = "#aaaaaa"
    ACCENT = "#ff0000"
    ACCENT_HOVER = "#cc0000"
    SUCCESS = "#3ea6ff"
    ENTRY_BG = "#121212"
    BORDER = "#303030"
    TREEVIEW_BG = "#121212"
    TREEVIEW_SELECT = "#3e3e3e"
    BUTTON_BG = "#cc0000"
    BUTTON_FG = "#ffffff"
    PLAYER_BG = "#000000"
    VIDEO_ONLY = "#f2a832"
    AUDIO_ONLY = "#3ea6ff"
    SUBTITLE_ON = "#3ea6ff"
    SPONSORBLOCK_ON = "#2ba640"
    KNOB = "#ffffff"
    ACCENT_BUTTON_FG = "#ffffff"
    ACCENT_BUTTON_HOVER = "#65b8ff"


class DraculaTheme:
    """Dracula colour palette — dark with pastel accents"""
    NAME = "Dracula"
    BG = "#282a36"
    BG_LIGHT = "#2d303d"
    BG_LIGHTER = "#44475a"
    FG = "#f8f8f2"
    FG_DIM = "#8b8fa8"
    ACCENT = "#bd93f9"
    ACCENT_HOVER = "#d4b4fc"
    SUCCESS = "#50fa7b"
    ENTRY_BG = "#21222c"
    BORDER = "#44475a"
    TREEVIEW_BG = "#21222c"
    TREEVIEW_SELECT = "#44475a"
    BUTTON_BG = "#bd93f9"
    BUTTON_FG = "#282a36"
    PLAYER_BG = "#000000"
    VIDEO_ONLY = "#f1fa8c"
    AUDIO_ONLY = "#8be9fd"
    SUBTITLE_ON = "#8be9fd"
    SPONSORBLOCK_ON = "#50fa7b"
    KNOB = "#f8f8f2"
    ACCENT_BUTTON_FG = "#282a36"
    ACCENT_BUTTON_HOVER = "#7afc9e"


class GruvboxTheme:
    """Gruvbox dark — warm retro colour scheme"""
    NAME = "Gruvbox"
    BG = "#282828"
    BG_LIGHT = "#3c3836"
    BG_LIGHTER = "#504945"
    FG = "#ebdbb2"
    FG_DIM = "#928374"
    ACCENT = "#fe8019"
    ACCENT_HOVER = "#fabd2f"
    SUCCESS = "#b8bb26"
    ENTRY_BG = "#1d2021"
    BORDER = "#504945"
    TREEVIEW_BG = "#1d2021"
    TREEVIEW_SELECT = "#504945"
    BUTTON_BG = "#fe8019"
    BUTTON_FG = "#1d2021"
    PLAYER_BG = "#000000"
    VIDEO_ONLY = "#fabd2f"
    AUDIO_ONLY = "#83a598"
    SUBTITLE_ON = "#83a598"
    SPONSORBLOCK_ON = "#b8bb26"
    KNOB = "#ebdbb2"
    ACCENT_BUTTON_FG = "#1d2021"
    ACCENT_BUTTON_HOVER = "#d1d935"


class SolarizedTheme:
    """Solarized Dark — Ethan Schoonover's precision colour scheme"""
    NAME = "Solarized"
    BG = "#002b36"
    BG_LIGHT = "#073642"
    BG_LIGHTER = "#0a4352"
    FG = "#93a1a1"
    FG_DIM = "#657b83"
    ACCENT = "#268bd2"
    ACCENT_HOVER = "#2aa198"
    SUCCESS = "#859900"
    ENTRY_BG = "#00242e"
    BORDER = "#0a4352"
    TREEVIEW_BG = "#00242e"
    TREEVIEW_SELECT = "#073642"
    BUTTON_BG = "#268bd2"
    BUTTON_FG = "#fdf6e3"
    PLAYER_BG = "#000000"
    VIDEO_ONLY = "#b58900"
    AUDIO_ONLY = "#2aa198"
    SUBTITLE_ON = "#2aa198"
    SPONSORBLOCK_ON = "#859900"
    KNOB = "#eee8d5"
    ACCENT_BUTTON_FG = "#002b36"
    ACCENT_BUTTON_HOVER = "#99a514"


# Registry of all available themes
THEMES = {
    "Dark": DarkTheme,
    "Nord": NordTheme,
    "Monokai": MonokaiTheme,
    "YouTube": YouTubeTheme,
    "Dracula": DraculaTheme,
    "Gruvbox": GruvboxTheme,
    "Solarized": SolarizedTheme,
}

# Active theme (module-level, set at startup and on theme change)
active_theme = DarkTheme


def get_theme():
    """Return the currently active theme class"""
    return active_theme


def set_theme(name):
    """Set the active theme by name and return the theme class"""
    global active_theme
    active_theme = THEMES.get(name, DarkTheme)
    return active_theme


def setup_styles(theme=None):
    """Configure ttk styles for the given theme (or active theme)"""
    if theme is None:
        theme = active_theme

    style = ttk.Style()
    style.theme_use("clam")

    # Frame styles
    style.configure("TFrame", background=theme.BG)
    style.configure("TLabelframe", background=theme.BG, foreground=theme.FG,
                   bordercolor=theme.BORDER, relief="solid")
    style.configure("TLabelframe.Label", background=theme.BG, foreground=theme.ACCENT,
                   font=("Helvetica", 10, "bold"))

    # Label styles
    style.configure("TLabel", background=theme.BG, foreground=theme.FG)
    style.configure("Title.TLabel", background=theme.BG, foreground=theme.ACCENT,
                   font=("Helvetica", 18, "bold"))
    style.configure("Version.TLabel", background=theme.BG, foreground=theme.FG_DIM,
                   font=("Helvetica", 9))
    style.configure("Status.TLabel", background=theme.BG, foreground=theme.SUCCESS,
                   font=("Helvetica", 9))

    # Entry styles
    style.configure("TEntry", fieldbackground=theme.ENTRY_BG, foreground=theme.FG,
                   insertcolor=theme.FG, bordercolor=theme.BORDER)
    style.map("TEntry",
              fieldbackground=[("focus", theme.BG_LIGHTER)],
              bordercolor=[("focus", theme.ACCENT)])

    # Button styles
    style.configure("TButton", background=theme.BUTTON_BG, foreground=theme.BUTTON_FG,
                   bordercolor=theme.ACCENT, focuscolor=theme.ACCENT,
                   font=("Helvetica", 9, "bold"), padding=(12, 6))
    style.map("TButton",
              background=[("active", theme.ACCENT_HOVER), ("disabled", theme.BG_LIGHTER)],
              foreground=[("disabled", theme.FG_DIM)])

    # Accent button (for primary actions)
    style.configure("Accent.TButton", background=theme.SUCCESS, foreground=theme.ACCENT_BUTTON_FG,
                   font=("Helvetica", 10, "bold"), padding=(15, 8))
    style.map("Accent.TButton",
              background=[("active", theme.ACCENT_BUTTON_HOVER), ("disabled", theme.BG_LIGHTER)],
              foreground=[("disabled", theme.FG_DIM)])

    # Small button style
    style.configure("Small.TButton", padding=(8, 4), font=("Helvetica", 8))

    # Treeview styles
    style.configure("Treeview",
                   background=theme.TREEVIEW_BG,
                   foreground=theme.FG,
                   fieldbackground=theme.TREEVIEW_BG,
                   bordercolor=theme.BORDER,
                   font=("Helvetica", 9))
    style.configure("Treeview.Heading",
                   background=theme.BG_LIGHTER,
                   foreground=theme.FG,
                   bordercolor=theme.BORDER,
                   font=("Helvetica", 9, "bold"))
    style.map("Treeview",
              background=[("selected", theme.TREEVIEW_SELECT)],
              foreground=[("selected", theme.BUTTON_FG)])
    style.map("Treeview.Heading",
              background=[("active", theme.BG_LIGHT)])

    # Progressbar styles
    style.configure("TProgressbar",
                   background=theme.ACCENT,
                   troughcolor=theme.BG_LIGHT,
                   bordercolor=theme.BORDER,
                   lightcolor=theme.ACCENT,
                   darkcolor=theme.ACCENT)

    # Scrollbar styles
    style.configure("Vertical.TScrollbar",
                   background=theme.BG_LIGHTER,
                   troughcolor=theme.BG_LIGHT,
                   bordercolor=theme.BG,
                   arrowcolor=theme.FG)
    style.map("Vertical.TScrollbar",
              background=[("active", theme.ACCENT)])

    # Notebook (tab) styles
    style.configure("TNotebook", background=theme.BG, bordercolor=theme.BORDER)
    style.configure("TNotebook.Tab", background=theme.BG_LIGHT, foreground=theme.FG_DIM,
                   font=("Helvetica", 10, "bold"), padding=(16, 6))
    style.map("TNotebook.Tab",
              background=[("selected", theme.BG), ("active", theme.BG_LIGHTER)],
              foreground=[("selected", theme.ACCENT), ("active", theme.FG)])

    # Combobox styles
    style.configure("TCombobox",
                   fieldbackground=theme.ENTRY_BG,
                   background=theme.BG_LIGHTER,
                   foreground=theme.FG,
                   arrowcolor=theme.FG,
                   bordercolor=theme.BORDER)
    style.map("TCombobox",
              fieldbackground=[("readonly", theme.ENTRY_BG)],
              foreground=[("readonly", theme.FG)])

    # Checkbutton style for dark theme
    style.configure("Dark.TCheckbutton",
                   background=theme.BG,
                   foreground=theme.FG,
                   font=("Helvetica", 9))
    style.map("Dark.TCheckbutton",
              background=[("active", theme.BG)],
              foreground=[("active", theme.FG)])

    # Radiobutton style for dark theme
    style.configure("Dark.TRadiobutton",
                   background=theme.BG,
                   foreground=theme.FG,
                   font=("Helvetica", 9))
    style.map("Dark.TRadiobutton",
              background=[("active", theme.BG)],
              foreground=[("active", theme.FG)])

    # Scale style for dark theme
    style.configure("TScale",
                   background=theme.BG,
                   troughcolor=theme.BG_LIGHT)
