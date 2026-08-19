"""Snatch — a yt-dlp frontend package"""

import shutil

try:
    from tkinterdnd2 import DND_TEXT, TkinterDnD
    HAS_DND = True
except ImportError:
    HAS_DND = False

HAS_MPV = shutil.which("mpv") is not None

__version__ = "0.1.0"
