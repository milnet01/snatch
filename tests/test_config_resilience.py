"""A damaged config.json must not stop Snatch opening.

SNAT-0051 filed the gap against STANDARDS.md 7.3, which promises "Graceful
fallback: Returns {} on missing/corrupt config". _load_config caught only
FileNotFoundError and json.JSONDecodeError, so a permission problem, a
directory in place of the file, undecodable bytes, or valid JSON of the wrong
shape all escaped -- out of SnatchApp.__init__, before any window exists, so
there was no UI route to repair it and no message saying what was wrong.

The saved geometry is the second half. root.geometry() returns WxH+X+Y, so
the offset is saved too; a malformed value raises TclError from the same
constructor, and an offset saved on a monitor that is no longer attached
reopens the window out of reach.

Both are tested as plain functions against a stub host. Neither needs a Tk
window, and building one would not make the fallback any more true.
"""

import json
import os

import pytest

from snatch.app import SnatchApp


class _Host:
    """Only what _load_config touches."""

    def __init__(self, config_file):
        self.config_file = config_file


load = SnatchApp._load_config


def _write(tmp_path, text, name="config.json"):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return str(path)


def test_missing_file_gives_an_empty_config(tmp_path):
    assert load(_Host(str(tmp_path / "absent.json"))) == {}


def test_a_valid_object_is_returned(tmp_path):
    path = _write(tmp_path, json.dumps({"theme": "Nord", "last_tab": 2}))
    assert load(_Host(path)) == {"theme": "Nord", "last_tab": 2}


def test_unparseable_json_gives_an_empty_config(tmp_path):
    assert load(_Host(_write(tmp_path, "{not json"))) == {}


def test_truncated_json_gives_an_empty_config(tmp_path):
    # The shape a config left half-written by a crash actually takes.
    assert load(_Host(_write(tmp_path, '{"theme": "Nord"'))) == {}


@pytest.mark.parametrize("payload", ["[1, 2, 3]", "5", '"a string"', "null", "true"])
def test_valid_json_of_the_wrong_shape_gives_an_empty_config(tmp_path, payload):
    # These parse. saved_config.get() then raises AttributeError, which was
    # the crash STANDARDS.md 7.3 already promised would not happen.
    assert load(_Host(_write(tmp_path, payload))) == {}


def test_undecodable_bytes_give_an_empty_config(tmp_path):
    path = tmp_path / "config.json"
    path.write_bytes(b'{"theme": "\xff\xfe invalid utf-8"}')
    assert load(_Host(str(path))) == {}


def test_a_directory_in_place_of_the_file_gives_an_empty_config(tmp_path):
    directory = tmp_path / "config.json"
    directory.mkdir()
    assert load(_Host(str(directory))) == {}


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignores file permissions")
def test_an_unreadable_file_gives_an_empty_config(tmp_path):
    path = tmp_path / "config.json"
    path.write_text("{}", encoding="utf-8")
    path.chmod(0o000)
    try:
        assert load(_Host(str(path))) == {}
    finally:
        path.chmod(0o600)


# ── Saved window geometry ────────────────────────────────────────────

class _FakeRoot:
    def __init__(self, width=1920, height=1080):
        self._width = width
        self._height = height

    def winfo_screenwidth(self):
        return self._width

    def winfo_screenheight(self):
        return self._height


class _GeometryHost:
    DEFAULT_GEOMETRY = SnatchApp.DEFAULT_GEOMETRY
    _GEOMETRY_RE = SnatchApp._GEOMETRY_RE

    def __init__(self, **screen):
        self.root = _FakeRoot(**screen)


sanitize = SnatchApp._sanitize_geometry
DEFAULT = SnatchApp.DEFAULT_GEOMETRY


def test_a_plain_size_is_kept():
    assert sanitize(_GeometryHost(), "1200x900") == "1200x900"


def test_an_on_screen_origin_is_kept():
    assert sanitize(_GeometryHost(), "1200x900+100+50") == "1200x900+100+50"


def test_an_origin_past_the_right_edge_is_dropped():
    # The monitor this was saved on is no longer attached.
    assert sanitize(_GeometryHost(width=1920), "1200x900+3000+50") == "1200x900"


def test_an_origin_below_the_bottom_edge_is_dropped():
    assert sanitize(_GeometryHost(height=1080), "1200x900+100+4000") == "1200x900"


def test_an_edge_anchored_origin_is_kept():
    # A negative sign measures from the right or bottom edge, which always
    # exists, so there is nothing to fall off.
    assert sanitize(_GeometryHost(), "1200x900-0-0") == "1200x900-0-0"


@pytest.mark.parametrize("bad", [
    "not-a-geometry",
    "1200x",
    "1200x900+",
    "1200x900+10",
    "1200 x 900",
    "",
    None,
    {"width": 1200},
    1200,
])
def test_anything_tk_would_reject_falls_back_to_the_default(bad):
    # root.geometry() raises TclError on these, from inside __init__.
    assert sanitize(_GeometryHost(), bad) == DEFAULT
