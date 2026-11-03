"""Replace the running Snatch with a verified update, and start it (SNAT-0038).

Only two builds can do this: the Linux AppImage and the frozen Windows
snatch.exe. Everything else -- a source run, macOS, a distro package --
gets None from detect_installer() and keeps opening the release page.

The file handed to install() has already been verified by
self_update.download_verified() and sits in the target's own folder, so
every move here is a same-volume rename.

Windows lets a running .exe be renamed but not deleted (measured on the test
box, 2026-11-03), so the old process moves itself aside and the new file
takes its name. There is no helper script: finbreak's PowerShell helper is
what left its Windows updates broken for a run of releases (FIBR-0444).
"""

import os
import platform
import subprocess
import sys
import time
from pathlib import Path

from .logging_setup import get_logger
from .platform_utils import _is_writable_dir, is_frozen, is_macos, is_windows

log = get_logger(__name__)

# Antivirus can hold a freshly written .exe for a moment.
REPLACE_ATTEMPTS = 5
REPLACE_RETRY_SEC = 0.5
# <target>.old, then <target>.old-1 ... when an earlier one is still locked.
OLD_NAME_ATTEMPTS = 10
# A .snatch-update-* younger than this may be another copy's live download.
STALE_TEMP_AGE_SEC = 3600
TEMP_PREFIX = ".snatch-update-"
# subprocess only defines this on Windows; the value is the Win32 constant.
CREATE_NEW_PROCESS_GROUP = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP",
                                   0x00000200)
# Variables naming the old bundle. The new process must find its own.
BUNDLE_VARIABLES = ("APPIMAGE", "APPDIR", "ARGV0")


class UpdateInstallError(Exception):
    """The swap did not happen; the running file is still in place."""


def discard(path):
    try:
        os.unlink(path)
    except FileNotFoundError:
        pass
    except OSError:
        log.warning("Could not remove %s", path, exc_info=True)


def _fsync_dir(folder):
    # Makes the rename durable. Windows cannot open a directory for this.
    fd = os.open(folder, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def child_environment():
    """os.environ for the new process, minus the old bundle's variables.

    PYINSTALLER_RESET_ENVIRONMENT makes the new bootloader reset its own
    _PYI_* variables; PyInstaller says code outside the bootloader must not
    change them, so they are left as they are.
    """
    env = {k: v for k, v in os.environ.items() if k not in BUNDLE_VARIABLES}
    env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    return env


class _Installer:
    def __init__(self, target):
        self.target = Path(target)

    def _spawn_options(self):
        raise NotImplementedError

    def relaunch(self):
        """Start the installed build and end this process. Never returns.

        Exits also when the spawn fails: the swap is already committed, so
        this process is the old version either way. The user starts the new
        one by hand.
        """
        try:
            subprocess.Popen([str(self.target)], env=child_environment(),
                             stdin=subprocess.DEVNULL,
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, close_fds=True,
                             **self._spawn_options())
        except OSError:
            log.exception("Could not start the updated Snatch at %s",
                          self.target)
        os._exit(0)


class AppImageInstaller(_Installer):
    """Replaces the .AppImage file. The running copy keeps its mounted image."""

    @property
    def asset_name(self):
        return f"Snatch-{platform.machine()}.AppImage"

    def install(self, temp_path):
        try:
            os.chmod(temp_path, 0o755)
            with open(temp_path, "rb") as handle:
                os.fsync(handle.fileno())
            os.replace(temp_path, self.target)
            _fsync_dir(self.target.parent)
        except OSError as exc:
            discard(temp_path)
            raise UpdateInstallError(str(exc)) from exc

    def _spawn_options(self):
        return {"start_new_session": True}


class WindowsInstaller(_Installer):
    """Moves the running snatch.exe aside and puts the new one in its place."""

    asset_name = "snatch.exe"

    def _old_names(self):
        old = self.target.with_name(self.target.name + ".old")
        yield old
        for n in range(1, OLD_NAME_ATTEMPTS):
            yield old.with_name(f"{old.name}-{n}")

    def _move_aside(self):
        """Rename the running target to a free .old name; return that name."""
        for old in self._old_names():
            try:
                old.unlink(missing_ok=True)
            except OSError:
                continue  # an earlier .old still running or locked
            os.rename(self.target, old)
            return old
        raise UpdateInstallError("no free name to move the running file to")

    def install(self, temp_path):
        try:
            moved = self._move_aside()
        except (OSError, UpdateInstallError) as exc:
            discard(temp_path)
            raise UpdateInstallError(str(exc)) from exc
        for attempt in range(REPLACE_ATTEMPTS):
            try:
                os.replace(temp_path, self.target)
                return
            except OSError as exc:
                failure = exc
                if attempt + 1 < REPLACE_ATTEMPTS:
                    time.sleep(REPLACE_RETRY_SEC)
        # INV-9: put the working copy back, so the user is never left with
        # no snatch.exe at all.
        try:
            os.rename(moved, self.target)
        except OSError:
            log.exception("Could not move %s back to %s", moved, self.target)
        discard(temp_path)
        raise UpdateInstallError(str(failure)) from failure

    def _spawn_options(self):
        # Never DETACHED_PROCESS (the spec's INV-11).
        return {"creationflags": CREATE_NEW_PROCESS_GROUP}


def detect_installer():
    """The installer for this build, or None to keep today's behaviour."""
    if not is_frozen():
        return None
    if is_windows():
        installer = WindowsInstaller(os.path.realpath(sys.executable))
    elif is_macos():
        return None
    else:
        # $APPIMAGE alone is not trusted: a program started from another
        # AppImage inherits it. This process must be running from $APPDIR.
        image, appdir = os.environ.get("APPIMAGE"), os.environ.get("APPDIR")
        if not image or not appdir or not os.path.isfile(image):
            return None
        exe = os.path.realpath(sys.executable)
        root = os.path.realpath(appdir)
        if os.path.commonpath([exe, root]) != root:
            return None
        installer = AppImageInstaller(os.path.realpath(image))
    # A real create-and-delete, not os.access: on Windows that said True for
    # a folder whose access list denied writing (measured 2026-11-03).
    if not _is_writable_dir(str(installer.target.parent)):
        return None
    return installer


def cleanup_stale(installer):
    """Delete leftovers of earlier updates from the target's own folder."""
    folder, name = installer.target.parent, installer.target.name
    now = time.time()
    try:
        entries = list(os.scandir(folder))
    except OSError:
        log.debug("Could not list %s", folder, exc_info=True)
        return
    for entry in entries:
        if entry.name.startswith(TEMP_PREFIX):
            try:
                if now - entry.stat().st_mtime < STALE_TEMP_AGE_SEC:
                    continue
            except OSError:
                continue
        elif not entry.name.startswith(name + ".old"):
            continue
        if not entry.is_file(follow_symlinks=False):
            continue
        try:
            os.unlink(entry.path)
        except OSError:
            log.debug("Left %s for next time", entry.path, exc_info=True)


def install_and_relaunch(app, installer, temp_path):
    """On the main thread: stop and save the app, swap, and restart.

    Returns False when the user chose to keep a running download, having
    deleted the update. Raises UpdateInstallError when the swap failed; the
    app then carries on as it was. Otherwise it does not return.
    """
    if not app._confirm_close():
        discard(temp_path)
        return False
    # Saves config and queue.json, and clears nothing, so a failed install
    # leaves the app usable. Nothing writes either file after this (INV-10).
    app._shutdown_state()
    installer.install(temp_path)
    installer.relaunch()
