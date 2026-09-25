"""The packaged-build self-test reports what it checked (SNAT-0024).

It runs in CI against each built artefact, so it must fail loudly on the
breakages packaging causes and never on a source checkout that simply has no
bundled binaries.
"""

import pathlib

from snatch import platform_utils, selftest

PACKAGE = pathlib.Path(selftest.__file__).resolve().parent


def test_every_module_is_checked():
    on_disk = {
        "snatch." + ".".join(p.relative_to(PACKAGE).with_suffix("").parts)
        for p in PACKAGE.rglob("*.py")
        if p.name not in ("__init__.py", "__main__.py")
    }
    assert set(selftest.MODULES) == on_disk


def test_a_source_run_passes(tmp_path):
    report = tmp_path / "report.txt"

    assert selftest.run(str(report)) == 0
    text = report.read_text(encoding="utf-8")
    assert "PASS  private settings write" in text
    assert "FAIL" not in text


def test_a_broken_private_write_fails_and_is_named(tmp_path, monkeypatch):
    def broken(path, data):
        raise AttributeError("module 'os' has no attribute 'fchmod'")
    monkeypatch.setattr(selftest, "write_private_json", broken)
    report = tmp_path / "report.txt"

    assert selftest.run(str(report)) == 1
    assert "FAIL  private settings write: AttributeError" in report.read_text(
        encoding="utf-8")


def test_a_frozen_build_missing_a_binary_fails(tmp_path, monkeypatch):
    monkeypatch.setattr(platform_utils, "is_frozen", lambda: True)
    monkeypatch.setattr(platform_utils, "_find_bundled_binary", lambda name: None)
    report = tmp_path / "report.txt"

    assert selftest.run(str(report)) == 1
    assert "FAIL  bundled yt-dlp: RuntimeError: yt-dlp is not in the bundle" in (
        report.read_text(encoding="utf-8"))
