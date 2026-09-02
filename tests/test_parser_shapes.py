"""Parsers must survive the JSON yt-dlp actually emits, not the ideal shape.

SNAT-0050. `-J --flat-playlist` puts a JSON null under "entries" when a
playlist has no listable children, so a `.get("entries", [])` default never
fires and iterating raises TypeError. Individual elements are null for
deleted, private and region-blocked videos, and entry.get() then raises
AttributeError. In the search tab that lands in _display_search_results,
which runs on the main thread with no try -- an unhandled Tk traceback with
the results tree half-populated.

The guard is expressed as a comprehension over `... or []` filtered on dict,
so both shapes collapse to "skip it". These lock that comprehension rather
than the crash, because the crash cannot be asserted once the fix is in.

Also here: the two reads that had no size bound. The thumbnail URL comes out
of remote JSON and the ffprobe output grows with the stream count, so in
both cases the size is decided somewhere other than this codebase.
"""

import inspect

from snatch.downloader import DownloaderMixin
from snatch.tabs.media_info import MediaInfoTabMixin
from snatch.tabs.search import SearchTabMixin


def _guard(entries_value):
    """The shape every one of these parse sites now uses."""
    return [e for e in (entries_value or []) if isinstance(e, dict)]


def test_a_null_entries_list_becomes_empty():
    # `.get("entries", [])` returns None here -- the default never fires,
    # because the key is present and its value is null.
    assert _guard(None) == []


def test_null_elements_are_skipped_and_the_rest_kept():
    good = {"title": "kept", "url": "abc"}
    assert _guard([None, good, None]) == [good]


def test_non_dict_elements_are_skipped():
    assert _guard(["a string", 5, {"title": "kept"}, []]) == [{"title": "kept"}]


def test_a_normal_list_is_unchanged():
    entries = [{"title": "a"}, {"title": "b"}]
    assert _guard(entries) == entries


# ── The guard is present at each site ────────────────────────────────
#
# Asserted against the source because the alternative is a live yt-dlp run
# against a playlist whose children happen to be deleted today. The shape
# these check for is the one exercised above.

def test_the_search_parser_guards_its_entries():
    source = inspect.getsource(SearchTabMixin._search_thread)
    assert 'data.get("entries") or []' in source
    assert "isinstance(e, dict)" in source


def test_the_playlist_parser_guards_its_entries():
    source = inspect.getsource(DownloaderMixin._fetch_formats_thread)
    assert 'data.get("entries") or []' in source


def test_the_format_parser_guards_its_list():
    source = inspect.getsource(DownloaderMixin._fetch_formats_thread)
    assert 'data.get("formats") or []' in source


# ── Reads whose size is decided elsewhere ────────────────────────────

def test_the_thumbnail_read_is_capped():
    source = inspect.getsource(DownloaderMixin._fetch_formats_thread)
    # Reading exactly the cap cannot distinguish "fits" from "was truncated",
    # so the read asks for one byte more and rejects on the overflow.
    assert "resp.read(self.MAX_THUMBNAIL_BYTES + 1)" in source
    assert "len(img_data) > self.MAX_THUMBNAIL_BYTES" in source
    assert DownloaderMixin.MAX_THUMBNAIL_BYTES > 0


class _TextHost(MediaInfoTabMixin):
    def __init__(self):
        self.media_info_text = _FakeText()


class _FakeText:
    def __init__(self):
        self.content = ""

    def config(self, **kwargs):
        pass

    def delete(self, start, end):
        self.content = ""

    def insert(self, index, text):
        self.content = text


def test_oversized_ffprobe_output_is_truncated_before_the_widget():
    host = _TextHost()
    cap = MediaInfoTabMixin.MAX_MEDIA_INFO_CHARS

    host._set_media_info_text("x" * (cap * 2))

    assert len(host.media_info_text.content) < cap * 2
    assert "truncated" in host.media_info_text.content


def test_ordinary_output_is_passed_through_unchanged():
    host = _TextHost()
    host._set_media_info_text("Duration: 00:03:12\nStreams: 2")
    assert host.media_info_text.content == "Duration: 00:03:12\nStreams: 2"
