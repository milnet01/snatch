"""Worker threads must not touch Tk, and the GUI thread must not block on IPC.

STANDARDS.md 4.1 rule 1 ("all blocking operations run in daemon threads") and
rule 2 ("never modify GUI from a thread") are both unconditional. SNAT-0048
is the MEDIUM tail the 2026-09-01 CRITICAL/HIGH pass left behind.

The first test here is the one worth having. Rather than naming the four
breaches that existed on 2026-09-02, it walks the AST of every function this
codebase hands to threading.Thread and fails on any Tk variable access that
is not marshalled through root.after -- so a breach introduced later is
caught by the same test, without anyone remembering to extend a list.

Depending on the _tkinter build, a Tk call from a worker either takes the Tcl
lock or raises RuntimeError. Neither is something a test can provoke
reliably, which is why this is asserted structurally.
"""

import ast
import pathlib
import threading
import time

import pytest

from snatch.downloader import DownloaderMixin
from snatch.player import PlayerMixin

PACKAGE = pathlib.Path(__file__).resolve().parent.parent / "snatch"


def _thread_target_names(tree):
    """Names handed to threading.Thread(target=...) anywhere in a module."""
    names = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        is_thread = (isinstance(func, ast.Attribute) and func.attr == "Thread") or \
                    (isinstance(func, ast.Name) and func.id == "Thread")
        if not is_thread:
            continue
        for kw in node.keywords:
            if kw.arg != "target":
                continue
            if isinstance(kw.value, ast.Attribute):
                names.add(kw.value.attr)
            elif isinstance(kw.value, ast.Name):
                names.add(kw.value.id)
    return names


def _tk_access_outside_after(func_node):
    """Tk variable reads/writes in this function, skipping root.after payloads.

    Anything passed to root.after runs on the main thread by definition, so
    its subtree is not walked.
    """
    found = []

    def walk(node):
        if isinstance(node, ast.Call):
            target = node.func
            if (isinstance(target, ast.Attribute) and target.attr == "after"
                    and isinstance(target.value, ast.Attribute)
                    and target.value.attr == "root"):
                return  # scheduled onto the main thread; not a breach
        if (isinstance(node, ast.Attribute) and node.attr in ("get", "set")
                and isinstance(node.value, ast.Attribute)
                and node.value.attr.endswith("_var")):
            found.append((node.lineno, f"{node.value.attr}.{node.attr}()"))
        for child in ast.iter_child_nodes(node):
            walk(child)

    for child in ast.iter_child_nodes(func_node):
        walk(child)
    return found


