"""Platform-aware helpers — paths, binary resolution, file-open.

When running from source (dev mode), behaves identically to the pre-existing
Linux logic so nothing regresses. When frozen by PyInstaller (Windows .exe),
resolves bundled binaries from sys._MEIPASS and writes user data next to the
.exe itself rather than into the temp-extraction directory.
"""

import os
import shutil
import subprocess
import sys


def is_windows():
    return sys.platform == "win32"


def is_macos():
    return sys.platform == "darwin"


def is_frozen():
    """True when running inside a PyInstaller bundle."""
    return getattr(sys, "frozen", False)


def app_data_dir():
    """Directory for user data (config.json, history.json, cookies.txt, downloads).

    Frozen .exe: the directory containing the .exe — user data lives next to it.
    Dev mode: the project root (same as the previous script_dir behaviour).
    """
    if is_frozen():
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def resource_path(*parts):
    """Locate a bundled read-only resource (icon, binary, data file).

    Frozen: sys._MEIPASS is PyInstaller's runtime extraction dir.
    Dev: project root.
    """
    if is_frozen():
        base = sys._MEIPASS  # noqa: SLF001 — PyInstaller's documented API
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *parts)


def _find_bundled_binary(name):
    """Return the path to a bundled binary if present, else None.

    Looks in <_MEIPASS>/bin/<name>(.exe) when frozen.
    """
    if not is_frozen():
        return None
    candidate = resource_path("bin", name + (".exe" if is_windows() else ""))
    if os.path.isfile(candidate):
        return candidate
    return None


def find_ytdlp():
    """Resolve the yt-dlp binary. Bundled copy wins; otherwise falls back to PATH."""
    bundled = _find_bundled_binary("yt-dlp")
    if bundled:
        return bundled
    on_path = shutil.which("yt-dlp")
    if on_path:
        return on_path
    return "yt-dlp"  # last-resort literal — subprocess will surface FileNotFoundError


def find_ffmpeg():
    """Resolve ffmpeg. Returns None if not found (caller should omit --ffmpeg-location)."""
    bundled = _find_bundled_binary("ffmpeg")
    if bundled:
        return bundled
    return shutil.which("ffmpeg")


def find_ffprobe():
    """Resolve ffprobe. Bundled copy wins; otherwise falls back to PATH; otherwise 'ffprobe'."""
    bundled = _find_bundled_binary("ffprobe")
    if bundled:
        return bundled
    on_path = shutil.which("ffprobe")
    if on_path:
        return on_path
    return "ffprobe"


def open_path(target):
    """Open a file, folder, or URL in the OS default handler.

    Cross-platform replacement for `subprocess.Popen(["xdg-open", "--", target])`.
    Safe against argument injection — uses os.startfile on Windows (no shell)
    and the dedicated openers on macOS/Linux with `--` separator.
    """
    if not target:
        return
    if is_windows():
        # os.startfile is the Windows-native way; honours file associations.
        os.startfile(target)  # noqa: S606 — intentional, Windows-only API
        return
    if is_macos():
        subprocess.Popen(["open", "--", target])
        return
    subprocess.Popen(["xdg-open", "--", target])
