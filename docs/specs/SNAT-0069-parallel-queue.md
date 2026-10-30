<!-- ants-spec-format: 1 -->
# SNAT-0069 — Run queued downloads at the same time

**Status:** accepted (2026-10-30), no review gate at the user's instruction (§3).
**Kind:** implement.
**Source:** ROADMAP SNAT-0069 (split from SNAT-0039).

A new "At once" menu beside the download queue lets several queued videos download together; it starts at 1, so nothing changes until you ask for more.

## 1. Goal

The queue can run up to three downloads at once, chosen by the user. Each queue row shows its own state, and the one progress bar shows the whole queue. At the default of 1 the queue runs one item at a time, as it does now.

## 2. Problem

`DownloaderMixin._download_complete` advances `queue_index` and starts the next item, so one queue item runs at a time. The state assumes that everywhere:

1. `self.download_process` holds one process. `cancel_download` reaches only that one.
2. `self.is_downloading` is one flag, read by `_download_thread` to detect a cancel.
3. `_process_next_queue_item` sets `url_var` to pass the URL, and `_download_complete` reads `url_var` back for the history record. With two running, a record would carry the wrong URL.
4. `progress_var`, `status_var` and the window title each show one download.
5. `_show_merge_progress` switches the one bar to indeterminate mode.
6. `queue_index` names one current row. `_download_complete` and `_queue_item_failed` mark that row.

Running processes side by side also creates three hazards that do not exist today:

7. **Same output file.** The template is `%(title)s.%(ext)s`, so two videos with one title write one file. yt-dlp's `sanitize_open` falls back to a plain `open` when the lock fails, and never locks on Windows (`yt_dlp/utils/_utils.py`, read on 2026.10.21). The downloads would corrupt each other with no error.
8. **Speed limit.** `FileDownloader.slow_down` counts per process, so N downloads under a limit could reach N times it.
9. **Cookies file.** `YoutubeDL.close` calls `save_cookies`, which rewrites a `--cookies` file on exit. A process starting at that moment can read it part-written.

## 3. Scope decisions (agreed with the user)

- **Write this spec, skip its review gate.** The user, 2026-10-30: "Write a spec first but no need to review it. The coding will be the review."

Made by the author and not yet put to the user. Each is cheap to change:

- **Default 1, choices 1, 2, 3.** The throughput gain is unmeasured, and SNAT-0040's own measurement found a similar claim did not hold on a fast connection. The cap stays small because unbounded parallel downloads invite rate limiting.
- **The one bar shows the whole queue.** Per-item percent goes in the queue row's Status column. No extra bars, because the Progress area has no room for them.
- **Above 1, filenames gain the video id**: `%(title)s [%(id)s].%(ext)s`. This removes hazard 7. At 1 they stay as they are.
- **Cancel stops everything.** It ends every running download and the queue, as it does today. Per-item cancel is out of scope.

## 4. Design

### 4.1 One job per download

`snatch/downloader.py` gains a small class. A job replaces `self.download_process` and the worker's reliance on `self.is_downloading`.

```python
class DownloadJob:
    url, save_path, format_spec, options, audio_only, merge
    history_title, history_format
    entry      # the queue row dict, or None for a single download
    proc       # subprocess.Popen once started, else None
    cancelled  # set by cancel_download, read by the worker
    percent    # last reported, 0-100
```

`self.active_jobs` is a list touched only on the main thread. `self.is_downloading` stays, set while any job runs, because `_on_close` and the Busy guards read it.

`_download_thread` takes a job. It reads no Tk variable and no `self.*` download state. Single downloads and queue items share this one path.

### 4.2 Choosing what starts

Pure functions, so they can be tested without a display:

```python
def queue_limit(at_once, speed_limit, cookies_file) -> int
    # 1 if a speed limit or a cookies file is set, or at_once is not offered;
    # otherwise int(at_once).

def next_queue_entries(queue, active_urls, slots) -> list
    # The first `slots` rows with status "Pending" whose URL is not running
    # and not already chosen in this call.
```

