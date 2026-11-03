"""Which builds can update, and how the swap and relaunch go (SNAT-0038).

Real Windows file locking cannot happen on Linux, so INV-9 is checked with
`os.replace` made to fail; the live recipe in the spec covers the real thing.
"""

import os
import stat
import subprocess
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from snatch import update_installer
from snatch.app import SnatchApp
from snatch.update_installer import (AppImageInstaller, UpdateInstallError,
                                     WindowsInstaller, cleanup_stale,
                                     detect_installer, install_and_relaunch)

DETACHED_PROCESS = 0x00000008


@pytest.fixture
def platform(monkeypatch):
    """Pretend to be a frozen build on Linux unless a test says otherwise."""
    state = {"frozen": True, "windows": False, "macos": False}
    monkeypatch.setattr(update_installer, "is_frozen", lambda: state["frozen"])
    monkeypatch.setattr(update_installer, "is_windows", lambda: state["windows"])
    monkeypatch.setattr(update_installer, "is_macos", lambda: state["macos"])
    return state


@pytest.fixture
def appimage(tmp_path, monkeypatch):
    """A mounted AppImage: the file in a folder, and its mount elsewhere."""
    image = tmp_path / "apps" / "Snatch-x86_64.AppImage"
    image.parent.mkdir()
    image.write_bytes(b"old build")
    appdir = tmp_path / "mount"
    (appdir / "usr" / "bin").mkdir(parents=True)
    exe = appdir / "usr" / "bin" / "snatch"
    exe.write_bytes(b"")
    monkeypatch.setenv("APPIMAGE", str(image))
    monkeypatch.setenv("APPDIR", str(appdir))
    monkeypatch.setattr(update_installer.sys, "executable", str(exe))
    return image


# ── INV-8: only a real AppImage or a frozen Windows build can update ─────

def test_detect_an_appimage(platform, appimage):
    installer = detect_installer()
    assert isinstance(installer, AppImageInstaller)
    assert installer.target == Path(os.path.realpath(appimage))


def test_detect_a_windows_build(platform, tmp_path, monkeypatch):
    platform["windows"] = True
    exe = tmp_path / "snatch.exe"
    exe.write_bytes(b"")
    monkeypatch.setattr(update_installer.sys, "executable", str(exe))
    installer = detect_installer()
    assert isinstance(installer, WindowsInstaller)
    assert installer.asset_name == "snatch.exe"


def test_detect_a_source_run_is_none(platform, appimage):
    platform["frozen"] = False
    assert detect_installer() is None


def test_detect_macos_is_none(platform, appimage):
    platform["macos"] = True
    assert detect_installer() is None


def test_detect_an_unwritable_target_is_none(platform, appimage, monkeypatch):
    monkeypatch.setattr(update_installer, "_is_writable_dir", lambda _p: False)
    assert detect_installer() is None


def test_detect_an_inherited_appimage_variable_is_none(
        platform, appimage, tmp_path, monkeypatch):
    # Started from another AppImage: $APPIMAGE and $APPDIR are its, and this
    # process's executable is somewhere else entirely.
    other = tmp_path / "elsewhere" / "snatch"
    other.parent.mkdir()
    other.write_bytes(b"")
    monkeypatch.setattr(update_installer.sys, "executable", str(other))
    assert detect_installer() is None


def test_detect_a_missing_appimage_file_is_none(platform, appimage):
    appimage.unlink()
    assert detect_installer() is None


def test_detect_without_appdir_is_none(platform, appimage, monkeypatch):
    monkeypatch.delenv("APPDIR")
    assert detect_installer() is None


# ── Installing ────────────────────────────────────────────────────────────

def _new_build(folder):
    temp = folder / ".snatch-update-abc"
    temp.write_bytes(b"new build")
    return temp


def test_appimage_install_replaces_the_file(tmp_path):
    image = tmp_path / "Snatch-x86_64.AppImage"
    image.write_bytes(b"old build")
    AppImageInstaller(image).install(str(_new_build(tmp_path)))
    assert image.read_bytes() == b"new build"
    assert stat.S_IMODE(image.stat().st_mode) == 0o755
    assert sorted(p.name for p in tmp_path.iterdir()) == [image.name]


def test_windows_install_moves_the_running_file_aside(tmp_path):
    exe = tmp_path / "snatch.exe"
    exe.write_bytes(b"old build")
    WindowsInstaller(exe).install(str(_new_build(tmp_path)))
    assert exe.read_bytes() == b"new build"
    assert (tmp_path / "snatch.exe.old").read_bytes() == b"old build"


@pytest.mark.parametrize("locked_old", [False, True], ids=["old", "old-1"])
def test_windows_failed_replace_restores_the_original(
        tmp_path, monkeypatch, locked_old):
    exe = tmp_path / "snatch.exe"
    exe.write_bytes(b"old build")
    if locked_old:
        # A directory cannot be unlinked, which stands in for a .old still
        # held by a previous run, so the install has to use .old-1.
        (tmp_path / "snatch.exe.old").mkdir()
    temp = _new_build(tmp_path)

    def held_by_antivirus(_src, _dst):
        raise PermissionError("in use")
    monkeypatch.setattr(update_installer.os, "replace", held_by_antivirus)
    monkeypatch.setattr(update_installer.time, "sleep", lambda _s: None)

    with pytest.raises(UpdateInstallError):
        WindowsInstaller(exe).install(str(temp))
    assert exe.read_bytes() == b"old build"
    assert not temp.exists()
    assert not (tmp_path / "snatch.exe.old-1").exists()
    assert (tmp_path / "snatch.exe.old").is_dir() == locked_old


