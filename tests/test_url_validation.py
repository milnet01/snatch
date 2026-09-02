"""DownloaderMixin._is_valid_url — the gate in front of every subprocess call.

STANDARDS.md 5.1 makes this the check that decides what reaches yt-dlp. A
scheme that slips through here is passed to a subprocess, so the rejections
matter more than the acceptances.
"""

from snatch.downloader import DownloaderMixin

valid = DownloaderMixin._is_valid_url


def test_accepts_http_and_https():
    assert valid("https://www.youtube.com/watch?v=abc")
    assert valid("http://example.com/video.mp4")


def test_accepts_the_yt_dlp_search_prefix():
    # ytsearch: is not a URL but is a legitimate yt-dlp target.
    assert valid("ytsearch:cats")
    assert valid("ytsearch5:cats")


def test_rejects_schemes_that_are_not_http():
    for bad in ("ftp://example.com/x", "file:///etc/passwd",
                "javascript:alert(1)", "data:text/html,<script>"):
        assert not valid(bad), bad


def test_rejects_empty_and_none():
    # re.match raises TypeError on None, so the falsy guard is what keeps this
    # a rejection rather than an exception escaping into the download thread.
    assert not valid("")
    assert not valid(None)


def test_rejects_a_bare_hostname_with_no_scheme():
    assert not valid("example.com/video")


def test_does_not_accept_a_scheme_merely_containing_http():
    # startswith is the real check; anything that only mentions http must fail.
    assert not valid("nothttp://example.com")
    assert not valid("x-http://example.com")