`_fill_queue_slots` replaces `_process_next_queue_item`. It runs on the main thread, does nothing unless `is_processing_queue` is true, starts jobs until the limit is reached, and ends the queue when no job runs and no row is Pending. The existing 500 ms pause after a finish stays. A stale pause firing after a cancel finds `is_processing_queue` false; firing after a restart, it only fills free slots.

It re-reads the limit on each call, so a menu change takes effect at the next start. Running downloads are left alone.

`_start_download` keeps its signature for single downloads. Queue jobs do not pass through `url_var`, so the URL box is left alone during a queue run, including at 1.

### 4.3 The command

`_download_thread` builds the same command as today, with two differences when the limit in force is above 1:

- `-o` uses `%(title)s [%(id)s].%(ext)s`.
- `_rate_args` is called with fragments `"1"`, because parallel parts in each of three downloads would open up to 24 connections to one site.

The limit in force is stored in the job's `options` when it is created. The `--` separator and `_is_valid_url` gate stay on every job.

### 4.4 What the user sees

| Where | Single download | Queue |
|---|---|---|
| Progress bar | that download | `(finished + sum of running percents / 100) / rows` |
| Status line | yt-dlp's line, as now | `Downloading 3 of 10...`, or `Downloading 3 of 10 (2 at once)` while more than one runs |
| Window title | percent, as now | the bar's percent |
| Queue row Status | not applicable | `Pending`, `Starting`, `42%`, `Merging`, `Done`, `Failed`, `Cancelled` |
| Merge | indeterminate bar, as now | row says `Merging`; bar stays determinate |

The menu is an `ttk.Combobox` labelled "At once:" in `queue_btn_row` in `snatch/tabs/download.py`. Its variable is `self.queue_at_once_var`, saved as the `queue_at_once` key in `_save_config`, default `"1"`. `queue_limit` treats a value it does not offer as 1.

Workers report at most every `PROGRESS_THROTTLE_SEC`, as now. The main-thread handler stores the percent and redraws only if `PROGRESS_THROTTLE_SEC` has passed since the last redraw. It updates the queue row in place and does not rebuild the tree.

### 4.5 Finishing and cancelling

`_download_complete` and `_queue_item_failed` take the job. They mark `job.entry`, record history from `job.url`, `job.history_title` and `job.history_format`, set `last_download_path` from `job.save_path`, and remove the job from `active_jobs`. In queue mode they then schedule `_fill_queue_slots`.

Clearing the queue during a run removes the rows. Running jobs keep their row dicts, finish, and record history.

Pressing Download Queue again runs every row that is not Done. Before this change it ran every row, Done ones included. A single download started between two queue items is refused as Busy, because `is_processing_queue` is still true.

`cancel_download` sets `cancelled` on every job and `is_processing_queue` false. It calls `terminate()` on every process first, then waits on them against one shared `TERMINATE_GRACE_SEC` deadline, then calls `kill()` on any left, then waits against one shared `KILL_GRACE_SEC` deadline. This keeps the main thread's wait the same as today however many are running. Running rows become `Cancelled`; Pending rows stay Pending.

## 5. Invariants

Each clause names the rule its fixture isolates. Every *Breaks when* was applied to the code on 2026-10-30, and the named test failed.

- **INV-1** — Never more jobs run than `queue_limit` allows.
  *Test:* `tests/test_download_queue.py::test_fill_stops_at_the_limit`, with a stubbed job starter and five Pending rows at limit 2; isolates the slot count.
  *Breaks when:* `_fill_queue_slots` is called twice before a job finishes and the second call does not count running jobs.

- **INV-2** — A speed limit or a cookies file forces one at a time, and a value not offered counts as 1.
  *Test:* `tests/test_download_queue.py::test_queue_limit`, with `at_once` "3" in each case; each case differs from the passing one in one argument.
  *Breaks when:* a saved `queue_at_once` of "999" or "abc" is passed to `int()` unchecked.

