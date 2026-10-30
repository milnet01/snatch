"""The parallel queue's contract: docs/specs/SNAT-0069-parallel-queue.md § 5.

No display and no network: a fake host stands in for the app, fake processes
stand in for yt-dlp, and scheduled callbacks run when a test pumps them.
"""

import subprocess
from unittest.mock import MagicMock

import pytest

from snatch import downloader
from snatch.downloader import (DownloadJob, DownloaderMixin, next_queue_entries,
                               queue_limit, queue_percent, stop_processes)


class FakeRoot:
    def __init__(self):
        self.pending = []

    def after(self, _ms, fn):
        self.pending.append(fn)

    def pump(self):
        while self.pending:
            self.pending.pop(0)()


class FakeVar:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class FakeProc:
    """Prints `lines`, then exits with `code`."""

    def __init__(self, lines=(), code=0):
        self.stdout = MagicMock()
        self.stdout.__iter__ = lambda _self: iter(lines)
        self.returncode = code
        self.terminated = False

    def terminate(self):
        self.terminated = True

    def wait(self, timeout=None):
        return self.returncode

    def poll(self):
        return self.returncode


class Host(DownloaderMixin):
    def __init__(self, tmp_path, at_once="2", speed="Unlimited", fragments="1"):
        self.root = FakeRoot()
        self.active_jobs = []
        self.download_queue = []
        self.is_downloading = False
        self.is_processing_queue = False
        self.queue_at_once_var = FakeVar(at_once)
        self.speed_limit_var = FakeVar(speed)
        self.fragments_var = FakeVar(fragments)
        self.save_path_var = FakeVar(str(tmp_path))
        self.url_var = FakeVar("https://example.invalid/typed-in-the-box")
        self.status_var = FakeVar("")
        self.progress_var = FakeVar(0)
        self.subtitle_var = FakeVar(0)
        self.sponsorblock_var = FakeVar(0)
        self.last_download_path = ""
        self.last_download_title = ""
        self.last_download_format = ""
        self.video_title = ""
        self.failed_cookie_args = None
        self.history = []
        self.started = []
        for widget in ("download_btn", "cancel_btn", "open_folder_btn",
                       "queue_tree", "queue_status_label", "progress_bar"):
            setattr(self, widget, MagicMock())
        self._update_title_progress = MagicMock()
        self._cookie_state = lambda: ("", "none")
        self._preferred_format_spec = lambda: ("best", False)
        self._get_base_cmd = lambda: ["yt-dlp"]
        self._show_error = MagicMock()

    def _add_history_entry(self, title, url, fmt, path):
        self.history.append((title, url))

    def _spawn_worker(self, job):
        self.started.append(job)


def rows(*urls):
    return [{"url": u, "status": "Pending", "title": u[-1]} for u in urls]


URLS = [f"https://example.invalid/{c}" for c in "abcde"]


@pytest.fixture
def host(tmp_path, monkeypatch):
    monkeypatch.setattr(downloader, "messagebox", MagicMock())
    return Host(tmp_path)


def start_queue(host, *urls):
    host.download_queue = rows(*urls)
    host._process_queue()


# INV-1
def test_fill_stops_at_the_limit(host):
    start_queue(host, *URLS)
    assert len(host.started) == 2
    host._fill_queue_slots()  # the second call must count what is running
    assert len(host.started) == 2


def test_a_freed_slot_starts_exactly_one(host):
    start_queue(host, *URLS)
    host._download_complete(host.started[0])
    host.root.pump()
    assert len(host.started) == 3
    assert len(host.active_jobs) == 2


# INV-2
@pytest.mark.parametrize("at_once,speed,cookies,expected", [
    ("3", "Unlimited", False, 3),
    ("3", "2M", False, 1),
    ("3", "Unlimited", True, 1),
    ("999", "Unlimited", False, 1),
    ("abc", "Unlimited", False, 1),
    ("1", "Unlimited", False, 1),
])
def test_queue_limit(at_once, speed, cookies, expected):
    assert queue_limit(at_once, speed, cookies) == expected


# INV-3
def test_duplicate_url_is_held():
    queue = rows(URLS[0], URLS[0])
    assert next_queue_entries(queue, set(), 2) == [queue[0]]
    queue[0]["status"] = "Done"
    assert next_queue_entries(queue, set(), 2) == [queue[1]]


def test_a_url_already_running_is_held():
    queue = rows(URLS[0], URLS[1])
    assert next_queue_entries(queue, {URLS[0]}, 2) == [queue[1]]


# INV-4
def _output_template(job):
    cmd = DownloaderMixin._download_cmd(job.host, job)
    return cmd[cmd.index("-o") + 1]


def test_output_template(host, tmp_path):
    start_queue(host, URLS[0])
    job = host.started[0]
    job.host = host
    assert _output_template(job).endswith("%(title)s [%(id)s].%(ext)s")

    host.cancel_download()
    host.queue_at_once_var.set("1")
    host.started.clear()
    start_queue(host, URLS[1])
    job = host.started[0]
    job.host = host
    assert _output_template(job) == str(tmp_path / "%(title)s.%(ext)s")


def test_a_speed_limit_keeps_the_plain_template(tmp_path, monkeypatch):
    monkeypatch.setattr(downloader, "messagebox", MagicMock())
    host = Host(tmp_path, at_once="3", speed="2M")
    start_queue(host, URLS[0])
    job = host.started[0]
    job.host = host
    assert _output_template(job) == str(tmp_path / "%(title)s.%(ext)s")


