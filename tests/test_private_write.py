"""The private-write helper must work where os.fchmod does not exist.

SNAT-0073. utils.atomic_private_write called os.fchmod(fd, 0o600)
unguarded. os.fchmod reached Windows only in Python 3.13, and the Windows
build runs 3.12 -- measured on the Windows test machine with the official
3.12.10 embeddable build: the attribute is absent and the call raises
AttributeError. config.json, history.json and cookies.txt all go through the
helper, and the config and history callers catch OSError only, so on Windows
nothing was ever saved.

Windows is simulated here by removing os.fchmod, which is exactly the
difference that broke it. The POSIX half checks the fix did not cost the
owner-only mode where mode bits are the access mechanism.
"""

import json
import os
import stat
import sys

import pytest

from snatch.utils import write_private_json


def test_writes_without_fchmod(tmp_path, monkeypatch):
    monkeypatch.delattr(os, "fchmod", raising=False)
    target = tmp_path / "config.json"

    write_private_json(str(target), {"theme": "Nord"})

    assert json.loads(target.read_text(encoding="utf-8")) == {"theme": "Nord"}
    assert [p.name for p in tmp_path.iterdir()] == ["config.json"]


@pytest.mark.skipif(sys.platform == "win32",
                    reason="POSIX mode bits are not the access mechanism on Windows")
def test_still_owner_only_on_posix(tmp_path):
    target = tmp_path / "history.json"
    target.write_text("[]", encoding="utf-8")
    os.chmod(target, 0o664)

    write_private_json(str(target), [])

    assert stat.S_IMODE(os.lstat(target).st_mode) == 0o600
