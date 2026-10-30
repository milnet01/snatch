"""DownloaderMixin._rate_args — the speed limit and parallel parts (SNAT-0040).

yt-dlp applies --limit-rate to each fragment's connection separately, so
parallel parts under a limit would download at a multiple of it. These pin
that a set limit wins, and that the default changes nothing.
"""

from snatch.downloader import DownloaderMixin

rate_args = DownloaderMixin._rate_args


def test_defaults_add_nothing():
    assert rate_args("Unlimited", "1") == []


def test_parallel_parts_without_a_limit():
    assert rate_args("Unlimited", "4") == ["--concurrent-fragments", "4"]


def test_a_speed_limit_wins_over_parallel_parts():
    assert rate_args("2M", "4") == ["--limit-rate", "2M"]


def test_a_value_not_offered_is_ignored():
    # config.json is user-editable, so anything can come back from it.
    assert rate_args("Unlimited", "999") == []
    assert rate_args("Unlimited", 4) == []
    assert rate_args("", "") == []
