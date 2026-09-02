"""HistoryTabMixin._safe_resolve_path — CLAUDE.md's resolve-symlinks rule.

History entries are paths the app later opens. A symlink resolved at open
time is a different file from the one recorded, so STANDARDS.md 5.5 requires
realpath before use.
"""

import os

from snatch.tabs.history import HistoryTabMixin

resolve = HistoryTabMixin._safe_resolve_path


def test_returns_none_for_empty_input():
    assert resolve("") is None
    assert resolve(None) is None


def test_rejects_a_path_containing_a_null_byte():
    assert resolve("/tmp/evil\x00.mp4") is None


def test_resolves_a_symlink_to_its_target(tmp_path):
    target = tmp_path / "real.mp4"
    target.write_text("x")
    link = tmp_path / "link.mp4"
    link.symlink_to(target)
    assert resolve(str(link)) == os.path.realpath(str(target))


def test_normalises_dot_dot_traversal(tmp_path):
    d = tmp_path / "a" / "b"
    d.mkdir(parents=True)
    messy = str(d / ".." / ".." / "c.mp4")
    assert resolve(messy) == os.path.realpath(str(tmp_path / "c.mp4"))
    assert ".." not in resolve(messy)


def test_returns_an_absolute_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert os.path.isabs(resolve("relative.mp4"))
