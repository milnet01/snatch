#!/usr/bin/env python3
"""Checks the user-data permission tightening pass (SNAT-0006).

Runs against a scratch directory, never the project root -- the real files
are already 0o600 here, so asserting against them would pass without the
code under test. Each case creates the loose state the bug produced.
"""

import os
import stat
import sys
import tempfile

# Allow running from project root without installing the package.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from snatch.platform_utils import is_windows
from snatch.utils import (
    PRIVATE_DATA_FILES,
    PRIVATE_MODE,
    atomic_private_write,
    tighten_user_data_permissions,
)


def mode_of(path):
    return stat.S_IMODE(os.lstat(path).st_mode)


def main():
    if is_windows():
        print("Windows: POSIX mode bits are not the access mechanism — skipped.")
        return

    with tempfile.TemporaryDirectory() as data_dir:
        # A file that predates the 0o600 write path and is never saved again.
        # This is the exact shape measured on 2026-08-19.
        for name, loose in zip(PRIVATE_DATA_FILES, (0o664, 0o644, 0o664)):
            path = os.path.join(data_dir, name)
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("{}")
            os.chmod(path, loose)
            assert mode_of(path) == loose, f"setup failed for {name}"

        fixed = tighten_user_data_permissions(data_dir)
        assert sorted(fixed) == sorted(PRIVATE_DATA_FILES), \
            f"expected all three tightened, got {fixed}"
        for name in PRIVATE_DATA_FILES:
            got = mode_of(os.path.join(data_dir, name))
            assert got == PRIVATE_MODE, f"{name} is {oct(got)}, want 0o600"

        # Idempotent: a second pass reports nothing to fix.
        assert tighten_user_data_permissions(data_dir) == [], \
            "second pass should find nothing — the mode check is not converging"

        # A missing file is not an error.
        os.unlink(os.path.join(data_dir, "cookies.txt"))
        assert tighten_user_data_permissions(data_dir) == [], \
            "a missing file must be skipped, not reported"

        # A symlink is skipped, not followed — chmod follows links, so
        # following one would re-mode a file outside the data directory.
        outside = os.path.join(data_dir, "outside.txt")
        with open(outside, "w", encoding="utf-8") as handle:
            handle.write("x")
        os.chmod(outside, 0o664)
        os.symlink(outside, os.path.join(data_dir, "cookies.txt"))
        assert tighten_user_data_permissions(data_dir) == [], \
            "a symlink must be skipped"
        assert mode_of(outside) == 0o664, \
            "chmod followed a symlink and re-moded a file outside the data dir"

        # The write path still installs 0o600 over a loose existing file.
        os.unlink(os.path.join(data_dir, "cookies.txt"))
        target = os.path.join(data_dir, "config.json")
        os.chmod(target, 0o664)
        with atomic_private_write(target) as handle:
            handle.write("{}")
        assert mode_of(target) == PRIVATE_MODE, \
            f"atomic_private_write left {oct(mode_of(target))}, want 0o600"

    print("OK")


if __name__ == "__main__":
    main()
