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


class _Answer:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_https_is_skipped_unless_a_url_is_given(tmp_path, monkeypatch):
    monkeypatch.delenv(selftest.HTTPS_URL_ENV, raising=False)
    report = tmp_path / "report.txt"

    assert selftest.run(str(report)) == 0
    assert "SKIP  HTTPS fetch" in report.read_text(encoding="utf-8")


def test_https_passes_when_the_url_answers(tmp_path, monkeypatch):
    # SNAT-0089: the newer-distro check sets the URL; the fetch goes through
    # the opener the update check uses, so it meets the same certificates.
    monkeypatch.setenv(selftest.HTTPS_URL_ENV, "https://example.invalid/")
    seen = []
    monkeypatch.setattr(selftest, "_open_https",
                        lambda url, timeout: seen.append(url) or _Answer())
    report = tmp_path / "report.txt"

    assert selftest.run(str(report)) == 0
    assert seen == ["https://example.invalid/"]
    assert "PASS  HTTPS fetch: https://example.invalid/ answered 200" in (
        report.read_text(encoding="utf-8"))


def test_https_fails_on_an_unverifiable_certificate(tmp_path, monkeypatch):
    # The SNAT-0088 shape: certificates looked for where this system has none.
    def unverified(url, timeout):
        raise OSError("CERTIFICATE_VERIFY_FAILED")
    monkeypatch.setenv(selftest.HTTPS_URL_ENV, "https://example.invalid/")
    monkeypatch.setattr(selftest, "_open_https", unverified)
    report = tmp_path / "report.txt"

    assert selftest.run(str(report)) == 1
    assert "FAIL  HTTPS fetch: OSError: CERTIFICATE_VERIFY_FAILED" in (
        report.read_text(encoding="utf-8"))
