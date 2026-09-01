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
    #
    # These run UNCONDITIONALLY. They used to sit behind `if pu.is_frozen():`,
    # and sys.frozen is set only inside a PyInstaller bundle — while all four
    # call sites (build-linux.sh:20, build-windows.sh:20, build-macos.sh:22,
    # local-ci.sh:68) run this as a plain script, every one of them BEFORE
    # PyInstaller. So the branch never executed on any platform and the file
    # asserted nothing at all. Each build script fetches the bundled binaries
    # at step 1, so by the time this runs they are on disk in both modes.
    assert os.path.isdir(pu.app_data_dir()), \
        f"app_data_dir must exist: {pu.app_data_dir()}"

    ytdlp = pu.find_ytdlp()
    assert ytdlp != "yt-dlp", \
        "find_ytdlp fell through to the bare literal — no bundled copy, none " \
        "in user_bin_dir, and none on PATH"
    assert os.path.isfile(ytdlp), f"find_ytdlp returned a non-file: {ytdlp}"

    # The one above passes when yt-dlp is merely on PATH, which is a legitimate
    # runtime answer and NOT what a build needs: PyInstaller is about to bundle
    # the copy in bin/. Measured while writing this — hiding bin/yt-dlp on a
    # machine with /usr/local/bin/yt-dlp left the assert green, so it would have
    # caught nothing here and only worked by accident on a bare runner.
    assert pu._find_bundled_binary("yt-dlp") is not None, \
        "no bundled yt-dlp — run scripts/fetch-binaries.sh before building"
    assert pu._find_bundled_binary("ffmpeg") is not None, \
        "no bundled ffmpeg — run scripts/fetch-binaries.sh before building"

    ffmpeg = pu.find_ffmpeg()
    assert ffmpeg is not None, "find_ffmpeg found neither a bundled copy nor one on PATH"
    assert os.path.isfile(ffmpeg), f"find_ffmpeg returned a non-file: {ffmpeg}"

    icon = pu.resource_path("icon.png")
    assert os.path.isfile(icon), f"resource_path could not locate icon.png: {icon}"

    assert os.path.isdir(pu.user_bin_dir()), \
        f"user_bin_dir must exist and be a directory: {pu.user_bin_dir()}"

    print("OK")


if __name__ == "__main__":
    main()