- **INV-3** — The same URL never runs twice at once, and the held row runs later.
  *Test:* `tests/test_download_queue.py::test_duplicate_url_is_held`, with two rows of one URL and two free slots.
  *Breaks when:* `next_queue_entries` checks `active_urls` but not the rows chosen in the same call.

- **INV-4** — Above 1, the output template contains `%(id)s`; at 1 it is exactly `%(title)s.%(ext)s`.
  *Test:* `tests/test_download_queue.py::test_output_template`, on the command builder.
  *Breaks when:* the template is chosen from the menu's value and not the limit in force, so a speed limit at "At once: 3" still changes filenames.

- **INV-5** — Above 1, no `--concurrent-fragments` is passed.
  *Test:* `tests/test_download_queue.py::test_no_parallel_parts_above_one`, with fragments "8".
  *Breaks when:* the command builder passes `options["fragments"]` straight to `_rate_args`.

- **INV-6** — Each history record carries its own job's URL and title, whatever `url_var` holds.
  *Test:* `tests/test_download_queue.py::test_history_uses_the_job`, finishing two jobs in reverse start order with `url_var` set to something else.
  *Breaks when:* `_download_complete` reads `url_var`, as it does today.

- **INV-7** — One item's failure marks only its row, and the rest of the queue continues.
  *Test:* `tests/test_download_queue.py::test_failure_marks_only_its_row`.
  *Breaks when:* the failure path calls `_reset_ui` while another job runs, clearing `is_downloading` and stopping that job's worker.

- **INV-8** — Cancel ends every process, and the main thread waits at most `TERMINATE_GRACE_SEC` + `KILL_GRACE_SEC` in total. Each wait is bounded (CLAUDE.md, the `Popen` carve-out).
  *Test:* `tests/test_download_queue.py::test_cancel_shares_one_deadline`, with three fake processes that ignore `terminate()` and a fake clock.
  *Breaks when:* each process gets its own `wait(timeout=TERMINATE_GRACE_SEC)` in turn, so three stubborn ones hold the window for three times as long.

- **INV-9** — After a cancel, no new job starts, including from a pause already scheduled.
  *Test:* `tests/test_download_queue.py::test_no_start_after_cancel`, calling `_fill_queue_slots` after `cancel_download`.
  *Breaks when:* `_fill_queue_slots` does not check `is_processing_queue`.

- **INV-10** — A cancelled job's worker makes no UI change after the cancel, and a cancelled job records no history.
  *Test:* `tests/test_download_queue.py::test_cancelled_job_is_silent`, a worker over a fake process with `cancelled` set mid-output.
  *Breaks when:* the worker tests `is_downloading`, which another job can keep true.

- **INV-11** — Trust boundary: every job's URL passes `_is_valid_url` immediately before the command is built, and `--` precedes it. Queue URLs come from remote playlist JSON.
  *Test:* `tests/test_download_queue.py::test_bad_url_never_reaches_popen`, a row added directly with a `file://` URL; it is marked Failed and `Popen` is not called.
  *Breaks when:* validation stays only in `_start_download`, which queue jobs no longer pass through.

- **INV-12** — The queue bar's value is `(finished + sum of running percents / 100) / rows`, capped at `QUEUE_RUNNING_MAX_PERCENT` while a row runs.
  *Test:* `tests/test_download_queue.py::test_queue_percent`.
  *Breaks when:* Failed rows are left out of `finished`, so the bar never reaches 100 on a queue with a failure.

- **INV-13** — A single download behaves as before: same command, same dialogs, and a second start refused as Busy.
  *Test:* `tests/test_download_queue.py::test_single_download_command`, plus the manual recipe in §7.
  *Breaks when:* a single download picks up the queue's template or its row handling.

## 6. Failure modes

