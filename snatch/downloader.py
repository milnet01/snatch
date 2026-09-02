"""Download engine, format fetching/filtering, and queue management"""

import os
import re
import json
import shutil
import subprocess
import threading
import time
import tkinter as tk
from tkinter import messagebox
import urllib.request
from io import BytesIO

from .utils import format_duration, format_filesize, clear_treeview
from .cookies import extract_browser_cookies, get_cookie_args
from .platform_utils import find_ytdlp, find_ffmpeg, find_jsruntime, is_windows
from .logging_setup import get_logger

log = get_logger(__name__)

try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


class DownloaderMixin:
    """Mixin providing download, format fetching, queue, and filter logic.
    Expects the host class to provide all relevant GUI widgets and state variables.
    """

    _cached_runtimes = None

    PROGRESS_THROTTLE_SEC = 0.15
    THUMBNAIL_SIZE = (160, 120)

    # yt-dlp groups these as Chromium-based. On Windows their cookie
    # stores are sealed by App-Bound Encryption and cannot be decrypted
    # at all (yt-dlp issue 10927), so a browser cookie fetch there fails
    # outright rather than returning less. Used ONLY to word a message;
    # nothing is blocked on it, because this is yt-dlp's limitation to
    # lift and a blocklist here would outlive the fix silently.
    CHROMIUM_BROWSERS = frozenset(
        ("brave", "chrome", "chromium", "edge", "opera", "vivaldi", "whale"))

    RESOLUTION_RANGES = {
        "480p": (0, 480),
        "720p": (481, 720),
        "1080p": (721, 1080),
        "1440p": (1081, 1440),
        "4K+": (1441, float('inf')),
    }

    @classmethod
    def _ensure_runtime_cache(cls):
        """Populate the JS runtime cache if not already done.

        Entries are yt-dlp --js-runtimes values: a bare name for a runtime on
        PATH, or "name:path" for the copy bundled inside a packaged build.

        Order carries no meaning here. --js-runtimes only ENABLES a runtime;
        yt-dlp picks by its own priority (deno > node > quickjs > bun) among
        the ones enabled and available. Each entry is passed as its own flag
        by _get_base_cmd.
        """
        if cls._cached_runtimes is None:
            runtimes = []
            bundled = find_jsruntime()
            if bundled:
                name, path = bundled
                runtimes.append(f"{name}:{path}")
            runtimes.extend(
                r for r in ("deno", "node", "quickjs", "bun") if shutil.which(r)
            )
            cls._cached_runtimes = runtimes

    @classmethod
    def _has_any_runtime(cls):
        """True when any JS runtime is available, bundled or on PATH."""
        cls._ensure_runtime_cache()
        return bool(cls._cached_runtimes)

    @staticmethod
    def _is_valid_url(url):
        """Check that URL uses a safe scheme (http/https) or is a search query"""
        if not url:
            return False
        if re.match(r'^ytsearch\w*:', url):
            return True
        return url.startswith("http://") or url.startswith("https://")

    def _get_base_cmd(self):
        """Build the base yt-dlp command with JS runtime + ffmpeg detection."""
        cmd = [find_ytdlp(), "--ignore-config", "--remote-components", "ejs:github"]
        ffmpeg = find_ffmpeg()
        if ffmpeg:
            cmd.extend(["--ffmpeg-location", ffmpeg])
        self._ensure_runtime_cache()
        # One flag per runtime. --js-runtimes takes a single RUNTIME[:PATH]
        # and is repeatable; a comma-joined list is read as ONE runtime with
        # a nonsense path, which leaves yt-dlp with no JS runtime at all and
        # silently drops every format behind YouTube's n challenge.
        for runtime in self._cached_runtimes:
            cmd.extend(["--js-runtimes", runtime])
        return cmd

    def _get_cookie_args(self):
        """Get the appropriate cookie arguments for yt-dlp.

        A cookie source this session has already proved unreadable is
        dropped. Without that, a fetch could recover by retrying without
        cookies and the download that followed would rebuild the same
        failing arguments and die -- which is worse than not offering the
        source at all, because the format list looks healthy first.

        Keyed on the arguments themselves rather than on a flag, so
        choosing a different browser is tried afresh with no reset step.
        """
        cookies_file = self.cookies_file_var.get().strip()
        browser = self.browser_var.get()
        args = get_cookie_args(cookies_file, browser)
        if args and args == self.failed_cookie_args:
            return []
        return args

    def _extract_browser_cookies(self):
        """Extract cookies and update the cookies_file_var"""
        browser = self.browser_var.get()
        cookies_out = os.path.join(self.script_dir, "cookies.txt")
        result = extract_browser_cookies(browser, cookies_out)
        if result:
            self.cookies_file_var.set(result)
        return result

    def check_nodejs(self):
        """Warn only if NO JavaScript runtime is available at all.

        A packaged build bundles QuickJS, so this should never fire there. It
        previously fired whenever deno/node were absent, which meant every
        release nagged the user to install Node.js even though a working
        runtime was shipped inside the app.
        """
        if not self._has_any_runtime():
            self._warn_no_jsruntime()

    def _warn_no_jsruntime(self):
        """Show warning about missing JavaScript runtime."""
        self.status_var.set("No JS runtime found - required for YouTube downloads")
        if is_windows():
            body = (
                "No JavaScript runtime found.\n\n"
                "YouTube needs one to solve download challenges.\n\n"
                "Downloaded releases of Snatch include one, so if you are\n"
                "seeing this you are running from source. Install Node.js\n"
                "from https://nodejs.org/ (the LTS installer is fine), then\n"
                "restart this app."
            )
        else:
            body = (
                "No JavaScript runtime found.\n\n"
                "YouTube needs one to solve download challenges. Downloaded\n"
                "releases of Snatch include one, so if you are seeing this\n"
                "you are running from source.\n\n"
                "Install Deno (recommended):\n"
                "curl -fsSL https://deno.land/install.sh | sh\n\n"
                "Or install Node.js:\n"
                "sudo apt install nodejs\n\n"
                "Then restart this app."
            )
        messagebox.showwarning("JavaScript Runtime Required", body)

    # ── Format fetching ─────────────────────────────────────────────

    def fetch_formats(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Warning", "Please enter a video URL")
            return
        if not self._is_valid_url(url):
            messagebox.showwarning("Warning", "Please enter a valid HTTP/HTTPS URL")
            return

        clear_treeview(self.format_tree)
        self.formats = []
        self._hide_playlist()

        self.preview_title_var.set("")
        self.preview_uploader_var.set("")
        self.preview_duration_var.set("")
        self.thumb_label.config(image="", text="Loading...")
        self.video_thumbnail = None

        self.status_var.set("Fetching available formats...")
        self.progress_var.set(0)
        self.progress_bar.config(mode="indeterminate")
        self.progress_bar.start(15)

        thread = threading.Thread(target=self._fetch_formats_thread, args=(url,))
        thread.daemon = True
        thread.start()

    def _probe_formats(self, url, cookie_args):
        """Dump one URL's metadata as JSON with the given cookie arguments.

        --ignore-no-formats-error is what keeps a probe alive: -J still runs
        yt-dlp's default format selection, so a video the site answers with
        audio-only streams aborts the whole dump with "Requested format is
        not available" and the user sees no formats at all rather than the
        audio ones that do exist.

        Warnings are deliberately NOT suppressed. A failed JS challenge is
        reported by yt-dlp as a warning -- it still exits 0 and still
        returns a payload, just without the video formats -- so
        --no-warnings threw away the only account of why they were gone.
        """
        cmd = self._get_base_cmd()
        cmd.extend(cookie_args)
        cmd.extend(["-J", "--ignore-no-formats-error", "--", url])
        return subprocess.run(cmd, capture_output=True, text=True, timeout=60)

    @staticmethod
    def _has_video_format(data):
        """True if a -J payload offers at least one format carrying video."""
        return any(fmt.get("vcodec", "none") != "none"
                   for fmt in (data.get("formats") or []))

    def _cookie_failure_note(self):
        """Word the note for cookies the app tried, failed on, and skipped.

        The browser name only chooses the sentence. It decides nothing:
        the retry that produced this note was keyed on the exit code, so
        an unrecognised browser still recovers and still gets told.
        """
        browser = self.browser_var.get()
        if is_windows() and browser in self.CHROMIUM_BROWSERS:
            return (f" {browser.capitalize()} cookies cannot be read on "
                    "Windows, so they were skipped. Firefox is not affected.")
        return " Cookies could not be read, so they were skipped."

    @staticmethod
    def _no_video_note(stderr):
        """Say that nothing carrying video came back, and why when known.

        Triggered by the observable -- a payload with no video format --
        and never by yt-dlp's wording, because the source may genuinely
        offer audio only. yt-dlp's text merely SHARPENS the sentence, so
        a reworded release costs the detail and not the warning.
        """
        if "solving failed" in (stderr or "").lower():
            return (" No video formats came back: the site's JavaScript "
                    "challenge failed, so only audio is listed.")
        return (" No video formats came back, so only audio is listed. "
                "If you expected video, try again in a moment.")

    def _fetch_formats_thread(self, url):
        try:
            self.cookie_fallback_used = False
            self.fetch_notes = []
            cookie_args = self._get_cookie_args()
            cookies_requested = bool(cookie_args)

            self.root.after(0, lambda: self.status_var.set("Fetching formats..."))

            result = self._probe_formats(url, cookie_args)

            # A cookied probe that fails OUTRIGHT used to skip the
            # fallback below, which sits behind the success path -- and
            # an outright failure is precisely what Windows produces,
            # where Chromium cookie stores cannot be decrypted at all.
            # Retry without cookies before reporting anything. Keyed on
            # the exit code and on whether cookies were sent, so no
            # rewording of yt-dlp's errors can stop it firing.
            if result.returncode != 0 and cookie_args:
                self.root.after(0, lambda: self.status_var.set(
                    "Cookies failed - retrying without them..."))
                try:
                    retry = self._probe_formats(url, [])
                    if retry.returncode == 0:
                        self.failed_cookie_args = list(cookie_args)
                        result = retry
                        cookie_args = []
                        self.cookie_fallback_used = True
                        self.fetch_notes.append(self._cookie_failure_note())
                except subprocess.TimeoutExpired:
                    pass  # Report the original failure below.

            if result.returncode != 0:
                error_msg = result.stderr
                # Only a MISSING runtime is fatal. A challenge that fails
                # with a runtime present is a warning and exits 0, so it
                # cannot be why this run failed -- and since warnings are
                # no longer suppressed, testing for it here would blame
                # the runtime for an unrelated failure. That case is now
                # reported from the success path instead.
                if "JavaScript runtime" in error_msg:
                    self.root.after(0, lambda: self._show_error(
                        "YouTube JS challenge failed.\n\n"
                        "Install Deno (recommended):\n"
                        "curl -fsSL https://deno.land/install.sh | sh\n\n"
                        "Or install Node.js:\n"
                        "sudo apt install nodejs\n\n"
                        "Then restart this app and try again."
                    ))
                else:
                    # There is no stable phrase to test for an age gate or
                    # a sign-in wall: yt-dlp relays whatever the site said.
                    # So the hint is keyed on what this app already knows
                    # -- the fetch failed and no cookie source was set --
                    # which covers age gates, sign-in walls and bot checks
                    # alike and cannot rot when yt-dlp rewords an error.
                    hint = "" if cookies_requested else (
                        "\n\nIf this video is age-restricted or asks you to "
                        "sign in, choose your browser next to 'Cookies' and "
                        "try again."
                    )
                    self.root.after(0, lambda e=error_msg, h=hint:
                                    self._show_error(f"Error fetching formats:\n{e}{h}"))
                return

            data = json.loads(result.stdout)
            probe_stderr = result.stderr

            # YouTube answers some cookied requests with audio-only streams,
            # which reads as "this video has no video". The cookies are worth
            # nothing here, so probe once more without them and keep whichever
            # answer actually carries video.
            if (cookie_args and "entries" not in data
                    and data.get("_type") != "playlist"
                    and not self._has_video_format(data)):
                self.root.after(0, lambda: self.status_var.set(
                    "No video formats with cookies — retrying without them..."))
                try:
                    retry = self._probe_formats(url, [])
                    if retry.returncode == 0:
                        retry_data = json.loads(retry.stdout)
                        if self._has_video_format(retry_data):
                            del data
                            data = retry_data
                            probe_stderr = retry.stderr
                            self.cookie_fallback_used = True
                            self.fetch_notes.append(
                                " Cookies returned audio only, so they were"
                                " skipped.")
                except (subprocess.TimeoutExpired, json.JSONDecodeError):
                    pass  # Keep the cookied answer; it is all we have.

            # A failed JS challenge is a WARNING in yt-dlp: it exits 0 and
            # simply leaves the video formats out, so a stripped answer was
            # indistinguishable from a complete one and the user was shown
            # audio and storyboards with nothing said. The trigger is the
            # observable -- a non-playlist payload carrying no video at all
            # -- so it holds however yt-dlp words the warning, and it stays
            # honest about a source that really does offer audio only.
            if ("entries" not in data and data.get("_type") != "playlist"
                    and not self._has_video_format(data)):
                self.fetch_notes.append(self._no_video_note(probe_stderr))

            title = data.get("title", "")
            uploader = data.get("uploader", data.get("channel", ""))
            duration = data.get("duration")
            thumbnail_url = data.get("thumbnail", "")

            self.video_title = title
            self.last_download_title = title

            dur_str = f"Duration: {format_duration(duration)}" if duration else ""

            self.root.after(0, lambda: self.preview_title_var.set(title))
            self.root.after(0, lambda: self.preview_uploader_var.set(uploader))
            self.root.after(0, lambda: self.preview_duration_var.set(dur_str))

            if thumbnail_url and HAS_PIL and thumbnail_url.startswith("https://"):
                try:
                    req = urllib.request.Request(thumbnail_url,
                                                headers={"User-Agent": "Snatch"})
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        img_data = resp.read()
                    img = Image.open(BytesIO(img_data))
                    img.thumbnail(self.THUMBNAIL_SIZE, Image.LANCZOS)
                    photo = ImageTk.PhotoImage(img)
                    img.close()  # Release PIL image after converting to PhotoImage
                    del img_data  # Free raw image bytes
                    # Release old PhotoImage reference before assigning new
                    old_thumb = self.video_thumbnail
                    self.video_thumbnail = photo
                    del old_thumb
                    self.root.after(0, lambda: self.thumb_label.config(
                        image=self.video_thumbnail, text=""))
                except Exception:
                    log.debug("Thumbnail could not be decoded", exc_info=True)
                    self.root.after(0, lambda: self.thumb_label.config(
                        image="", text="No thumbnail"))

            if data.get("_type") == "playlist" or "entries" in data:
                entries = data.get("entries", [])
                if entries:
                    del data  # Free large JSON before scheduling UI updates
                    pl_title = title or "Playlist"
                    self.root.after(0, lambda: self._show_playlist(entries, pl_title))
                    self.root.after(0, self._stop_indeterminate)
                    self.root.after(0, lambda: self.status_var.set(
                        f"Playlist: {len(entries)} videos found"))
                    return

            formats = data.get("formats", [])
            del data  # Free large JSON — extracted fields are kept above
            self.formats = []
            for fmt in formats:
                format_id = fmt.get("format_id", "N/A")
                ext = fmt.get("ext", "N/A")

                width = fmt.get("width")
                height = fmt.get("height")
                if width and height:
                    resolution = f"{width}x{height}"
                else:
                    resolution = fmt.get("resolution", "audio only")

                fps = fmt.get("fps", "")
                if fps:
                    fps = f"{int(fps)}"

                filesize = fmt.get("filesize") or fmt.get("filesize_approx")
                size_str = format_filesize(filesize)

                vcodec = fmt.get("vcodec", "none")
                acodec = fmt.get("acodec", "none")
                if vcodec == "none":
                    note = f"Audio: {acodec}"
                elif acodec == "none":
                    note = f"Video: {vcodec}"
                else:
                    note = f"V: {vcodec}, A: {acodec}"

                # Pre-compute type flags and parsed height for filtering.
                #
                # There are FOUR cases, not three. A format carrying neither
                # stream -- vcodec "none" AND acodec "none" -- is not media at
                # all: yt-dlp emits these on essentially every YouTube video
                # as the sb0/sb1 storyboard sheets, ext mhtml. Both flags below
                # come out False for it, which used to read as "muxed", so it
                # was tagged [V+A], labelled "Audio: none", kept by the
                # Video+Audio filter, and -- because it carries width and
                # height -- filed into a resolution bucket. A user filtering to
                # Video+Audio / 480p was offered a sheet of thumbnails
                # presented as video, and downloading it reported success.
                is_media = not (vcodec == "none" and acodec == "none")
                if not is_media:
                    continue
                is_video_only = vcodec != "none" and acodec == "none"
                is_audio_only = vcodec == "none" and acodec != "none"
                parsed_height = None
                if resolution and resolution != "audio only":
                    parts = resolution.split("x")
                    if len(parts) == 2:
                        try:
                            parsed_height = int(parts[1])
                        except ValueError:
                            pass

                self.formats.append({
                    "format_id": format_id,
                    "ext": ext,
                    "resolution": resolution,
                    "fps": fps,
                    "filesize": size_str,
                    "note": note,
                    "vcodec": vcodec,
                    "acodec": acodec,
                    "video_only": is_video_only,
                    "audio_only": is_audio_only,
                    "height": parsed_height,
                })

            self.root.after(0, self._update_format_list)

        except subprocess.TimeoutExpired:
            self.root.after(0, lambda: self._show_error("Timeout while fetching formats"))
        except json.JSONDecodeError as e:
            log.warning("yt-dlp returned unparseable format data", exc_info=True)
            self.root.after(0, lambda e=e: self._show_error(f"Error parsing format data: {e}"))
        except Exception as e:
            log.exception("Fetching formats failed")
            self.root.after(0, lambda e=e: self._show_error(f"Error: {e}"))

    def _stop_indeterminate(self):
        """Stop indeterminate progress bar and reset to determinate mode"""
        self.progress_bar.stop()
        self.progress_bar.config(mode="determinate")
        self.progress_var.set(0)

    def _update_format_list(self):
        self._stop_indeterminate()
        self._populate_filter_options()
        self._apply_filters()
        self._auto_select_preferred()
        note = "".join(self.fetch_notes)
        self.status_var.set(
            f"Found {len(self.formats)} formats. "
            f"Video-only formats will auto-merge with best audio.{note}")

    def _show_error(self, message):
        self._stop_indeterminate()
        self.status_var.set("Error")
        messagebox.showerror("Error", message)

    # ── Format filtering ────────────────────────────────────────────

    def _populate_filter_options(self):
        """Populate filter dropdowns from fetched formats"""
        resolutions = set()
        extensions = set()
        for fmt in self.formats:
            h = fmt.get("height")
            if h is not None:
                if h <= 480:
                    resolutions.add("480p")
                elif h <= 720:
                    resolutions.add("720p")
                elif h <= 1080:
                    resolutions.add("1080p")
                elif h <= 1440:
                    resolutions.add("1440p")
                else:
                    resolutions.add("4K+")
            ext = fmt.get("ext", "")
            if ext and ext != "N/A":
                extensions.add(ext)

        res_vals = ["All"] + sorted(resolutions,
                                    key=lambda x: {"480p": 1, "720p": 2, "1080p": 3,
                                                   "1440p": 4, "4K+": 5}.get(x, 6))
        ext_vals = ["All"] + sorted(extensions)

        self.filter_res_combo.config(values=res_vals)
        self.filter_ext_combo.config(values=ext_vals)

        self.filter_res_var.set("All")
        self.filter_type_var.set("All")
        self.filter_ext_var.set("All")

    def _apply_filters(self):
        """Filter the format treeview based on dropdown selections"""
        res_filter = self.filter_res_var.get()
        type_filter = self.filter_type_var.get()
        ext_filter = self.filter_ext_var.get()

        clear_treeview(self.format_tree)

        for fmt in self.formats:
            is_video_only = fmt["video_only"]
            is_audio_only = fmt["audio_only"]

            if type_filter == "Video+Audio" and (is_video_only or is_audio_only):
                continue
            if type_filter == "Video Only" and not is_video_only:
                continue
            if type_filter == "Audio Only" and not is_audio_only:
                continue

            if ext_filter != "All" and fmt.get("ext", "") != ext_filter:
                continue

            if res_filter != "All":
                h = fmt.get("height")
                if h is None:
                    continue
                lo, hi = self.RESOLUTION_RANGES.get(res_filter, (0, float('inf')))
                if not (lo <= h <= hi):
                    continue

            note = fmt["note"]
            if is_video_only:
                note = "[VIDEO ONLY] " + note
                tag = "video_only"
            elif is_audio_only:
                note = "[AUDIO ONLY] " + note
                tag = "audio_only"
            else:
                note = "[V+A] " + note
                tag = "muxed"

            self.format_tree.insert("", tk.END, values=(
                fmt["format_id"],
                fmt["ext"],
                fmt["resolution"],
                fmt["fps"],
                fmt["filesize"],
                note
            ), tags=(tag,))

    def _auto_select_preferred(self):
        """Auto-select the preferred resolution+ext in the format treeview"""
        if not self.preferred_resolution or not self.preferred_ext:
            return
        for item_id in self.format_tree.get_children():
            vals = self.format_tree.item(item_id, "values")
            if len(vals) >= 3:
                if str(vals[2]) == self.preferred_resolution and str(vals[1]) == self.preferred_ext:
                    self.format_tree.selection_set(item_id)
                    self.format_tree.see(item_id)
                    return

    def _preferred_format_spec(self):
        """Build a yt-dlp format selector from the saved resolution/ext preference.

        A queue item is a different video, so a stored format_id means nothing
        to it — the preference has to be re-expressed as a selector yt-dlp
        resolves per video. Returns (format_spec, merge), falling back to
        ("best", False) when nothing usable is stored.
        """
        height = None
        if self.preferred_resolution and "x" in self.preferred_resolution:
            try:
                height = int(self.preferred_resolution.split("x")[1])
            except ValueError:
                height = None

        ext = self.preferred_ext
        if not ext or not ext.isalnum():
            ext = None

        if height is None and ext is None:
            return "best", False

        h_filter = f"[height<={height}]" if height else ""
        e_filter = f"[ext={ext}]" if ext else ""

        # Widest match first, degrading to plain "best" so an unusual
        # preference never leaves a queue item with nothing to download.
        candidates = [
            f"bestvideo{h_filter}{e_filter}+bestaudio",
            f"best{h_filter}{e_filter}",
            f"bestvideo{h_filter}+bestaudio",
            f"best{h_filter}",
            "best",
        ]
        return "/".join(dict.fromkeys(candidates)), True

    # ── Download ────────────────────────────────────────────────────

    def download_selected(self):
        selection = self.format_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a format to download")
            return

        item = self.format_tree.item(selection[0])
        format_id = str(item["values"][0])

        fmt_data = None
        for fmt in self.formats:
            if str(fmt["format_id"]) == format_id:
                fmt_data = fmt
                break

        is_video_only = fmt_data and fmt_data.get("video_only", False)
        merge_on = self.merge_audio_var.get() == 1

        if fmt_data:
            self.preferred_resolution = fmt_data.get("resolution", "")
            self.preferred_ext = fmt_data.get("ext", "")
            self.last_download_format = f"{fmt_data.get('resolution', '')} {fmt_data.get('ext', '')}"

        if is_video_only and merge_on:
            format_spec = f"{format_id}+bestaudio"
            self.status_var.set(f"Downloading {format_id} + best audio (merging)...")
            self._start_download(format_spec, merge=True)
        elif is_video_only and not merge_on:
            self.status_var.set(f"Downloading {format_id} (video only, no audio merge)")
            self._start_download(format_id)
        else:
            self._start_download(format_id)

    def quick_download(self, format_spec, audio_only=False, merge=False):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Warning", "Please enter a video URL")
            return
        self.last_download_format = format_spec[:30]
        self._start_download(format_spec, audio_only=audio_only, merge=merge)

    def _start_download(self, format_spec, audio_only=False, merge=False,
                        queue_mode=False, history_title=None, history_format=None):
        # The disabled download_btn is not the control it looks like:
        # app.py binds <Control-d> to download_selected regardless of widget
        # state, and the Quick Select buttons are never stored on self and so
        # are never disabled. Without this, a second download overwrote
        # self.download_process and the two threads then closed each other's
        # pipes. _process_queue already guards; this did not.
        if self.is_downloading and not queue_mode:
            messagebox.showwarning("Busy", "A download is already in progress")
            return

        url = self.url_var.get().strip()
        save_path = self.save_path_var.get().strip()

        if not url:
            messagebox.showwarning("Warning", "Please enter a video URL")
            return
        if not self._is_valid_url(url):
            messagebox.showwarning("Warning", "Please enter a valid HTTP/HTTPS URL")
            return
        if not save_path:
            messagebox.showwarning("Warning", "Please select a save location")
            return
        if not os.path.isdir(save_path):
            messagebox.showerror("Error", "Save location does not exist")
            return

        self.is_downloading = True
        self.download_btn.config(state=tk.DISABLED)
        self.cancel_btn.config(state=tk.NORMAL)
        self.open_folder_btn.pack_forget()
        self.progress_var.set(0)
        self.status_var.set("Starting download...")

        thread = threading.Thread(
            target=self._download_thread,
            args=(url, save_path, format_spec, audio_only, merge, queue_mode,
                  history_title, history_format))
        thread.daemon = True
        thread.start()

    def _download_thread(self, url, save_path, format_spec, audio_only=False,
                         merge=False, queue_mode=False, history_title=None,
                         history_format=None):
        try:
            cmd = self._get_base_cmd()
            cmd.extend(self._get_cookie_args())

            cmd.extend([
                "-f", format_spec,
                "-o", os.path.join(save_path, "%(title)s.%(ext)s"),
                "--newline",
                "--progress"
            ])

            if audio_only:
                cmd.extend(["-x", "--audio-format", "mp3"])

            if merge:
                cmd.extend(["--merge-output-format", "mp4"])

            if self.subtitle_var.get() == 1:
                cmd.extend(["--write-sub", "--write-auto-sub", "--sub-lang", "en"])

            if self.sponsorblock_var.get() == 1:
                cmd.extend(["--sponsorblock-remove", "all"])

            speed = self.speed_limit_var.get()
            if speed and speed != "Unlimited":
                cmd.extend(["--limit-rate", speed])

            cmd.extend(["--", url])

            # Bound to a local as well as to self. self.download_process is
            # what cancel_download reaches, and _reset_ui sets it to None --
            # which used to land between this thread's pipe close and its
            # wait(), raising AttributeError into the handler below and
            # popping "'NoneType' object has no attribute 'wait'" at a user
            # who had just pressed Escape. The local is this thread's own
            # handle and cannot be nulled or replaced underneath it.
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            self.download_process = proc

            try:
                # Throttle UI updates to avoid flooding the event loop
                last_ui_update = 0
                pending_progress = None
                pending_status = None

                for line in proc.stdout:
                    if not self.is_downloading:
                        break

                    line = line.strip()

                    progress_match = re.search(r'\[download\]\s+(\d+\.?\d*)%', line)
                    if progress_match:
                        pending_progress = float(progress_match.group(1))

                    if "[Merger]" in line or "[ExtractAudio]" in line:
                        self.root.after(0, self._show_merge_progress)
                        self.root.after(0, lambda: self._update_title_progress(text="Merging..."))
                        last_ui_update = time.monotonic()
                        pending_progress = None
                        pending_status = None
                        continue

                    if line and not line.startswith('[debug]'):
                        pending_status = line[:80]

                    # Flush pending updates at most every 150ms
                    now = time.monotonic()
                    if (pending_progress is not None or pending_status is not None) and now - last_ui_update >= self.PROGRESS_THROTTLE_SEC:
                        if pending_progress is not None:
                            p = pending_progress
                            self.root.after(0, lambda p=p: self.progress_var.set(p))
                            self.root.after(0, lambda p=p: self._update_title_progress(percent=p))
                            pending_progress = None
                        if pending_status is not None:
                            s = pending_status
                            self.root.after(0, lambda s=s: self.status_var.set(s))
                            pending_status = None
                        last_ui_update = now

                # Flush any remaining updates -- but not on the cancel path.
                # The loop also exits by `break` when is_downloading goes
                # false, and these after() callbacks would then land AFTER
                # cancel_download had written "Download cancelled" and zeroed
                # the bar, leaving a stale percentage on screen.
                if self.is_downloading and pending_progress is not None:
                    p = pending_progress
                    self.root.after(0, lambda p=p: self.progress_var.set(p))
                    self.root.after(0, lambda p=p: self._update_title_progress(percent=p))
                if self.is_downloading and pending_status is not None:
                    s = pending_status
                    self.root.after(0, lambda s=s: self.status_var.set(s))
            finally:
                # Always close the stdout pipe to release the file descriptor
                try:
                    proc.stdout.close()
                except Exception:
                    log.debug("Closing the yt-dlp stdout pipe failed",
                              exc_info=True)

            proc.wait()

            if self.is_downloading and proc.returncode == 0:
                self.last_download_path = save_path
                self.root.after(0, lambda: self._download_complete(
                    queue_mode, history_title, history_format))
            elif self.is_downloading:
                if queue_mode:
                    self.root.after(0, lambda: self._queue_item_failed())
                else:
                    self.root.after(0, lambda: self._show_error("Download failed"))
                    self.root.after(0, self._reset_ui)
                    self.root.after(0, self._update_title_progress)

        except Exception as e:
            log.exception("Download failed")
            self.root.after(0, lambda e=e: self._show_error(f"Download error: {e}"))
            self.root.after(0, self._reset_ui)
            self.root.after(0, self._update_title_progress)

    def _show_merge_progress(self):
        """Switch to indeterminate progress for merge/extract phase"""
        self.progress_bar.config(mode="indeterminate")
        self.progress_bar.start(15)
        self.status_var.set("Merging audio and video...")

    def _download_complete(self, queue_mode=False, history_title=None,
                           history_format=None):
        self._stop_indeterminate()
        self.progress_var.set(100)
        self.status_var.set("Download complete!")
        self._update_title_progress()

        # Prefer what this download was started with. Reading the two
        # session-global attributes instead meant every QUEUED download wrote
        # a record describing a different video: _process_next_queue_item
        # calls _start_download directly and sets neither, so history.json
        # recorded the last FETCHED title and the last MANUALLY CHOSEN format
        # for each queue item -- or an empty title for a session that queued
        # without fetching. The queue entry has always carried the right
        # title; it was simply discarded.
        self._add_history_entry(
            history_title or self.last_download_title or self.video_title,
            self.url_var.get().strip(),
            history_format or self.last_download_format,
            self.last_download_path
        )

        self.open_folder_btn.pack(side=tk.LEFT, padx=(10, 0))

        if queue_mode:
            if self.queue_index < len(self.download_queue):
                self.download_queue[self.queue_index]["status"] = "Done"
                self._refresh_queue_tree()
            self.queue_index += 1
            self._reset_ui()
            self.root.after(500, self._process_next_queue_item)
        else:
            messagebox.showinfo("Success", "Download completed successfully!")
            self._reset_ui()

    def _queue_item_failed(self):
        """Handle a failed queue item"""
        if self.queue_index < len(self.download_queue):
            self.download_queue[self.queue_index]["status"] = "Failed"
            self._refresh_queue_tree()
        self.queue_index += 1
        self._reset_ui()
        self.root.after(500, self._process_next_queue_item)

    def _reset_ui(self):
        self.is_downloading = False
        self.download_btn.config(state=tk.NORMAL)
        self.cancel_btn.config(state=tk.DISABLED)
        self.download_process = None

    def cancel_download(self):
        if self.download_process:
            self.is_downloading = False
            self.is_processing_queue = False
            try:
                self.download_process.terminate()
                try:
                    self.download_process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self.download_process.kill()
                    self.download_process.wait(timeout=2)
            except Exception:
                log.debug("Tearing down the yt-dlp process on cancel failed",
                          exc_info=True)
            self.status_var.set("Download cancelled")
            self._stop_indeterminate()
            self._update_title_progress()
            self._reset_ui()

    # ── Queue ───────────────────────────────────────────────────────

    def _add_to_queue(self):
        """Add current URL to the download queue"""
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Warning", "Please enter a URL to add to queue")
            return
        if not self._is_valid_url(url):
            messagebox.showwarning("Warning", "Please enter a valid HTTP/HTTPS URL")
            return
        self.download_queue.append({"url": url, "status": "Pending", "title": url[:60]})
        self._refresh_queue_tree()
        self.url_var.set("")

    def _refresh_queue_tree(self):
        """Refresh the queue treeview display"""
        clear_treeview(self.queue_tree)
        for i, entry in enumerate(self.download_queue, 1):
            self.queue_tree.insert("", tk.END, values=(
                i,
                entry["url"][:70],
                entry["status"]
            ))
        self.queue_status_label.config(text=f"{len(self.download_queue)} items in queue")

    def _clear_queue(self):
        """Clear the download queue"""
        self.download_queue = []
        self._refresh_queue_tree()

    def _process_queue(self):
        """Download all queued items sequentially using preferred format"""
        if not self.download_queue:
            messagebox.showinfo("Queue Empty", "No items in the download queue")
            return
        if self.is_downloading:
            messagebox.showwarning("Busy", "A download is already in progress")
            return

        self.is_processing_queue = True
        self.queue_index = 0
        self._process_next_queue_item()

    def _process_next_queue_item(self):
        """Process the next item in the queue"""
        if self.queue_index >= len(self.download_queue):
            self.is_processing_queue = False
            self.status_var.set("Queue complete!")
            messagebox.showinfo("Queue Complete", "All queued downloads finished!")
            return

        entry = self.download_queue[self.queue_index]
        entry["status"] = "Downloading"
        self._refresh_queue_tree()

        total = len(self.download_queue)
        self.status_var.set(f"Downloading {self.queue_index + 1} of {total}...")
        self.url_var.set(entry["url"])

        format_spec, merge = self._preferred_format_spec()
        self._start_download(format_spec, merge=merge, queue_mode=True,
                             history_title=entry.get("title"),
                             history_format=format_spec)

    # ── Playlist ────────────────────────────────────────────────────

    def _show_playlist(self, entries, title):
        """Display playlist entries in the playlist treeview"""
        self.is_playlist = True
        self.playlist_entries = entries
        self.playlist_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 12),
                                 after=self.format_tree.master)

        clear_treeview(self.playlist_tree)

        for i, entry in enumerate(entries, 1):
            dur_str = format_duration(entry.get("duration"))
            etitle = entry.get("title", entry.get("url", f"Video {i}"))
            self.playlist_tree.insert("", tk.END, iid=str(i),
                                      values=("[x]", i, etitle, dur_str))

        self.preview_title_var.set(f"Playlist: {title}")
        self.preview_uploader_var.set(f"{len(entries)} videos")
        self.preview_duration_var.set("")

    def _hide_playlist(self):
        """Hide the playlist section"""
        self.is_playlist = False
        self.playlist_entries = []
        self.playlist_frame.pack_forget()

    def _toggle_playlist_select(self, event):
        """Toggle selection checkbox on click"""
        region = self.playlist_tree.identify_region(event.x, event.y)
        if region != "cell":
            return
        col = self.playlist_tree.identify_column(event.x)
        if col != "#1":
            return
        item_id = self.playlist_tree.identify_row(event.y)
        if not item_id:
            return
        vals = list(self.playlist_tree.item(item_id, "values"))
        vals[0] = "[ ]" if vals[0] == "[x]" else "[x]"
        self.playlist_tree.item(item_id, values=vals)

    def _playlist_select_all(self):
        for item_id in self.playlist_tree.get_children():
            vals = list(self.playlist_tree.item(item_id, "values"))
            vals[0] = "[x]"
            self.playlist_tree.item(item_id, values=vals)

    def _playlist_deselect_all(self):
        for item_id in self.playlist_tree.get_children():
            vals = list(self.playlist_tree.item(item_id, "values"))
            vals[0] = "[ ]"
            self.playlist_tree.item(item_id, values=vals)

    def _download_playlist_selected(self):
        """Add selected playlist videos to queue and process"""
        selected_indices = []
        for item_id in self.playlist_tree.get_children():
            vals = self.playlist_tree.item(item_id, "values")
            if vals[0] == "[x]":
                idx = int(vals[1]) - 1
                selected_indices.append(idx)

        if not selected_indices:
            messagebox.showinfo("Info", "No videos selected")
            return

        for idx in selected_indices:
            if idx < len(self.playlist_entries):
                entry = self.playlist_entries[idx]
                url = entry.get("url") or entry.get("webpage_url", "")
                title = entry.get("title", f"Video {idx + 1}")
                if url:
                    self.download_queue.append({
                        "url": url, "status": "Pending", "title": title[:60]
                    })

        self._refresh_queue_tree()
        messagebox.showinfo("Queued", f"Added {len(selected_indices)} videos to queue.\n"
                                      f"Click 'Download Queue' to start.")
