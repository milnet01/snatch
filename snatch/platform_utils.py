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

    Frozen Windows .exe: the directory containing the .exe, so the app stays
    portable — copy the .exe and its data travels with it.

    Frozen macOS .app: ~/Library/Application Support/Snatch. Writing next to
    sys.executable would put user data *inside* the .app bundle, which breaks
    on upgrade and on a read-only /Applications mount.

    Frozen Linux AppImage: $XDG_DATA_HOME/snatch (default ~/.local/share/snatch).
    sys.executable points at PyInstaller's temp extraction dir, which is deleted
    on exit, so it can never hold user data.

    Dev mode: the project root (same as the previous script_dir behaviour).
    """
    if is_frozen():
        if is_windows():
            return os.path.dirname(os.path.abspath(sys.executable))
        if is_macos():
            base = os.path.expanduser("~/Library/Application Support")
            return _ensure_dir(os.path.join(base, "Snatch"))
        base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
        return _ensure_dir(os.path.join(base, "snatch"))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _ensure_dir(path):
    """Create a user-data directory 0700 if absent, and return it."""
    try:
        os.makedirs(path, mode=0o700, exist_ok=True)
    except OSError:
        pass
    return path


_USER_BIN_DIR = None


def _is_writable_dir(path):
    """True when a file can actually be created in `path`.

    os.access(W_OK) is not enough: it answers from the permission bits, and
    on Windows a directory can report writable and still refuse the write.
    Probing costs one create+unlink, which is why user_bin_dir() caches.
    """
    probe = os.path.join(path, ".snatch-write-probe")
    try:
        with open(probe, "w"):
            pass
        os.unlink(probe)
        return True
    except OSError:
        return False


def user_bin_dir():
    """Writable directory for binaries the app has fetched for itself.

    Sits inside app_data_dir(), so it survives an upgrade. The bundled copy
    lives in PyInstaller's extraction directory, which is read-only and
    deleted on exit -- that is precisely why a packaged build could not
    update its own yt-dlp before (SNAT-0016).

    Windows falls back to %LOCALAPPDATA%\\Snatch\\bin when the directory
    holding the .exe cannot be written to. app_data_dir() deliberately puts
    user data next to the .exe so the app stays portable, which is right on a
    USB stick and wrong under C:\\Program Files, where writing needs admin
    rights. ONLY this directory falls back: config.json and history.json stay
    where app_data_dir() puts them, because moving them would strand the
    settings of someone who already has them.

    Running from SOURCE it is app_data_dir()/bin/updated, not
    app_data_dir()/bin. From source app_data_dir() is the repo root, so the
    plain path is <repo>/bin -- the very directory scripts/fetch-binaries.sh
    fills with the PINNED copy a release bundles. A self-update therefore
    overwrote the pin and left no floor to fall back to, which made
    find_ytdlp()'s own docstring, docs/building.md and the dialog shown to
    the user ("The copy that came with Snatch is kept, so you can go back to
    it at any time") all false on that path. Frozen builds are unaffected:
    there the bundled copy lives in PyInstaller's extraction directory and
    never shared this one.

    Cached -- find_ytdlp() runs on every subprocess call and the Windows
    writability probe is a real filesystem write.
    """
    global _USER_BIN_DIR
    if _USER_BIN_DIR is None:
        parts = ["bin"] if is_frozen() else ["bin", "updated"]
        candidate = _ensure_dir(os.path.join(app_data_dir(), *parts))
        if is_windows() and not _is_writable_dir(candidate):
            base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
            candidate = _ensure_dir(os.path.join(base, "Snatch", "bin"))
        _USER_BIN_DIR = candidate
    return _USER_BIN_DIR


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

    Frozen: <_MEIPASS>/bin/<name>(.exe), the copy inside the packaged app.

    From source: the repo's own bin/ directory, which scripts/fetch-binaries.sh
    fills with the SAME pinned binaries a release ships. Without this a source
    run silently used whatever was on PATH, which is how a developer ended up
    on a yt-dlp that cannot play YouTube while the packaged build was fine --
    the pinned version is the fix, and a source run was not getting it. Absent
    until a build or fetch has run, in which case the PATH fallback applies as
    before.
    """
    suffix = ".exe" if is_windows() else ""
    if is_frozen():
        candidate = resource_path("bin", name + suffix)
        return candidate if os.path.isfile(candidate) else None
    repo_bin = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "bin", name + suffix)
    return repo_bin if os.path.isfile(repo_bin) else None


def _find_updated_binary(name):
    """Return a self-updated copy of `name` from user_bin_dir(), else None.

    Only yt-dlp is ever written here (SNAT-0016). It is the one bundled tool
    that goes stale on somebody else's schedule -- YouTube changes and yt-dlp
    has to chase it, faster than we cut releases. ffmpeg, mpv and QuickJS are
    stable and large, so they stay bundled and ship with a release.

    A file that is not executable is ignored rather than returned, so a
    half-written or wrongly-permissioned download falls through to the
    bundled copy instead of breaking the app.
    """
    suffix = ".exe" if is_windows() else ""
    candidate = os.path.join(user_bin_dir(), name + suffix)
    if not os.path.isfile(candidate):
        return None
    if not is_windows() and not os.access(candidate, os.X_OK):
        return None
    return candidate


def find_ytdlp():
    """Resolve yt-dlp: self-updated copy, then bundled, then PATH.

    The bundled copy stays as the floor, so a failed or half-written download
    can never leave the app with no yt-dlp at all.
    """
    updated = _find_updated_binary("yt-dlp")
    if updated:
        return updated
    bundled = _find_bundled_binary("yt-dlp")
    if bundled:
        return bundled
    on_path = shutil.which("yt-dlp")
    if on_path:
        return on_path
    return "yt-dlp"  # last-resort literal — subprocess will surface FileNotFoundError


def updated_ytdlp_path():
    """Path of the self-updated yt-dlp if one is in use, else None.

    Lets the UI offer a way back to the bundled copy without reaching into
    this module's private lookup (SNAT-0016).
    """
    return _find_updated_binary("yt-dlp")


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


def find_mpv():
    """Resolve mpv for the in-app player: bundled copy first, then PATH.

    mpv is bundled as a DIRECTORY (bin/mpv/) rather than a lone binary,
    because the Windows build needs its DLLs beside the executable. Returns
    the path to the executable, or None when there is no mpv at all — in
    which case the player falls back to opening the video in a browser.
    """
    if is_frozen():
        candidate = resource_path("bin", "mpv", "mpv" + (".exe" if is_windows() else ""))
        if os.path.isfile(candidate):
            return candidate
    return shutil.which("mpv")


def find_jsruntime():
    """Resolve a bundled JavaScript runtime, or None.

    yt-dlp needs one to solve YouTube's nsig challenges; without it,
    extraction is deprecated and some formats go missing. The packaged builds
    bundle QuickJS, so a user who downloaded a release never has to install
    Node.js or Deno. Returns (name, path) for --js-runtimes NAME:PATH, or None
    when running from source with nothing bundled.
    """
    bundled = _find_bundled_binary("qjs")
    if bundled:
        return ("quickjs", bundled)
    return None


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
