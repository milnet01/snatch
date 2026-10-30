"""The download queue survives closing the app (SNAT-0023).

queue.json is user-editable and may hold anything, so what comes back is
checked, and nothing a saved queue contains can start a download by itself.
"""

import json
import os
import stat
import sys

import pytest

from snatch.downloader import (DownloaderMixin, MAX_SAVED_QUEUE_ROWS,
                               parse_saved_queue, rows_to_save)
from snatch.utils import PRIVATE_DATA_FILES

URL = "https://example.invalid/a"


def test_rows_come_back_pending_whatever_they_were():
    saved = [{"url": URL, "title": "A", "status": "42%"}]
    assert parse_saved_queue(saved, DownloaderMixin._is_valid_url) == [
        {"url": URL, "status": "Pending", "title": "A"}]


@pytest.mark.parametrize("data", [5, "x", None, {"url": URL}])
def test_a_file_of_the_wrong_shape_gives_an_empty_queue(data):
    assert parse_saved_queue(data, DownloaderMixin._is_valid_url) == []


@pytest.mark.parametrize("row", [
    5, None, {}, {"url": 5}, {"url": "file:///etc/passwd"}, {"url": "-x"},
])
def test_a_bad_row_is_dropped_and_the_rest_kept(row):
    parsed = parse_saved_queue([row, {"url": URL}], DownloaderMixin._is_valid_url)
    assert [r["url"] for r in parsed] == [URL]


def test_a_missing_or_odd_title_falls_back_to_the_url():
    parsed = parse_saved_queue([{"url": URL, "title": 7}],
                               DownloaderMixin._is_valid_url)
    assert parsed[0]["title"] == URL[:60]


def test_a_huge_file_is_capped():
    saved = [{"url": f"{URL}{i}"} for i in range(MAX_SAVED_QUEUE_ROWS + 5)]
    parsed = parse_saved_queue(saved, DownloaderMixin._is_valid_url)
    assert len(parsed) == MAX_SAVED_QUEUE_ROWS


def test_finished_rows_are_not_saved():
    rows = [{"url": URL, "status": s, "title": s}
            for s in ("Done", "Failed", "Cancelled", "42%", "Pending")]
    assert [r["title"] for r in rows_to_save(rows)] == [
        "Failed", "Cancelled", "42%", "Pending"]


class Host(DownloaderMixin):
    def __init__(self, path):
        self.queue_file = str(path)
        self.download_queue = []


def test_save_then_load_round_trips(tmp_path):
    host = Host(tmp_path / "queue.json")
    host.download_queue = [{"url": URL, "status": "Pending", "title": "A"}]
    host._save_queue()
    other = Host(tmp_path / "queue.json")
    other._load_queue()
    assert other.download_queue == host.download_queue


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX mode bits")
def test_the_file_is_owner_only(tmp_path):
    host = Host(tmp_path / "queue.json")
    host._save_queue()
    assert stat.S_IMODE(os.stat(host.queue_file).st_mode) == 0o600


def test_it_is_in_the_permission_repair_list():
    assert "queue.json" in PRIVATE_DATA_FILES


@pytest.mark.parametrize("content", [b"not json", b"\xff\xfe", b"[{}]"])
def test_a_damaged_file_never_raises(tmp_path, content):
    path = tmp_path / "queue.json"
    path.write_bytes(content)
    host = Host(path)
    host._load_queue()
    assert host.download_queue == []


def test_a_directory_in_its_place_never_raises(tmp_path):
    host = Host(tmp_path)
    host._load_queue()
    assert host.download_queue == []


def test_a_failed_save_never_raises(tmp_path):
    host = Host(tmp_path / "missing-folder" / "queue.json")
    host.download_queue = [{"url": URL, "status": "Pending", "title": "A"}]
    host._save_queue()
    assert not os.path.exists(host.queue_file)
    assert json.dumps(host.download_queue)
