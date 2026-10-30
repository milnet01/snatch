"""The Donate menu must not drift from .github/FUNDING.yml (SNAT-0015).

The packaged app cannot read that file, since it is not bundled, so the links
live in code and this test holds the two together.
"""

import os
import re

from snatch.app import DONATE_LINKS

FUNDING = os.path.join(os.path.dirname(__file__), "..", ".github", "FUNDING.yml")


def _funding():
    with open(FUNDING, encoding="utf-8") as handle:
        return handle.read()


def test_every_link_is_https():
    assert DONATE_LINKS
    assert all(url.startswith("https://") for _label, url in DONATE_LINKS)


def test_every_funding_source_has_a_link():
    text = _funding()
    urls = [url for _label, url in DONATE_LINKS]
    github = re.search(r"^github:\s*\[(.+?)\]", text, re.M).group(1)
    patreon = re.search(r"^patreon:\s*(\S+)", text, re.M).group(1)
    custom = re.search(r'^custom:\s*\["(.+?)"\]', text, re.M).group(1)
    assert f"https://github.com/sponsors/{github}" in urls
    assert f"https://patreon.com/{patreon}" in urls
    assert custom in urls
    assert len(urls) == 3