# INV-5
def test_no_parallel_parts_above_one(tmp_path, monkeypatch):
    monkeypatch.setattr(downloader, "messagebox", MagicMock())
    host = Host(tmp_path, at_once="2", fragments="8")
    start_queue(host, URLS[0])
    assert "--concurrent-fragments" not in host._download_cmd(host.started[0])


def test_parallel_parts_still_apply_at_one(tmp_path, monkeypatch):
    monkeypatch.setattr(downloader, "messagebox", MagicMock())
    host = Host(tmp_path, at_once="1", fragments="8")
    start_queue(host, URLS[0])
    assert "--concurrent-fragments" in host._download_cmd(host.started[0])


# INV-6
def test_history_uses_the_job(host):
    start_queue(host, URLS[0], URLS[1])
    first, second = host.started
    host._download_complete(second)
    host._download_complete(first)
    assert host.history == [("b", URLS[1]), ("a", URLS[0])]


# INV-7
def test_failure_marks_only_its_row(host):
    start_queue(host, *URLS[:3])
    first, second = host.started
    host._queue_item_failed(first)
    assert host.is_downloading  # before the next item starts: the other job
    assert second in host.active_jobs  # is still running
    host.root.pump()
    assert host.download_queue[0]["status"] == "Failed"
    assert host.download_queue[1]["status"] != "Failed"
    assert len(host.started) == 3  # and the queue moved on


# INV-8
def test_cancel_shares_one_deadline(monkeypatch):
    clock = {"now": 0.0}

    class Stubborn:
        killed = False

        def terminate(self):
            pass

        def kill(self):
            self.killed = True

        def poll(self):
            return 0 if self.killed else None

        def wait(self, timeout=None):
            if self.killed:
                return 0
            clock["now"] += timeout
            raise subprocess.TimeoutExpired("yt-dlp", timeout)

    procs = [Stubborn(), Stubborn(), Stubborn()]
    stop_processes(procs, 3, 2, clock=lambda: clock["now"])
    assert clock["now"] <= 3 + 2
    assert all(p.killed for p in procs)


def test_cancel_reaches_every_process(host):
    start_queue(host, URLS[0], URLS[1])
    for job in host.started:
        job.proc = FakeProc()
    host.cancel_download()
    assert all(job.proc.terminated for job in host.started)
    assert not host.active_jobs
    assert not host.is_downloading
    assert [r["status"] for r in host.download_queue] == ["Cancelled", "Cancelled"]


# INV-9
def test_no_start_after_cancel(host):
    start_queue(host, *URLS)
    for job in host.started:
        job.proc = FakeProc()
    host.cancel_download()
    host.started.clear()
    host._fill_queue_slots()  # a pause scheduled before the cancel
    assert host.started == []
    assert host.download_queue[2]["status"] == "Pending"


# INV-10
def test_cancelled_job_is_silent(host, monkeypatch):
    job = DownloadJob(url=URLS[0], save_path="/tmp", format_spec="best",
                      options=host._download_options(), entry=rows(URLS[0])[0])
    host.active_jobs.append(job)

    def lines():
        yield "[download]  10.0% of 1MiB"
        job.cancelled = True
        yield "[download]  20.0% of 1MiB"

    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: FakeProc(lines()))
    host._download_thread(job)
    job.cancelled = True  # also covers callbacks queued before the cancel
    host.root.pump()
    assert host.history == []
    assert job.entry["status"] == "Pending"
    assert host.progress_var.get() == 0
    host.queue_tree.set.assert_not_called()


# INV-11
def test_bad_url_never_reaches_popen(host, monkeypatch):
    popen = MagicMock()
    monkeypatch.setattr(subprocess, "Popen", popen)
    host.download_queue = [{"url": "file:///etc/passwd", "status": "Pending",
                            "title": "x"}]
    host._process_queue()
    host._download_thread(host.started[0])
    host.root.pump()
    popen.assert_not_called()
    assert host.download_queue[0]["status"] == "Failed"


def test_url_comes_after_the_separator(host):
    start_queue(host, URLS[0])
    cmd = host._download_cmd(host.started[0])
    assert cmd[-2:] == ["--", URLS[0]]


# INV-12
def test_queue_percent():
    queue = rows(*URLS[:4])
    queue[0]["status"] = "Done"
    queue[1]["status"] = "Failed"
    assert queue_percent(queue, [50.0]) == pytest.approx(62.5)
    assert queue_percent(queue, [100.0, 100.0]) < 100  # still merging
    queue[2]["status"] = queue[3]["status"] = "Done"
    assert queue_percent(queue, []) == 100
    assert queue_percent([], []) == 0


# INV-13
def test_single_download_command(host, tmp_path):
    host.url_var.set(URLS[0])
    host._start_download("best")
    cmd = host._download_cmd(host.started[0])
    assert cmd[cmd.index("-o") + 1] == str(tmp_path / "%(title)s.%(ext)s")


def test_second_single_download_is_busy(host):
    host.url_var.set(URLS[0])
    host._start_download("best")
    host._start_download("best")
    assert len(host.started) == 1
    downloader.messagebox.showwarning.assert_called_once()


# § 6: a job that cannot start
def test_missing_save_folder_fails_rows_and_ends_the_queue(host, tmp_path):
    host.save_path_var.set(str(tmp_path / "gone"))
    start_queue(host, URLS[0], URLS[1])
    assert [r["status"] for r in host.download_queue] == ["Failed", "Failed"]
    assert host.started == []
    assert not host.is_processing_queue


def test_a_finished_queue_runs_nothing_twice(host):
    start_queue(host, URLS[0])
    host._download_complete(host.started[0])
    host.root.pump()
    assert not host.is_processing_queue
    host.started.clear()
    host._process_queue()
    assert host.started == []
