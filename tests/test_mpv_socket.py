"""The mpv IPC socket must not be reachable by another user on the machine.

SNAT-0052. mpv's IPC accepts every input command, `loadfile` and `run`
included, so whoever can connect owns the player's command surface. The
socket used to be placed at `snatch-mpv-<pid>` -- fully predictable -- inside
XDG_RUNTIME_DIR, or, where that is unset (a non-systemd box, an su session, a
container), inside a shared world-writable /tmp. CLAUDE.md requires ownership
validation for this path without qualification, and the /tmp branch was never
checked at all. The check that did run tested st_uid but not mode, so a
self-owned 0777 runtime dir passed it.

tempfile.mkdtemp answers both: 0700 by construction, and an unpredictable
name. These tests assert the mode and the cleanup, because those are the two
properties an attacker's access depends on.

Nothing here launches mpv. _play_in_mpv is driven with a stubbed Popen, so
the tests run wherever the suite does.
"""

import os
import stat

import pytest

from snatch import player
from snatch.player import PlayerMixin


class _Silent:
    def place_forget(self):
        pass

    def place(self, **kwargs):
        pass

    def config(self, **kwargs):
        pass

    def winfo_id(self):
        return 0


class _Var:
    def __init__(self, value=""):
        self._value = value

    def get(self):
        return self._value

    def set(self, value):
        self._value = value


class _Root:
    def after(self, ms, func=None):
        return "id"

    def after_cancel(self, token):
        pass


class _Host(PlayerMixin):
    def __init__(self):
        self.root = _Root()
        self.player_frame = _Silent()
        self.player_status_label = _Silent()
        self.play_pause_btn = _Silent()
        self.now_playing_var = _Var()
        self.player_time_var = _Var()
        self.seek_var = _Var(0)
        self.volume_var = _Var(80)
        self.cookies_file_var = _Var("")
        self.mpv_process = None
        self.mpv_socket_path = ""
        self._mpv_socket_dir = None
        self.player_update_id = None
        self.player_paused = False
        self._user_seeking = False

    @staticmethod
    def _is_valid_url(url):
        return True


class _FakePopen:
    """Records the argv instead of starting mpv."""

    last_cmd = None

    def __init__(self, cmd, **kwargs):
        _FakePopen.last_cmd = cmd

    def poll(self):
        return None

    def terminate(self):
        pass

    def wait(self, timeout=None):
        return 0


@pytest.fixture
def host(monkeypatch):
    monkeypatch.setattr(player.subprocess, "Popen", _FakePopen)
    monkeypatch.setattr(player, "find_mpv", lambda: "/usr/bin/mpv")
    monkeypatch.setattr(player, "find_ytdlp", lambda: None)
    monkeypatch.setattr(player, "is_windows", lambda: False)
    h = _Host()
    yield h
    h._stop_player()


def test_the_socket_lives_in_a_private_directory(host):
    host._play_in_mpv("https://example.com/v.mp4")

    mode = stat.S_IMODE(os.stat(host._mpv_socket_dir).st_mode)
    assert mode == 0o700, f"directory is {oct(mode)}, reachable by others"
    assert os.path.dirname(host.mpv_socket_path) == host._mpv_socket_dir


def test_the_directory_name_is_not_predictable(host):
    host._play_in_mpv("https://example.com/v.mp4")
    first = host._mpv_socket_dir
    host._stop_player()
    host._play_in_mpv("https://example.com/v.mp4")

    # The old name was snatch-mpv-<pid>, identical for the life of the
    # process, so a squatter needed only the pid.
    assert host._mpv_socket_dir != first
    assert str(os.getpid()) not in os.path.basename(host._mpv_socket_dir)


def test_the_fallback_branch_is_private_too(host, monkeypatch, tmp_path):
    """The case CLAUDE.md's rule covered and the code did not.

    With XDG_RUNTIME_DIR unset the old path went straight into a shared
    /tmp, on a branch the ownership check never reached.
    """
    monkeypatch.delenv("XDG_RUNTIME_DIR", raising=False)
    monkeypatch.setattr(player.tempfile, "gettempdir", lambda: str(tmp_path))

    host._play_in_mpv("https://example.com/v.mp4")

    assert host._mpv_socket_dir.startswith(str(tmp_path))
    assert stat.S_IMODE(os.stat(host._mpv_socket_dir).st_mode) == 0o700


def test_stopping_removes_the_directory(host):
    host._play_in_mpv("https://example.com/v.mp4")
    directory = host._mpv_socket_dir

    host._stop_player()

    assert not os.path.exists(directory)
    assert host.mpv_socket_path == ""
    assert host._mpv_socket_dir is None


def test_stopping_survives_a_directory_that_cannot_be_removed(host):
    """The old unguarded os.unlink raised PermissionError out of the caller."""
    host._play_in_mpv("https://example.com/v.mp4")
    host._mpv_socket_dir = "/proc/1/definitely-not-removable"

    host._stop_player()  # must not raise

    assert host._mpv_socket_dir is None


def test_the_cookie_path_is_passed_as_a_single_pair(host, tmp_path):
    """--ytdl-raw-options is a comma-separated LIST.

    A comma anywhere in the path splits it into nonsense and the cookies are
    dropped with no error. The -append form takes one pair.
    """
    cookies = tmp_path / "my,cookies.txt"
    cookies.write_text("# netscape", encoding="utf-8")
    host.cookies_file_var.set(str(cookies))

    host._play_in_mpv("https://example.com/v.mp4")

    passed = [a for a in _FakePopen.last_cmd if "cookies=" in a]
    assert passed == [f"--ytdl-raw-options-append=cookies={cookies}"]