# ── INV-10: state is saved before the new process starts ─────────────────

class _Exited(Exception):
    pass


class Host:
    """Just enough app for SnatchApp's own close and shutdown methods."""

    _confirm_close = SnatchApp._confirm_close
    _shutdown_state = SnatchApp._shutdown_state

    def __init__(self, order):
        self.is_downloading = False
        self.cancel_download = MagicMock()
        self._stop_player = MagicMock()
        self._stop_search_anim = MagicMock()
        self._save_config = lambda: order.append("config")
        self._save_queue = lambda: order.append("queue")


def _record_spawns(monkeypatch, order, fail=False):
    calls = []

    def popen(args, **kwargs):
        order.append("spawn")
        calls.append((args, kwargs))
        if fail:
            raise OSError("cannot start")
        return MagicMock()

    def exit_(code):
        order.append(f"exit {code}")
        raise _Exited

    monkeypatch.setattr(update_installer.subprocess, "Popen", popen)
    monkeypatch.setattr(update_installer.os, "_exit", exit_)
    return calls


def test_state_saved_before_spawn(tmp_path, monkeypatch):
    order = []
    _record_spawns(monkeypatch, order)
    image = tmp_path / "Snatch-x86_64.AppImage"
    image.write_bytes(b"old build")
    with pytest.raises(_Exited):
        install_and_relaunch(Host(order), AppImageInstaller(image),
                             str(_new_build(tmp_path)))
    assert order == ["config", "queue", "spawn", "exit 0"]


def test_declining_to_stop_downloads_installs_nothing(tmp_path, monkeypatch):
    order = []
    _record_spawns(monkeypatch, order)
    monkeypatch.setattr("snatch.app.messagebox.askyesno", lambda *a, **k: False)
    host = Host(order)
    host.is_downloading = True
    image = tmp_path / "Snatch-x86_64.AppImage"
    image.write_bytes(b"old build")
    temp = _new_build(tmp_path)
    assert install_and_relaunch(host, AppImageInstaller(image), str(temp)) is False
    assert order == []
    assert not temp.exists()
    assert image.read_bytes() == b"old build"


# ── INV-11: the relaunch is an argument list with a cleaned environment ──

@pytest.fixture
def bundle_env(monkeypatch):
    for name in ("APPIMAGE", "APPDIR", "ARGV0"):
        monkeypatch.setenv(name, "from the old bundle")
    monkeypatch.delenv("PYINSTALLER_RESET_ENVIRONMENT", raising=False)


def _relaunch(monkeypatch, installer, fail=False):
    order = []
    calls = _record_spawns(monkeypatch, order, fail=fail)
    with pytest.raises(_Exited):
        installer.relaunch()
    return calls, order


def _assert_clean_spawn(args, kwargs, target):
    assert args == [str(target)]
    assert "shell" not in kwargs
    env = kwargs["env"]
    assert not {"APPIMAGE", "APPDIR", "ARGV0"} & set(env)
    assert env["PYINSTALLER_RESET_ENVIRONMENT"] == "1"
    for stream in ("stdin", "stdout", "stderr"):
        assert kwargs[stream] is subprocess.DEVNULL
    assert kwargs["close_fds"] is True


def test_relaunch_appimage_starts_a_new_session(monkeypatch, bundle_env):
    target = Path("/apps/Snatch-x86_64.AppImage")
    calls, _ = _relaunch(monkeypatch, AppImageInstaller(target))
    (args, kwargs), = calls
    _assert_clean_spawn(args, kwargs, target)
    assert kwargs["start_new_session"] is True


def test_relaunch_windows_never_detaches(monkeypatch, bundle_env):
    target = Path("C:/Snatch/snatch.exe")
    calls, _ = _relaunch(monkeypatch, WindowsInstaller(target))
    (args, kwargs), = calls
    _assert_clean_spawn(args, kwargs, target)
    assert kwargs["creationflags"] & update_installer.CREATE_NEW_PROCESS_GROUP
    assert not kwargs["creationflags"] & DETACHED_PROCESS
    assert "start_new_session" not in kwargs


def test_relaunch_exits_even_when_the_spawn_fails(monkeypatch, bundle_env):
    _, order = _relaunch(monkeypatch, AppImageInstaller(Path("/x")), fail=True)
    assert order == ["spawn", "exit 0"]


def test_relaunch_leaves_this_process_environment_alone(monkeypatch, bundle_env):
    _relaunch(monkeypatch, AppImageInstaller(Path("/x")))
    assert os.environ["APPDIR"] == "from the old bundle"


# ── Cleanup at start ──────────────────────────────────────────────────────

def test_cleanup_removes_only_stale_update_files(tmp_path):
    exe = tmp_path / "snatch.exe"
    exe.write_bytes(b"running")
    names = ["snatch.exe.old", "snatch.exe.old-2", ".snatch-update-stale",
             ".snatch-update-fresh", "config.json", "other.exe.old"]
    for name in names:
        (tmp_path / name).write_bytes(b"x")
    hours_ago = time.time() - 2 * 3600
    os.utime(tmp_path / ".snatch-update-stale", (hours_ago, hours_ago))

    cleanup_stale(WindowsInstaller(exe))
    assert sorted(p.name for p in tmp_path.iterdir()) == [
        ".snatch-update-fresh", "config.json", "other.exe.old", "snatch.exe"]
