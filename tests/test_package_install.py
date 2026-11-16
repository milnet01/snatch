"""A distro package install (SNAT-0028, docs/specs/SNAT-0028-obs-package.md).

A package puts Snatch's source in a read-only folder and marks it with an
empty snatch/INSTALLED_BY_PACKAGE. Each test builds a fake install in a temp
folder and points platform_utils at it, by moving the marker path and the
module's own __file__, which app_data_dir(), resource_path() and
_find_bundled_binary() all resolve the install root from. Nothing here opens
a Tk window: GUI behaviour runs on the mixins with stubbed widgets and
messagebox, as tests/test_app_update_notice.py does.
"""

import os
import subprocess
from unittest.mock import MagicMock

import pytest

from snatch import platform_utils as pu
from snatch import selftest, version
from snatch.app import SnatchApp
from snatch.downloader import DownloaderMixin
from snatch.version import VersionMixin

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GIT_TIMEOUT_SEC = 10


@pytest.fixture(autouse=True)
def _reset_caches(monkeypatch):
    monkeypatch.setattr(pu, "_USER_BIN_DIR", None)
    monkeypatch.setattr(pu, "_PACKAGE_INSTALL", None, raising=False)
    monkeypatch.setattr(pu, "is_frozen", lambda: False)
    yield


