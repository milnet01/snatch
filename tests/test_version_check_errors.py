"""A failed version check must say which failure it was.

SNAT-0053, the "catch what you can name" half. Two handlers in version.py
collapsed every cause into one message:

  - the yt-dlp probe reported "yt-dlp not found" for a TimeoutExpired, a
    PermissionError and a corrupt binary alike, sending the user to look for
    a file that was right there;
  - the GitHub check reported "Check failed" for everything, including the
    403 rate limit, which is not a fault and clears on its own. That exact
    403 was in this project's own log on 2026-09-02.

~/.claude/standards/languages/python.md is explicit: catch what you can name.
"""

import subprocess
import urllib.error

import pytest

from snatch import version as version_module
from snatch.version import VersionMixin


class _Var:
    def __init__(self):
        self.value = None

    def set(self, value):
        self.value = value


class _Button:
    def __init__(self):
        self.text = None
        self.state = None

    def config(self, text=None, state=None):
        self.text = text
        self.state = state


class _Root:
    """Runs after() callbacks immediately, so the label is readable inline."""

    def after(self, ms, func=None):
        if func is not None:
            func()
        return "id"


class _Host(VersionMixin):
    def __init__(self):
        self.root = _Root()
        self.version_var = _Var()
        self.update_btn = _Button()
        self.current_version = None
        self.latest_version = None


@pytest.fixture
def host():
    return _Host()


# ── The local yt-dlp probe ───────────────────────────────────────────

@pytest.mark.parametrize("raised, expected", [
    (FileNotFoundError("no such file"), "yt-dlp not found"),
    (subprocess.TimeoutExpired("yt-dlp", 10), "Version check timed out"),
    (PermissionError("denied"), "yt-dlp will not run"),
    (OSError("Exec format error"), "yt-dlp will not run"),
])
def test_the_probe_names_the_failure(host, monkeypatch, raised, expected):
    def boom(*args, **kwargs):
        raise raised

    monkeypatch.setattr(version_module.subprocess, "run", boom)
    monkeypatch.setattr(version_module, "find_ytdlp", lambda: "/nowhere/yt-dlp")

    host._check_version_thread()

    assert host.version_var.value == expected


def test_a_wrong_architecture_binary_is_not_reported_as_missing(host, monkeypatch):
    """The case that cost a real search: the file is present, it will not run.

    PermissionError and "Exec format error" both arrive as OSError, and both
    used to render as "yt-dlp not found".
    """
    def boom(*args, **kwargs):
        raise OSError(8, "Exec format error")

    monkeypatch.setattr(version_module.subprocess, "run", boom)
    monkeypatch.setattr(version_module, "find_ytdlp", lambda: "/usr/bin/yt-dlp")

    host._check_version_thread()

    assert host.version_var.value != "yt-dlp not found"
    assert "not run" in host.version_var.value


# ── The GitHub release check ─────────────────────────────────────────

def _probe_ok(monkeypatch):
    """Get past the local probe so the network half is what is under test."""
    class Result:
        returncode = 0
        stdout = "2026.08.01"

    monkeypatch.setattr(version_module.subprocess, "run",
                        lambda *a, **k: Result())
    monkeypatch.setattr(version_module, "find_ytdlp", lambda: "/usr/bin/yt-dlp")


@pytest.mark.parametrize("code, expected", [
    (403, "Rate limited"),
    (429, "Rate limited"),
    (500, "Check failed"),
    (404, "Check failed"),
])
def test_an_http_error_distinguishes_the_rate_limit(host, monkeypatch,
                                                    code, expected):
    _probe_ok(monkeypatch)

    def boom(*args, **kwargs):
        raise urllib.error.HTTPError("u", code, "msg", {}, None)

    monkeypatch.setattr(version_module.urllib.request, "urlopen", boom)

    host._check_version_thread()

    assert host.update_btn.text == expected


def test_no_network_says_so(host, monkeypatch):
    _probe_ok(monkeypatch)

    def boom(*args, **kwargs):
        raise urllib.error.URLError("name resolution failed")

    monkeypatch.setattr(version_module.urllib.request, "urlopen", boom)

    host._check_version_thread()

    assert host.update_btn.text == "No connection"


def test_an_unreadable_response_is_not_reported_as_offline(host, monkeypatch):
    """json.JSONDecodeError is a ValueError; something answered, just not JSON."""
    _probe_ok(monkeypatch)

    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self):
            return b"<html>not json</html>"

    monkeypatch.setattr(version_module.urllib.request, "urlopen",
                        lambda *a, **k: _Response())

    host._check_version_thread()

    assert host.update_btn.text == "Check failed"
