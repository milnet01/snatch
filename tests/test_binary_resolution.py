"""platform_utils binary resolution.

SNAT-0016 turned on this behaviour and SNAT-0020 asked for it to be tested,
noting that the ad-hoc scripts written to check it at the time were thrown
away. These are those checks, kept.

Every test resets the module-level cache. user_bin_dir() memoises into
_USER_BIN_DIR precisely because find_ytdlp() runs on every subprocess call,
so without the reset the first test would decide the answer for all of them.
"""

import os

import pytest

from snatch import platform_utils as pu


@pytest.fixture(autouse=True)
def _clear_user_bin_cache():
    pu._USER_BIN_DIR = None
    yield
    pu._USER_BIN_DIR = None


def test_user_bin_dir_exists_and_is_writable():
    d = pu.user_bin_dir()
    assert os.path.isdir(d)
    assert os.access(d, os.W_OK)


def test_from_source_it_does_not_collide_with_the_pinned_bin_dir(monkeypatch):
    # From source, app_data_dir() is the repo root and bin/ holds the PINNED
    # copy fetch-binaries.sh writes. A self-update landing there would
    # overwrite the pin and leave nothing to revert to -- so from source the
    # updated copy must live one level deeper.
    monkeypatch.setattr(pu, "is_frozen", lambda: False)
    d = pu.user_bin_dir()
    assert os.path.basename(d) == "updated"
    assert os.path.basename(os.path.dirname(d)) == "bin"


def test_frozen_uses_bin_directly(monkeypatch, tmp_path):
    monkeypatch.setattr(pu, "is_frozen", lambda: True)
    monkeypatch.setattr(pu, "app_data_dir", lambda: str(tmp_path))
    d = pu.user_bin_dir()
    assert d == str(tmp_path / "bin")


def test_windows_falls_back_to_localappdata_when_the_exe_dir_is_read_only(
        monkeypatch, tmp_path):
    # The Program Files case: app_data_dir() puts data beside the .exe to stay
    # portable, which is right on a USB stick and wrong where writing needs
    # admin. Only this directory falls back.
    exe_dir = tmp_path / "programfiles"
    local = tmp_path / "localappdata"
    exe_dir.mkdir()
    local.mkdir()
    monkeypatch.setattr(pu, "is_frozen", lambda: True)
    monkeypatch.setattr(pu, "is_windows", lambda: True)
    monkeypatch.setattr(pu, "app_data_dir", lambda: str(exe_dir))
    monkeypatch.setattr(pu, "_is_writable_dir", lambda p: False)
    monkeypatch.setenv("LOCALAPPDATA", str(local))

    d = pu.user_bin_dir()
    assert d == str(local / "Snatch" / "bin")
    assert os.path.isdir(d)


def test_windows_does_not_fall_back_when_the_exe_dir_is_writable(
        monkeypatch, tmp_path):
    # The refuting case: the fallback must fire on unwritability alone, not on
    # being Windows. A portable install on a USB stick has to stay portable.
    exe_dir = tmp_path / "portable"
    exe_dir.mkdir()
    monkeypatch.setattr(pu, "is_frozen", lambda: True)
    monkeypatch.setattr(pu, "is_windows", lambda: True)
    monkeypatch.setattr(pu, "app_data_dir", lambda: str(exe_dir))
    monkeypatch.setattr(pu, "_is_writable_dir", lambda p: True)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "unused"))

    assert pu.user_bin_dir() == str(exe_dir / "bin")


def test_non_windows_never_falls_back(monkeypatch, tmp_path):
    monkeypatch.setattr(pu, "is_frozen", lambda: True)
    monkeypatch.setattr(pu, "is_windows", lambda: False)
    monkeypatch.setattr(pu, "app_data_dir", lambda: str(tmp_path))
    monkeypatch.setattr(pu, "_is_writable_dir", lambda p: False)
    assert pu.user_bin_dir() == str(tmp_path / "bin")


def test_find_ytdlp_prefers_an_updated_copy_over_the_bundled_one(
        monkeypatch, tmp_path):
    # The whole point of SNAT-0016: a packaged build that has fetched a newer
    # yt-dlp must run that one, not the copy it shipped with.
    updated = tmp_path / "updated-yt-dlp"
    updated.write_text("#!/bin/sh\n")
    updated.chmod(0o755)
    monkeypatch.setattr(pu, "_find_updated_binary", lambda name: str(updated))
    monkeypatch.setattr(pu, "_find_bundled_binary", lambda name: "/bundled/yt-dlp")
    assert pu.find_ytdlp() == str(updated)


def test_find_ytdlp_falls_through_to_bundled_then_path(monkeypatch):
    monkeypatch.setattr(pu, "_find_updated_binary", lambda name: None)
    monkeypatch.setattr(pu, "_find_bundled_binary", lambda name: "/bundled/yt-dlp")
    assert pu.find_ytdlp() == "/bundled/yt-dlp"

    monkeypatch.setattr(pu, "_find_bundled_binary", lambda name: None)
    # With neither, it must still return something the caller can try.
    assert pu.find_ytdlp()
