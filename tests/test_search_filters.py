"""Search targets for the Uploaded filter (SNAT-0072).

The sp= codes were verified against YouTube on 2026-09-25; these pin the
encoding that produced them, and the refusal for a channel search, which
has no sp= to carry the filter.
"""

import pytest

from snatch.tabs.search import (SearchTabMixin, _format_upload_date,
                                build_search_target, search_filter_code)


def test_codes_match_the_verified_ones():
    assert search_filter_code(1, False) == "EgIIAQ=="
    assert search_filter_code(2, False) == "EgIIAg=="
    assert search_filter_code(3, False) == "EgIIAw=="
    assert search_filter_code(4, False) == "EgIIBA=="
    assert search_filter_code(5, False) == "EgIIBQ=="
    assert search_filter_code(3, True) == "CAISAggD"
    assert search_filter_code(None, True) is None


def test_no_filter_keeps_the_ytsearch_prefixes():
    assert build_search_target("cats", "", 20, "Relevance", "Any") == "ytsearch20:cats"
    assert build_search_target("cats", "", 10, "Upload Date", "Any") == "ytsearchdate10:cats"


def test_a_filter_uses_the_results_url():
    target = build_search_target("big buck bunny", "", 20, "Relevance", "This week")
    assert target == ("https://www.youtube.com/results?search_query=big%20buck%20bunny"
                      "&sp=EgIIAw%3D%3D")


def test_a_channel_search_is_unchanged():
    assert build_search_target("open movie", "BlenderStudio", 20, "Relevance", "Any") == (
        "https://www.youtube.com/@BlenderStudio/search?query=open%20movie")
    assert build_search_target("", "@BlenderStudio", 20, "Relevance", "Any") == (
        "https://www.youtube.com/@BlenderStudio/videos")


def test_a_filter_inside_a_channel_is_refused():
    with pytest.raises(ValueError):
        build_search_target("x", "@BlenderStudio", 20, "Relevance", "Today")


class _Tree:
    def __init__(self):
        self.cells = {}

    def exists(self, iid):
        return True

    def set(self, iid, column, value):
        self.cells[(iid, column)] = value


class _Host(SearchTabMixin):
    def __init__(self, entries):
        self.search_results = entries
        self.search_tree = _Tree()
        self._search_generation = 1


def test_upload_dates_are_formatted():
    assert _format_upload_date("20260922") == "2026-09-22"
    assert _format_upload_date("NA") == ""
    assert _format_upload_date(None) == ""


def test_a_date_for_the_current_search_is_shown():
    entry = {"url": "https://www.youtube.com/watch?v=x", "_date_pending": True}
    host = _Host([entry])

    host._show_upload_date(1, 0, entry, "20260922")

    assert host.search_tree.cells[("1", "uploaded")] == "2026-09-22"
    assert "_date_pending" not in entry


def test_a_date_that_arrives_after_a_new_search_is_dropped():
    old = {"url": "https://www.youtube.com/watch?v=x", "_date_pending": True}
    host = _Host([{"url": "https://www.youtube.com/watch?v=y"}])
    host._search_generation = 2  # a newer search replaced the rows

    host._show_upload_date(1, 0, old, "20260922")

    assert host.search_tree.cells == {}
