"""SearchTabMixin re-entrancy — one search at a time, one animation at a time.

SNAT-0049 filed three consequences of the same missing guard. Two clicks on
Search started two yt-dlp subprocesses and two `after` animation chains; the
second chain overwrote the attribute holding the first one's id, so the first
could never be cancelled and rewrote the status label every 400 ms forever.
Worse, the tree could end up showing one search's rows while search_results
held the other's, and Play/Download read search_results -- so a click acted on
a different video from the one highlighted.

These exercise the mixin's methods against a stub host. There is no Tk root:
the point is the ordering of the guard and the state writes, and a real
widget tree would not make that any more true.
"""

import pytest

from snatch.tabs import search
from snatch.tabs.search import SearchTabMixin


class _FakeVar:
    def __init__(self, value=""):
        self._value = value

    def get(self):
        return self._value

    def set(self, value):
        self._value = value


class _FakeTree:
    def __init__(self):
        self.rows = []

    def get_children(self):
        return tuple(str(i) for i in range(len(self.rows)))

    def delete(self, *items):
        self.rows = []

    def insert(self, parent, index, iid=None, values=()):
        self.rows.append(values)


class _FakeRoot:
    """Records after()/after_cancel() instead of running them.

    Callbacks are never invoked, which is what keeps _tick_search_anim from
    recursing and lets the test read the scheduling decisions directly.
    """

    def __init__(self):
        self.scheduled = []
        self.cancelled = []

    def after(self, ms, func=None):
        token = f"after#{len(self.scheduled) + 1}"
        self.scheduled.append((token, ms, func))
        return token

    def after_cancel(self, token):
        self.cancelled.append(token)


class _Host(SearchTabMixin):
    """The attributes SearchTabMixin expects the app to provide."""

    def __init__(self):
        self.root = _FakeRoot()
        self.is_searching = False
        self.search_results = []
        self.search_tree = _FakeTree()
        self.search_status_var = _FakeVar()
        self.search_var = _FakeVar("cats")
        self.search_channel_var = _FakeVar()
        self.search_category_var = _FakeVar("Any")
        self.search_count_var = _FakeVar("20")
        self.search_sort_var = _FakeVar("Relevance")
        # Read by _perform_search on the main thread and passed to the worker
        # rather than read there (SNAT-0048).
        self.search_duration_var = _FakeVar("Any")

    def _cookie_state(self):
        """The snapshot _perform_search takes on the main thread (SNAT-0048)."""
        return ("", "none")


class _Recorder:
    """Stands in for tkinter.messagebox, which needs a root to display."""

    def __init__(self):
        self.warnings = []
        self.errors = []

    def showwarning(self, title, message):
        self.warnings.append((title, message))

    def showerror(self, title, message):
        self.errors.append((title, message))


@pytest.fixture
def messages(monkeypatch):
    recorder = _Recorder()
    monkeypatch.setattr(search, "messagebox", recorder)
    return recorder


@pytest.fixture
def no_threads(monkeypatch):
    """Capture the worker instead of starting yt-dlp."""
    started = []

    class _FakeThread:
        def __init__(self, target=None, args=()):
            self.target = target
            self.args = args
            self.daemon = False

        def start(self):
            started.append(self)

    monkeypatch.setattr(search.threading, "Thread", _FakeThread)
    return started


def test_a_second_search_is_refused_while_one_is_running(messages, no_threads):
    host = _Host()
    host.is_searching = True

    host._perform_search()

    assert messages.warnings, "the second click was accepted silently"
    assert not no_threads, "a second yt-dlp subprocess was started"
    assert host.root.scheduled == [], "a second animation chain was started"


def test_the_first_search_is_accepted(messages, no_threads):
    host = _Host()

    host._perform_search()

    assert host.is_searching is True
    assert len(no_threads) == 1
    assert messages.warnings == []


def test_starting_the_animation_cancels_one_already_running():
    host = _Host()

    host._start_search_anim()
    first_id = host._search_anim_id
    host._start_search_anim()

    assert host.root.cancelled == [first_id], (
        "the first chain was left running and is now unreachable"
    )


def test_results_and_tree_rows_are_published_together():
    host = _Host()
    host.is_searching = True
    entries = [{"title": "A", "url": "abc"}, {"title": "B", "url": "def"}]

    host._display_search_results(entries)

    # Both writes happen in this one main-thread call, so nothing can clear
    # search_results between the tree being filled and the list being set.
    assert host.search_results == entries
    assert len(host.search_tree.rows) == 2
    assert host.is_searching is False


def test_a_failed_search_releases_the_guard(messages):
    host = _Host()
    host.is_searching = True

    host._search_error("ERROR: nope")

    assert host.is_searching is False, "a failed search would block every later one"
    assert messages.errors


def test_the_thread_does_not_write_search_results_itself():
    """The assignment must not be reintroduced in _search_thread.

    On the worker it raced _change_theme, which clears search_results: the
    callback then filled the tree while the list was empty, and every row
    reported "Select a search result first".
    """
    import inspect

    source = inspect.getsource(SearchTabMixin._search_thread)
    assert "self.search_results" not in source