def _worker_functions():
    """Every function this package runs on a thread, with its module path."""
    for path in sorted(PACKAGE.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        targets = _thread_target_names(tree)
        if not targets:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name in targets:
                yield path, node


def test_at_least_one_worker_is_found():
    """Guards the walker itself: a broken matcher would pass every test below."""
    workers = list(_worker_functions())
    assert len(workers) >= 4, [n.name for _, n in workers]


def test_no_worker_touches_a_tk_variable_directly():
    """What this does NOT reach: a helper the worker calls.

    It reads each worker's own body, so a Tk access one call deeper is
    invisible to it -- which is exactly where _get_cookie_args hid its two
    reads until they were hoisted into _cookie_state(). The tests below
    cover that one; a future helper would need its own.
    """
    breaches = []
    for path, node in _worker_functions():
        for lineno, what in _tk_access_outside_after(node):
            breaches.append(f"{path.name}:{lineno} in {node.name}() -> {what}")
    assert not breaches, (
        "STANDARDS.md 4.1 rule 2: read the value on the main thread and pass "
        "it in, or write it back through root.after(0, ...):\n  "
        + "\n  ".join(breaches)
    )


# ── The snapshot the workers are given ───────────────────────────────

def test_get_cookie_args_requires_a_snapshot():
    """A caller must decide which thread reads the variables.

    The parameter is required rather than defaulted, so a new worker cannot
    fall back to reading the Tk variables by leaving it out.
    """
    with pytest.raises(TypeError):
        DownloaderMixin._get_cookie_args(object())


def test_get_cookie_args_uses_the_snapshot_it_is_given(monkeypatch):
    seen = {}

    def fake(cookies_file, browser):
        seen["args"] = (cookies_file, browser)
        return ["--cookies", cookies_file]

    monkeypatch.setattr("snatch.downloader.get_cookie_args", fake)

    class Host:
        def __init__(self):
            self.failed_cookie_args = []

    args = DownloaderMixin._get_cookie_args(Host(), ("/tmp/c.txt", "firefox"))

    assert seen["args"] == ("/tmp/c.txt", "firefox")
    assert args == ["--cookies", "/tmp/c.txt"]


def test_a_source_already_known_to_fail_is_dropped(monkeypatch):
    monkeypatch.setattr("snatch.downloader.get_cookie_args",
                        lambda f, b: ["--cookies-from-browser", b])

    class Host:
        def __init__(self):
            self.failed_cookie_args = ["--cookies-from-browser", "chrome"]

    assert DownloaderMixin._get_cookie_args(Host(), ("", "chrome")) == []


# ── mpv IPC no longer blocks the caller ──────────────────────────────

class _Root:
    """Hands out a distinct token per after(), so a cancel is observable."""

    def __init__(self):
        self.scheduled = []      # (token, ms, func)
        self.cancelled = []

    def after(self, ms, func=None):
        token = f"after#{len(self.scheduled) + 1}"
        self.scheduled.append((token, ms, func))
        return token

    def after_cancel(self, token):
        self.cancelled.append(token)

    def pending(self):
        return [c for c in self.scheduled if c[0] not in self.cancelled]


def test_an_ipc_round_trip_does_not_run_on_the_caller_thread():
    """The whole point: a wedged mpv must not stall whoever asked."""
    ran_on = {}
    released = threading.Event()

    class Host(PlayerMixin):
        def __init__(self):
            self.root = _Root()

        def _mpv_command(self, command):
            ran_on["thread"] = threading.current_thread().name
            time.sleep(0.05)
            released.set()
            return {"data": 1}

    host = Host()
    caller = threading.current_thread().name

    started = time.monotonic()
    host._mpv_command_async(["get_property", "duration"])
    returned_after = time.monotonic() - started

    assert released.wait(2), "the command never ran"
    assert ran_on["thread"] != caller
    assert returned_after < 0.05, "the caller blocked for the round-trip"


def test_a_result_comes_back_through_root_after():
    """Rule 2 in the other direction: the reply lands on the main thread."""
    done = threading.Event()

    class Host(PlayerMixin):
        def __init__(self):
            self.root = _Root()

        def _mpv_command(self, command):
            return {"data": 42}

    host = Host()
    host._mpv_command_async(["get_property", "x"], on_result=lambda r: None)
    for _ in range(200):
        if host.root.scheduled:
            done.set()
            break
        time.sleep(0.01)

    assert done.is_set(), "the result was never scheduled onto the main thread"
    assert host.root.scheduled[0][1] == 0, "should be after(0, ...), not a delay"


def test_dragging_the_volume_slider_sends_once():
    """The Scale callback fires per increment; only the last value matters.

    Each increment schedules a send and cancels the one before it, so a drag
    of eight steps leaves exactly one pending, carrying the value the user
    settled on -- instead of eight blocking IPC round-trips.
    """
    class Host(PlayerMixin):
        def __init__(self):
            self.root = _Root()
            self.mpv_process = None

    host = Host()
    for value in range(0, 40, 5):
        host._on_volume_change(float(value))

    pending = host.root.pending()
    assert len(pending) == 1, f"{len(pending)} sends left pending, expected 1"
    assert pending[0][2] == host._send_pending_volume
    assert pending[0][0] == host._volume_send_id
    assert host._pending_volume == 35
