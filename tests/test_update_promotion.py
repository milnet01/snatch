"""The self-update promotion rule and the digest that guards it.

SNAT-0020 calls this "the one place a bad file can replace a working binary".
The order is what matters: the SHA-256 comparison happens BEFORE the file is
made executable, and _probe_version runs the candidate afterwards only to
catch a wrong-architecture or truncated build. _probe_version's own docstring
says it is not what makes the promotion safe.
"""

import os
import stat

import pytest

from snatch.version import VersionMixin

probe = VersionMixin._probe_version


def test_probe_returns_none_for_a_file_that_is_not_executable(tmp_path):
    p = tmp_path / "yt-dlp"
    p.write_text("not a binary")
    assert probe(str(p)) is None


def test_probe_returns_none_for_an_html_error_page_saved_as_a_binary(tmp_path):
    # The shape the docstring names: a 200 response that is not the asset.
    p = tmp_path / "yt-dlp"
    p.write_text("<!DOCTYPE html><html><body>404</body></html>")
    p.chmod(0o700)
    assert probe(str(p)) is None


def test_probe_returns_none_when_the_binary_exits_non_zero(tmp_path):
    # It must PRINT a plausible version and still be rejected. An earlier
    # version of this test exited non-zero printing nothing, so the empty
    # stdout rejected it and the return-code check was never exercised --
    # a mutation removing that check left the test green.
    p = tmp_path / "yt-dlp"
    p.write_text("#!/bin/sh\necho 2026.08.30.232658\nexit 3\n")
    p.chmod(0o700)
    assert probe(str(p)) is None


def test_probe_returns_none_when_the_binary_prints_nothing(tmp_path):
    # Exit 0 with empty stdout is not a version; promoting on the exit code
    # alone would accept a file that reports nothing about itself.
    p = tmp_path / "yt-dlp"
    p.write_text("#!/bin/sh\nexit 0\n")
    p.chmod(0o700)
    assert probe(str(p)) is None


def test_probe_returns_the_reported_version(tmp_path):
    p = tmp_path / "yt-dlp"
    p.write_text("#!/bin/sh\necho 2026.08.30.232658\n")
    p.chmod(0o700)
    assert probe(str(p)) == "2026.08.30.232658"


def test_probe_returns_none_for_a_missing_path(tmp_path):
    assert probe(str(tmp_path / "does-not-exist")) is None


class _Resp:
    def __init__(self, body):
        self._body = body.encode()

    def read(self, n=-1):
        return self._body[:n] if n and n > 0 else self._body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _sums(monkeypatch, body):
    import snatch.version as v
    monkeypatch.setattr(v, "_open_https", lambda url, timeout: _Resp(body))


def test_expected_digest_reads_the_published_manifest(monkeypatch):
    import snatch.version as v
    good = "a" * 64
    _sums(monkeypatch, f"{good}  yt-dlp\n{'b' * 64}  yt-dlp.exe\n")
    assert v._expected_digest("2026.08.30.232658", "yt-dlp") == good


def test_expected_digest_raises_when_the_asset_is_absent(monkeypatch):
    import snatch.version as v
    _sums(monkeypatch, f"{'b' * 64}  yt-dlp.exe\n")
    # No digest means nothing to verify against, and the caller must not
    # fall back to writing the file anyway.
    with pytest.raises(ValueError):
        v._expected_digest("2026.08.30.232658", "yt-dlp")


def test_expected_digest_rejects_a_malformed_digest(monkeypatch):
    import snatch.version as v
    _sums(monkeypatch, "not-a-sha  yt-dlp\n")
    with pytest.raises(ValueError):
        v._expected_digest("2026.08.30.232658", "yt-dlp")


def test_expected_digest_rejects_a_short_hex_digest(monkeypatch):
    import snatch.version as v
    _sums(monkeypatch, f"{'a' * 63}  yt-dlp\n")
    with pytest.raises(ValueError):
        v._expected_digest("2026.08.30.232658", "yt-dlp")
