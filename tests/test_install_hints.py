"""Install advice must match the platform the user is actually on.

SNAT-0053. _no_player_message() branched three ways and its docstring recorded
why: "sudo apt install mpv" is wrong on Windows and macOS. That fix was never
carried to the other two messages, so media_info.py told a macOS user with no
ffmpeg to run apt, and so did downloader.py for Node.js -- on a project whose
own primary machine is openSUSE, which does not have apt either.

The advice now comes from one table in platform_utils. These tests assert the
property that broke: no message names a package manager the platform does not
have.
"""

from unittest.mock import patch

import pytest

from snatch import platform_utils as pu
from snatch.platform_utils import install_hint

TOOLS = ("ffmpeg", "mpv", "jsruntime")


def _on(platform):
    """Run install_hint as if we were on `platform`."""
    return patch.multiple(
        pu,
        is_windows=lambda: platform == "windows",
        is_macos=lambda: platform == "macos",
    )


@pytest.mark.parametrize("tool", TOOLS)
@pytest.mark.parametrize("platform", ["windows", "macos", "linux"])
def test_every_tool_has_advice_on_every_platform(tool, platform):
    with _on(platform):
        assert install_hint(tool).strip()


@pytest.mark.parametrize("tool", TOOLS)
def test_no_apt_on_macos(tool):
    """The exact defect: apt does not exist on macOS."""
    with _on("macos"):
        assert "apt" not in install_hint(tool)


@pytest.mark.parametrize("tool", TOOLS)
def test_no_unix_package_manager_on_windows(tool):
    with _on("windows"):
        hint = install_hint(tool)
        for manager in ("apt", "brew", "zypper", "dnf", "pacman", "sudo"):
            assert manager not in hint, f"{manager} named on Windows"


@pytest.mark.parametrize("tool", TOOLS)
def test_linux_advice_is_not_debian_only(tool):
    """This project's own machine is openSUSE; Fedora and Arch users exist too.

    The old copies said "sudo apt install X" flat, which is wrong on every
    non-Debian distribution.
    """
    with _on("linux"):
        hint = install_hint(tool)
        assert "apt" not in hint or "(or apt" in hint, hint


def test_macos_uses_brew_where_a_package_is_the_answer():
    with _on("macos"):
        assert install_hint("ffmpeg") == "brew install ffmpeg"
        assert install_hint("mpv") == "brew install mpv"


def test_an_unknown_tool_raises_rather_than_advising_nothing():
    """A vague fallback would ship a message telling the user to install
    nothing in particular. A KeyError fails a test instead."""
    with pytest.raises(KeyError):
        install_hint("not-a-tool")


def test_the_player_message_carries_the_platform_step():
    from snatch.player import _no_player_message

    with _on("linux"):
        message = _no_player_message()
    assert "zypper install mpv" in message
    # The framing stays at the call site; only the step is shared.
    assert "browser" in message
