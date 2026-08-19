#!/usr/bin/env python3
"""Prints what platform_utils resolves on the current platform.

Run on Linux before pushing: confirms the dev-mode path resolution still
matches the pre-existing behaviour (same project root, same yt-dlp on PATH).
Run inside the GitHub Actions Windows build (post-PyInstaller, against the
.exe via `--add-data`): confirms bundled binaries are found.
"""

import os
import sys

# Allow running from project root without installing the package.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from snatch import platform_utils as pu


def main():
    print("platform        :", sys.platform)
    print("is_windows      :", pu.is_windows())
    print("is_macos        :", pu.is_macos())
    print("is_frozen       :", pu.is_frozen())
    print("app_data_dir    :", pu.app_data_dir())
    print("resource_path() :", pu.resource_path("icon.png"))
    print("find_ytdlp      :", pu.find_ytdlp())
    print("find_ffmpeg     :", pu.find_ffmpeg())
    print()

    # Sanity asserts — fail loud if something looks wrong.
    assert os.path.isdir(pu.app_data_dir()), "app_data_dir must exist"
    if pu.is_frozen():
        assert pu.find_ytdlp() != "yt-dlp", \
            "frozen build must resolve yt-dlp to a real path (bundled or PATH)"
    print("OK")


if __name__ == "__main__":
    main()