- **A job cannot start** (`Popen` raises, or the save folder is gone): its row is Failed and the queue continues. Today the same case on the save-folder check leaves the row at "Downloading" and the queue stuck, because `_start_download` returns early.
- **The site rate-limits parallel requests:** those items report Failed through yt-dlp's exit code. The user can retry at 1.
- **The disk fills:** each yt-dlp fails on its own, and each row is Failed.
- **The queue is cancelled while its rows are at `Starting`:** yt-dlp is still reading metadata, and it ends the same way (seen 2026-10-30).
- **The window closes during a run:** `_on_close` already asks when `is_downloading` is true and calls `cancel_download`, which now covers every job.
- **Two different videos share a title at 1:** one at a time, so this stays as it is today.
- **The user changes the save folder mid-run:** each job holds the folder it started with, which is the existing `options` snapshot behaviour.
- **A browser cookie source (`--cookies-from-browser`) above 1:** it reads the browser's store and does not write a file, so it stays allowed. Whether a browser's own lock slows it is unmeasured.

## 7. Tests

`tests/test_download_queue.py` holds every clause in §5, using a fake host class in the manner of `tests/test_thread_discipline.py`, fake processes and no display. Each test must be seen to fail against a broken version before it counts, by the mutation each *Breaks when* names.

Manual recipe, on a private display and with real downloads, because no test here drives the GUI or the network:

1. Queue three short Creative Commons videos, at "At once: 2".
2. Check two rows show percents, the bar moves, and all three end Done with `[id]` in their filenames.
3. Repeat and press Cancel mid-run: rows show Cancelled, the remaining row stays Pending, and no yt-dlp process is left.
4. Queue the same videos at 1: filenames have no `[id]`, one row runs at a time.

## 8. Alternatives considered (and rejected)

- **A temp folder per job (`--paths temp:`).** Stops `.part` collisions, but the final move still lets one video replace another of the same title. Silent loss.
- **Asking yt-dlp for each filename first (`--print filename`).** Accurate, but adds a network probe per item to a feature whose point is speed, and the check can go stale before the download starts.
- **Dividing the speed limit among jobs.** The limit would have to be re-divided as jobs start and finish, and yt-dlp takes it only at launch.
- **A progress bar per download.** No room in the Progress area, and the queue row already gives each item a place to report.
- **A lock around the cookies file.** yt-dlp writes the file itself, so a lock in Snatch cannot cover it.
- **Default 2.** Would speed queues for everyone, on an unmeasured claim, and would change filenames without being asked.

## 9. Out of scope

- Keeping the queue across restarts — tracked by SNAT-0023.
- Cancelling one item — deferred; not yet queued.
- Retrying failed items — deferred; not yet queued.
- Measuring the throughput gain on a slow connection, to reconsider the default — deferred; not yet queued.

## 10. What checks this

| Rule | What catches a breach |
|------|----------------------|
| INV-1 to INV-13 | the named tests in `tests/test_download_queue.py` |
| The queue running against real yt-dlp, real files and a real cancel | **nothing** automated; §7's manual recipe, run on Linux on 2026-10-30 |
| Windows and macOS behaviour of parallel processes | **`Partial:`** CI's self-test proves the build starts, not that a queue runs |
| §4.4's display, row by row | **nothing** — no test drives the GUI |
| A real gain in speed | **nothing** — unmeasured, which is why the default is 1 |

## 11. Cross-doc impact

- `CHANGELOG.md`: an Added entry.
- `README.md`: the feature list, including the `[id]` filenames and that a speed limit or cookies file means one at a time.
- `STANDARDS.md`: the config key table gains `queue_at_once`.
- `ROADMAP.md`: SNAT-0069 carries the outcome.

## 12. Cold-eyes loop log

Rows live in `../reviews/SNAT-0069-parallel-queue-loop-log.md`.

## 13. Resource cost

Up to three yt-dlp processes and their ffmpeg children, against one today. The cap is `queue_limit`'s. `active_jobs` holds no more than the cap. No new dependency.

## 14. Migration / compatibility

A `config.json` without `queue_at_once` reads as `"1"`. An older Snatch ignores the key. Filenames change only for a user who raises the menu above 1.

## 15. Open questions

- Should a browser cookie source also force one at a time? §6 leaves it allowed, unmeasured.