def _executable(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/sh\n")
    path.chmod(0o755)
    return str(path)


@pytest.fixture
def install(monkeypatch, tmp_path):
    """A fake install tree, with HOME and XDG_DATA_HOME inside tmp_path.

    Unmarked until a test calls mark(): the same tree serves as a source
    checkout and as a package install.
    """
    root = tmp_path / "install"
    (root / "snatch").mkdir(parents=True)
    marker = root / "snatch" / "INSTALLED_BY_PACKAGE"
    monkeypatch.setattr(pu, "__file__", str(root / "snatch" / "platform_utils.py"))
    monkeypatch.setattr(pu, "_PACKAGE_MARKER", str(marker), raising=False)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
    monkeypatch.setenv("PATH", str(tmp_path / "pathbin"))

    class Install:
        pass

    tree = Install()
    tree.root = root
    tree.tmp = tmp_path
    tree.data = tmp_path / "xdg" / "snatch"
    tree.mark = lambda: marker.touch()
    return tree


@pytest.fixture
def package(install):
    install.mark()
    return install


# ── INV-1 to INV-6: detection and paths ──

def test_marker_decides_package_install(install):
    # The fixture folder is writable either way, so only the marker decides.
    assert pu.is_package_install() is False
    install.mark()
    pu._PACKAGE_INSTALL = None
    assert pu.is_package_install() is True


def test_package_data_goes_to_xdg(package, monkeypatch):
    assert pu.app_data_dir() == str(package.data)
    assert os.path.isdir(package.data)

    monkeypatch.delenv("XDG_DATA_HOME")
    expected = package.tmp / "home" / ".local" / "share" / "snatch"
    assert pu.app_data_dir() == str(expected)
    assert pu.app_data_dir() != str(package.root)


def test_source_run_is_unchanged(install):
    assert pu.app_data_dir() == str(install.root)
    assert pu.user_bin_dir() == str(install.root / "bin" / "updated")


def _git(*args):
    """Run git in the repo; None where git cannot answer.

    The pre-push gate runs the suite in a container over a fresh worktree,
    whose .git points at a repository the container cannot see, so git
    exits 128 there (see tests/test_release_signing.py).
    """
    try:
        return subprocess.run(["git", *args], cwd=REPO, check=False,
                              capture_output=True, text=True,
                              timeout=GIT_TIMEOUT_SEC)
    except OSError:
        return None


def test_marker_is_ignored_and_untracked():
    marker = "snatch/INSTALLED_BY_PACKAGE"
    probe = _git("rev-parse", "--is-inside-work-tree")
    if probe is None or probe.returncode != 0:
        # Stricter for the first half: absent, not merely untracked.
        assert not os.path.exists(os.path.join(REPO, marker))
        with open(os.path.join(REPO, ".gitignore"), encoding="utf-8") as handle:
            assert marker in handle.read().splitlines()
        return
    assert _git("ls-files", "--", marker).stdout == ""
    assert _git("check-ignore", "-q", "--", marker).returncode == 0


def test_package_shares_the_appimage_bin_dir(package):
    assert pu.user_bin_dir() == str(package.data / "bin")


def test_package_ytdlp_order(package):
    # A yt-dlp inside the install folder must never be the floor.
    _executable(package.root / "bin" / "yt-dlp")
    on_path = _executable(package.tmp / "pathbin" / "yt-dlp")
    assert pu.find_ytdlp() == on_path

    fetched = _executable(package.data / "bin" / "yt-dlp")
    assert pu.find_ytdlp() == fetched


# ── INV-7 to INV-11: the yt-dlp offer, Revert, and no self-update ──

class Host(VersionMixin):
    def __init__(self, offer_shown=False):
        self.root = MagicMock()
        self.root.after = lambda _ms, fn: fn()
        self.update_btn = MagicMock()
        self.app_update_btn = MagicMock()
        self.status_var = MagicMock()
        self.version_var = MagicMock()
        self.current_version = "2025.10.22"
        self.latest_version = "2026.11.01.000000"
        self.ytdlp_offer_shown = offer_shown
        self._save_config = MagicMock()
        self.check_version = MagicMock()
        self.update_installer = None


@pytest.fixture
def dialogs(monkeypatch):
    box = MagicMock()
    box.askyesno.return_value = False
    monkeypatch.setattr(version, "messagebox", box)
    return box


def test_package_does_not_check_for_snatch_updates(package, monkeypatch):
    thread = MagicMock()
    opener = MagicMock()
    monkeypatch.setattr(version.threading, "Thread", thread)
    monkeypatch.setattr(version, "_open_https", opener)
    Host().check_app_update()
    thread.assert_not_called()
    opener.assert_not_called()


def _saved_config(monkeypatch, host):
    """Run the real SnatchApp._save_config on `host`; return what it wrote."""
    from snatch import app
    written = {}
    monkeypatch.setattr(app, "write_private_json",
                        lambda _path, data: written.update(data))
    stub = MagicMock()
    stub.ytdlp_offer_shown = host.ytdlp_offer_shown
    stub.dismissed_app_version = ""
    SnatchApp._save_config(stub)
    return written


def test_offer_is_shown_once(package, dialogs, monkeypatch):
    first = Host()
    first._show_update_available()
    dialogs.askyesno.assert_called_once()
    assert first.ytdlp_offer_shown is True
    first._save_config.assert_called_once()
    saved = _saved_config(monkeypatch, first)
    assert saved["ytdlp_offer_shown"] is True

    dialogs.reset_mock()
    later = Host(offer_shown=saved["ytdlp_offer_shown"])
    later._show_update_available()
    dialogs.askyesno.assert_not_called()
    later.update_btn.config.assert_called_with(
        text="Update to 2026.11.01.000000", state=version.tk.NORMAL)


def _run_check(host, monkeypatch, opener):
    monkeypatch.setattr(version.subprocess, "run", lambda *a, **k: MagicMock(
        returncode=0, stdout="2025.10.22\n"))
    monkeypatch.setattr(version, "_open_https", opener)
    host._check_version_thread()


def test_failed_check_keeps_the_offer(package, dialogs, monkeypatch):
    import io
    import json
    import urllib.error

    def offline(_url, _timeout):
        raise urllib.error.URLError("no route to host")

    def answers(tag):
        return lambda _url, _timeout: io.BytesIO(
            json.dumps({"tag_name": tag}).encode())

    for opener in (offline, answers("2025.10.22")):
        host = Host()
        _run_check(host, monkeypatch, opener)
        assert host.ytdlp_offer_shown is False
        host._save_config.assert_not_called()
        dialogs.askyesno.assert_not_called()

    # The control: a check that does find something newer uses the offer.
    host = Host()
    _run_check(host, monkeypatch, answers("2026.11.01.000000"))
    assert host.ytdlp_offer_shown is True
    dialogs.askyesno.assert_called_once()


def _texts(host, dialogs):
    """The four places the fallback copy is named."""
    dialogs.askyesno.return_value = True
    host._refresh_idle_button()
    button = host.update_btn.config.call_args.kwargs["text"]
    host._do_update = MagicMock()
    host._prompt_update()
    update = dialogs.askyesno.call_args.args[1]
    host._prompt_revert()
    revert = dialogs.askyesno.call_args.args[1]
    status = host.status_var.set.call_args.args[0]
    return button, update, revert, status


def test_fallback_wording(install, dialogs):
    fetched = install.root / "bin" / "updated" / "yt-dlp"
    _executable(fetched)
    button, update, revert, status = _texts(Host(), dialogs)
    assert button == "Revert to bundled yt-dlp"
    assert "The copy that came with Snatch is kept" in update
    assert "Go back to the copy that came with Snatch?" in revert
    assert status == "Reverted to the copy that came with Snatch"

    install.mark()
    pu._PACKAGE_INSTALL = None
    pu._USER_BIN_DIR = None
    _executable(install.data / "bin" / "yt-dlp")
    button, update, revert, status = _texts(Host(), dialogs)
    assert button == "Revert to system yt-dlp"
    assert "Your system's yt-dlp is kept" in update
    assert "Go back to your system's yt-dlp?" in revert
    assert status == "Reverted to your system's yt-dlp"


def test_revert_returns_to_system_ytdlp(package, dialogs):
    _executable(package.root / "bin" / "yt-dlp")
    on_path = _executable(package.tmp / "pathbin" / "yt-dlp")
    fetched = _executable(package.data / "bin" / "yt-dlp")
    dialogs.askyesno.return_value = True
    Host()._prompt_revert()
    assert not os.path.exists(fetched)
    assert pu.find_ytdlp() == on_path


# ── INV-12, INV-13: the JavaScript runtime and the window icon ──

def test_qjs_on_path_enables_quickjs(install, monkeypatch):
    from snatch import downloader
    _executable(install.tmp / "pathbin" / "qjs")
    monkeypatch.setattr(downloader, "find_jsruntime", lambda: None)
    monkeypatch.setattr(DownloaderMixin, "_cached_runtimes", None)
    DownloaderMixin._ensure_runtime_cache()
    assert DownloaderMixin._cached_runtimes == ["quickjs"]


def test_window_icon_comes_from_the_install(package, monkeypatch):
    from snatch import app
    (package.root / "icon.png").write_bytes(b"png")
    photo = MagicMock()
    monkeypatch.setattr(app.tk, "PhotoImage", photo)
    host = MagicMock()
    host.script_dir = str(package.data)
    SnatchApp._set_icon(host)
    photo.assert_called_once_with(file=str(package.root / "icon.png"))


# ── INV-14's self-test check, and INV-16 ──

def test_selftest_checks_the_package_data_folder(package, tmp_path):
    report = tmp_path / "report.txt"
    selftest.run(str(report))
    assert "PASS  package data folder" in report.read_text(encoding="utf-8")


def test_spec_version_is_a_placeholder():
    spec = os.path.join(REPO, "packaging", "obs", "snatch.spec")
    assert os.path.isfile(spec)
    with open(spec, encoding="utf-8") as handle:
        versions = [line.split(":", 1)[1].strip() for line in handle
                    if line.startswith("Version:")]
    assert versions == ["0"]
