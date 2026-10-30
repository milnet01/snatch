"""The newer-version notice (SNAT-0021): no nagging, and silent when offline.

It compares against Snatch's own version, which has nothing to do with
yt-dlp's, and the tag comes from the network so its shape is checked.
"""

import io
import json
from unittest.mock import MagicMock

import pytest

from snatch import version
from snatch.version import VersionMixin, newer_app_version


@pytest.mark.parametrize("tag,current,expected", [
    ("v1.4.0", "1.3.1", "1.4.0"),
    ("v1.10.0", "1.9.0", "1.10.0"),
    ("v1.3.1", "1.3.1", None),
    ("v1.3.0", "1.3.1", None),
    ("1.4.0", "1.3.1", None),
    ("v1.4.0-rc.1", "1.3.1", None),
    ("v1.4.0/../../evil", "1.3.1", None),
    ("2026.10.29.232701", "1.3.1", None),
    (None, "1.3.1", None),
    (7, "1.3.1", None),
])
def test_newer_app_version(tag, current, expected):
    assert newer_app_version(tag, current) == expected


class Host(VersionMixin):
    def __init__(self):
        self.root = MagicMock()
        self.root.after = lambda _ms, fn: fn()
        self.app_update_btn = MagicMock()
        self.available_app_version = None
        self.dismissed_app_version = ""
        self._save_config = MagicMock()


def _serve(monkeypatch, body):
    def fake_open(_url, _timeout):
        return io.BytesIO(body)
    monkeypatch.setattr(version, "_open_https", fake_open)


def test_a_newer_release_shows_the_button(monkeypatch):
    monkeypatch.setattr(version, "__version__", "1.3.1")
    _serve(monkeypatch, json.dumps({"tag_name": "v1.4.0"}).encode())
    host = Host()
    host._check_app_update_thread()
    assert host.available_app_version == "1.4.0"
    host.app_update_btn.pack.assert_called_once()


def test_a_dismissed_version_stays_hidden(monkeypatch):
    monkeypatch.setattr(version, "__version__", "1.3.1")
    _serve(monkeypatch, json.dumps({"tag_name": "v1.4.0"}).encode())
    host = Host()
    host.dismissed_app_version = "1.4.0"
    host._check_app_update_thread()
    host.app_update_btn.pack.assert_not_called()


def test_a_later_version_shows_again_after_a_dismissal(monkeypatch):
    monkeypatch.setattr(version, "__version__", "1.3.1")
    _serve(monkeypatch, json.dumps({"tag_name": "v1.5.0"}).encode())
    host = Host()
    host.dismissed_app_version = "1.4.0"
    host._check_app_update_thread()
    host.app_update_btn.pack.assert_called_once()


@pytest.mark.parametrize("body", [b"not json", b"[]", b"{}"])
def test_a_bad_answer_is_silent(monkeypatch, body):
    monkeypatch.setattr(version, "messagebox", MagicMock())
    _serve(monkeypatch, body)
    host = Host()
    host._check_app_update_thread()
    host.app_update_btn.pack.assert_not_called()
    version.messagebox.showerror.assert_not_called()


def test_being_offline_is_silent(monkeypatch):
    monkeypatch.setattr(version, "messagebox", MagicMock())

    def offline(_url, _timeout):
        raise OSError("no route to host")
    monkeypatch.setattr(version, "_open_https", offline)
    host = Host()
    host._check_app_update_thread()
    host.app_update_btn.pack.assert_not_called()
    version.messagebox.showerror.assert_not_called()


def test_no_remembers_the_version_and_hides(monkeypatch):
    monkeypatch.setattr(version, "messagebox", MagicMock())
    version.messagebox.askyesno.return_value = False
    opened = MagicMock()
    monkeypatch.setattr(version, "open_path", opened)
    host = Host()
    host.available_app_version = "1.4.0"
    host._on_app_update_click()
    assert host.dismissed_app_version == "1.4.0"
    host.app_update_btn.pack_forget.assert_called_once()
    host._save_config.assert_called_once()
    opened.assert_not_called()


def test_yes_opens_the_release_page(monkeypatch):
    monkeypatch.setattr(version, "messagebox", MagicMock())
    version.messagebox.askyesno.return_value = True
    opened = MagicMock()
    monkeypatch.setattr(version, "open_path", opened)
    host = Host()
    host.available_app_version = "1.4.0"
    host._on_app_update_click()
    assert opened.call_args[0][0].startswith("https://github.com/milnet01/snatch/")
    assert host.dismissed_app_version == ""
