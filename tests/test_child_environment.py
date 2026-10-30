"""A frozen build must not hand its own libraries to the programs it starts.

PyInstaller's bootloader points LD_LIBRARY_PATH at the bundle and saves the
old value as LD_LIBRARY_PATH_ORIG. The bundled yt-dlp is run by the system's
python3, which then loads the bundle's older libcrypto and dies (SNAT-0087).
"""

import os

from snatch import platform_utils


def _frozen(monkeypatch, frozen=True):
    monkeypatch.setattr(platform_utils, "is_frozen", lambda: frozen)
    monkeypatch.setattr(platform_utils, "is_windows", lambda: False)


def test_the_original_path_comes_back(monkeypatch):
    _frozen(monkeypatch)
    monkeypatch.setenv("LD_LIBRARY_PATH", "/bundle/_internal")
    monkeypatch.setenv("LD_LIBRARY_PATH_ORIG", "/users/own/lib")
    platform_utils.restore_child_library_path()
    assert os.environ["LD_LIBRARY_PATH"] == "/users/own/lib"


def test_no_original_path_means_none_at_all(monkeypatch):
    _frozen(monkeypatch)
    monkeypatch.setenv("LD_LIBRARY_PATH", "/bundle/_internal")
    monkeypatch.delenv("LD_LIBRARY_PATH_ORIG", raising=False)
    platform_utils.restore_child_library_path()
    assert "LD_LIBRARY_PATH" not in os.environ


def test_running_from_source_is_left_alone(monkeypatch):
    _frozen(monkeypatch, frozen=False)
    monkeypatch.setenv("LD_LIBRARY_PATH", "/developers/own/lib")
    monkeypatch.setenv("LD_LIBRARY_PATH_ORIG", "/something/else")
    platform_utils.restore_child_library_path()
    assert os.environ["LD_LIBRARY_PATH"] == "/developers/own/lib"
