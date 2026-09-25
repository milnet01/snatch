"""Packaged-build self-test: `snatch --selftest [REPORT_FILE]` (SNAT-0024).

CI built three artefacts and started none of them, so a bundle that built
cleanly and then died on launch -- a missing hidden import, a binary left out
of the bundle, a platform call the frozen Python lacks -- was green in CI and
broken for the user. SNAT-0073 was that last kind: every private write raised
AttributeError on the Windows build, and nothing ran the build to see it.

This checks what packaging can break, without opening a window, so it runs on
a CI machine with no display. The exit status is the verdict (0 pass, 1 fail).
The Windows build has no console, so its stdout goes nowhere: pass a report
file to read the per-check results there.
"""

import importlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

from . import HAS_DND, platform_utils
from .utils import write_private_json

# Every module in the package. tests/test_selftest.py fails when a module on
# disk is missing from this list, so a new one cannot be left unchecked.
MODULES = (
    "snatch.app",
    "snatch.cookies",
    "snatch.downloader",
    "snatch.logging_setup",
    "snatch.platform_utils",
    "snatch.player",
    "snatch.selftest",
    "snatch.tabs.download",
    "snatch.tabs.history",
    "snatch.tabs.media_info",
    "snatch.tabs.search",
    "snatch.theme",
    "snatch.utils",
    "snatch.version",
    "snatch.widgets",
)

# The binaries fetch-binaries.sh bundles on every platform. mpv is added on
# Windows, the one platform that bundles it.
BUNDLED = ("yt-dlp", "ffmpeg", "ffprobe", "qjs")
PROBE_TIMEOUT_SEC = 30


class Skip(Exception):
    """A check that does not apply to this run -- reported, never a failure."""


def _check_imports():
    for name in MODULES:
        importlib.import_module(name)
    return f"{len(MODULES)} modules"


def _check_tcl():
    # A Tcl interpreter needs no display, and proves the bundled Tcl/Tk
    # libraries were found -- the part of tkinter a frozen build most often
    # loses.
    import tkinter
    return "Tcl " + tkinter.Tcl().eval("info patchlevel")


def _check_optional_libs():
    found = []
    from .downloader import HAS_PIL
    if HAS_PIL:
        from PIL import Image, ImageTk  # noqa: F401 -- the import is the check
        found.append("Pillow")
    if HAS_DND:
        found.append("tkinterdnd2")
    if not found:
        raise Skip("neither Pillow nor tkinterdnd2 is installed")
    return ", ".join(found)


def _probe(path):
    """Run a binary's version query; return its first output line."""
    for flag in ("--version", "-version"):
        try:
            done = subprocess.run([path, flag], capture_output=True, text=True,
                                  timeout=PROBE_TIMEOUT_SEC)
        except subprocess.TimeoutExpired:
            continue
        if done.returncode == 0:
            out = (done.stdout or done.stderr).strip().splitlines()
            return out[0] if out else "ran"
    raise RuntimeError(f"{path} did not run")


def _check_binary(name):
    def check():
        if name == "mpv":
            path = platform_utils.find_mpv()
            bundled = path and platform_utils.is_frozen()
        else:
            path = platform_utils._find_bundled_binary(name)
            bundled = path is not None
        if not bundled:
            if platform_utils.is_frozen():
                raise RuntimeError(f"{name} is not in the bundle")
            raise Skip("not bundled in a source run")
        return _probe(path)
    return check


def _check_private_write():
    # The exact path config.json, history.json and cookies.txt take.
    directory = tempfile.mkdtemp(prefix="snatch-selftest-")
    try:
        target = os.path.join(directory, "config.json")
        write_private_json(target, {"selftest": True})
        write_private_json(target, {"selftest": "overwrite"})
        with open(target, encoding="utf-8") as handle:
            if json.load(handle) != {"selftest": "overwrite"}:
                raise RuntimeError("read back something other than was written")
        return "write, overwrite and read back"
    finally:
        shutil.rmtree(directory, ignore_errors=True)


def _checks():
    checks = [("import every module", _check_imports),
              ("Tcl runtime", _check_tcl),
              ("optional libraries", _check_optional_libs)]
    names = BUNDLED + (("mpv",) if platform_utils.is_windows() else ())
    checks += [(f"bundled {n}", _check_binary(n)) for n in names]
    checks.append(("private settings write", _check_private_write))
    return checks


def run(report_path=None):
    """Run every check; write the report; return the exit status."""
    lines, failed = [], 0
    for label, check in _checks():
        try:
            lines.append(f"PASS  {label}: {check()}")
        except Skip as why:
            lines.append(f"SKIP  {label}: {why}")
        except Exception as exc:  # the report must name every failure
            failed += 1
            lines.append(f"FAIL  {label}: {type(exc).__name__}: {exc}")
    lines.append(f"{'FAILED' if failed else 'OK'}: {failed} check(s) failed")
    report = "\n".join(lines) + "\n"
    if report_path:
        with open(report_path, "w", encoding="utf-8") as handle:
            handle.write(report)
    if sys.stdout is not None:  # None in the console-less Windows build
        sys.stdout.write(report)
    return 1 if failed else 0
