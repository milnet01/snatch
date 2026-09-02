"""VersionMixin._version_compare — the ordering the update button depends on.

If this is wrong in the > direction Snatch offers an update that is older than
what the user has; wrong in the < direction it stays silent on a real one.
Both were live bugs in this file's history (SNAT-0016), which is why the
comparison is tested rather than assumed.
"""

from snatch.version import VersionMixin

cmp = VersionMixin._version_compare


def test_orders_yt_dlp_nightly_datestamps():
    # The real shape: nightly tags are YYYY.MM.DD.HHMMSS.
    assert cmp("2026.08.30.232658", "2026.07.04") > 0
    assert cmp("2026.07.04", "2026.08.30.232658") < 0


def test_equal_versions_compare_equal():
    assert cmp("2026.7.4", "2026.7.4") == 0


def test_numeric_not_lexicographic():
    # "10" sorts before "9" as text and after it as a number. A lexicographic
    # comparison here would tell a user on .10 to downgrade to .9.
    assert cmp("2026.1.10", "2026.1.9") > 0


def test_missing_trailing_components_count_as_zero():
    assert cmp("2026.7", "2026.7.0") == 0
    assert cmp("2026.7.1", "2026.7") > 0


def test_leading_zeros_do_not_change_the_value():
    assert cmp("2026.08.04", "2026.8.4") == 0


def test_non_numeric_suffix_is_stripped_not_fatal():
    # Stable releases have carried suffixes; the function strips non-digits
    # rather than raising, and the caller relies on always getting an answer.
    assert cmp("2026.7.4.1", "2026.7.4") > 0
