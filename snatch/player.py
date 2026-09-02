"""Embedded mpv player control via IPC socket"""

import os
import json
import socket
import subprocess
import tempfile

from .theme import get_theme
from .utils import format_duration
from .platform_utils import open_path, is_windows, is_macos, find_mpv, find_ytdlp
from .logging_setup import get_logger

log = get_logger(__name__)


def _no_player_message():
    """Explain how to get in-app playback, in terms of THIS platform.

    The embedded player shells out to mpv, which is not bundled. Snatch falls
    back to opening the video in the default browser. The advice here used to
    be "sudo apt install mpv" on every platform, which is wrong on Windows and
    macOS -- exactly the machines least likely to have mpv already.
    """
    if is_windows():
        return ("No in-app player.\n\n"
                "Snatch opened the video in your browser instead.\n\n"
                "For playback inside Snatch, install mpv from\n"
                "https://mpv.io/installation/ and restart the app.")
    if is_macos():
        return ("No in-app player.\n\n"
                "Snatch opened the video in your browser instead.\n\n"
                "For playback inside Snatch:\nbrew install mpv\n"
                "then restart the app.")
    return ("No in-app player.\n\n"
            "Snatch opened the video in your browser instead.\n\n"
            "For playback inside Snatch, install mpv:\n"
            "sudo zypper install mpv   (or apt/dnf/pacman)\n"
            "then restart the app.")


def _embedding_env():
    """Environment for the mpv child so --wid embedding actually works.

    On a Wayland session tkinter still runs under XWayland, so
    player_frame.winfo_id() is an X11 window id. mpv, seeing WAYLAND_DISPLAY,
    picks its Wayland backend instead -- which cannot embed into an X11 window
    -- and opens a SEPARATE window rather than playing inside the app.
    Reported on KDE Plasma Wayland 2026-08-19; Windows was unaffected because
    it has no such split.

    Dropping WAYLAND_DISPLAY for the child makes mpv fall back to X11 through
    XWayland, where --wid works. Only done when there is a DISPLAY to fall
    back to, so a pure-Wayland box with no XWayland is left alone rather than
    handed a broken environment.
    """
    env = os.environ.copy()
    if not is_windows() and not is_macos():
        if env.get("WAYLAND_DISPLAY") and env.get("DISPLAY"):
            env.pop("WAYLAND_DISPLAY", None)
    return env


class PlayerMixin:
    """Mixin providing embedded mpv player functionality.
    Expects the host class to have: root, player_frame, player_status_label,
    play_pause_btn, now_playing_var, player_time_var, seek_var, volume_var,
    cookies_file_var, mpv_process, mpv_socket_path, player_update_id,
    player_paused, _user_seeking, and _is_valid_url().
    """

    POLL_PLAYING_MS = 500
    POLL_PAUSED_MS = 1000
    SOCKET_RECV_CAP = 65536
    SOCKET_CHUNK_SIZE = 4096

    def _play_in_mpv(self, url, title=""):
        """Launch mpv embedded in the player frame"""
        from tkinter import messagebox

        if not url or not self._is_valid_url(url):
            messagebox.showwarning("Warning", "Invalid URL for playback")
            return

        # find_mpv() is the single authority on whether there is a player. The
        # old gate here read HAS_MPV, which is shutil.which("mpv") evaluated at
        # import — blind to the copy bundled inside a packaged build, so a
        # release shipping its own mpv would still have fallen back to a
        # browser.
        mpv_bin = find_mpv()
        if not mpv_bin:
            try:
                open_path(url)
            except Exception:
                log.warning("Handing %s to the system player failed",
                            url, exc_info=True)
                messagebox.showerror("Error", _no_player_message())
            return

        self._stop_player()

        runtime_dir = os.environ.get("XDG_RUNTIME_DIR", tempfile.gettempdir())
        # Validate the runtime dir is owned by us and not a symlink
        runtime_dir = os.path.realpath(runtime_dir)
        if is_windows() or not os.path.isdir(runtime_dir) or os.stat(runtime_dir).st_uid != os.getuid():
            runtime_dir = tempfile.gettempdir()
        self.mpv_socket_path = os.path.join(runtime_dir, f"snatch-mpv-{os.getpid()}")
        if os.path.exists(self.mpv_socket_path):
            os.unlink(self.mpv_socket_path)

        wid = str(self.player_frame.winfo_id())

        cmd = [
            mpv_bin,
            f"--wid={wid}",
            f"--input-ipc-server={self.mpv_socket_path}",
            "--keep-open=yes",
            "--force-window=yes",
            "--no-terminal",
            f"--volume={self.volume_var.get()}",
        ]

        # mpv resolves YouTube links with its OWN yt-dlp through ytdl_hook,
        # so it never sees the command this app builds. Without this it would
        # look for yt-dlp on PATH and find nothing on a clean machine, even
        # though the app ships one.
        ytdlp_bin = find_ytdlp()
        if ytdlp_bin and os.path.isfile(ytdlp_bin):
            cmd.append(f"--script-opts=ytdl_hook-ytdl_path={ytdlp_bin}")

        # Pass cookies to mpv's yt-dlp
        cookies_file = self.cookies_file_var.get().strip()
        if cookies_file and os.path.isfile(cookies_file):
            cmd.append(f"--ytdl-raw-options=cookies={cookies_file}")

        cmd.extend(["--", url])

        self.player_status_label.place_forget()
        self.now_playing_var.set(title[:50] if title else "")
        self.play_pause_btn.config(text="Pause")
        self.player_paused = False

        try:
            self.mpv_process = subprocess.Popen(
                cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                env=_embedding_env())
        except FileNotFoundError:
            self.player_status_label.config(text=_no_player_message())
            self.player_status_label.place(relx=0.5, rely=0.5, anchor="center")
            return

        self.root.after(1000, self._update_player_state)

    def _toggle_fullscreen(self):
        """Toggle the window between fullscreen and normal.

        The video is embedded in a Tk frame via --wid, so it cannot go
        fullscreen independently of the window that owns it -- mpv's own
        fullscreen is not available to an embedded surface. Making the window
        fullscreen grows the player frame with it (it packs with expand=True),
        and the embedded video follows the frame.

        Escape leaves fullscreen, which is what every player does and what a
        user will try first when the title bar is gone.
        """
        self._fullscreen = not getattr(self, "_fullscreen", False)
        self.root.attributes("-fullscreen", self._fullscreen)
        if hasattr(self, "fullscreen_btn"):
            self.fullscreen_btn.config(
                text="Exit Full" if self._fullscreen else "Fullscreen")
        if self._fullscreen:
            self.root.bind("<Escape>", lambda e: self._toggle_fullscreen())
        else:
            # Restore, do not unbind. root.unbind("<Escape>") removes EVERY
            # Escape binding, including app.py's cancel_download — which
            # STANDARDS.md section 9 documents as a shortcut. Nothing rebound
            # it, so one fullscreen round-trip silently and permanently killed
            # a shipped feature.
            self.root.bind("<Escape>", lambda e: self.cancel_download())

    @staticmethod
    def _ipc_supported():
        """True where this app can talk to mpv's IPC server.

        mpv's own options.rst: "On Windows, named pipes are used, so the path
        refers to the pipe namespace." So --input-ipc-server creates no
        filesystem object there, os.path.exists is False forever, and every
        _mpv_command returned None — leaving play/pause, volume, seek and the
        position readout inert on a platform this project builds and ships,
        silently, because the handler below swallows everything.

        Reaching Windows means a named-pipe client rather than AF_UNIX, which
        is a feature and not this fix. What this does is stop pretending: the
        controls are disabled with a visible reason instead of doing nothing.
        """
        return not is_windows() and hasattr(socket, "AF_UNIX")

    def _mpv_command(self, command):
        """Send a command to mpv via IPC socket and return response"""
        if not self._ipc_supported():
            return None
        if not self.mpv_socket_path or not os.path.exists(self.mpv_socket_path):
            return None
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            try:
                sock.settimeout(0.5)
                sock.connect(self.mpv_socket_path)
                msg = json.dumps({"command": command}) + "\n"
                sock.sendall(msg.encode())
                data = b""
                while len(data) < self.SOCKET_RECV_CAP:
                    try:
                        chunk = sock.recv(self.SOCKET_CHUNK_SIZE)
                        if not chunk:
                            break
                        data += chunk
                        if b"\n" in data:
                            break
                    except socket.timeout:
                        break
            finally:
                sock.close()
            if data:
                for line in data.decode().strip().split("\n"):
                    try:
                        resp = json.loads(line)
                        if "data" in resp:
                            return resp
                    except json.JSONDecodeError:
                        continue
            return None
        except Exception:
            log.debug("mpv IPC command failed", exc_info=True)
            return None

    def _mpv_get_property(self, prop):
        """Get a property value from mpv"""
        resp = self._mpv_command(["get_property", prop])
        if resp and "data" in resp:
            return resp["data"]
        return None

    def _mpv_set_property(self, prop, value):
        """Set a property in mpv"""
        self._mpv_command(["set_property", prop, value])

    def _toggle_play_pause(self):
        """Toggle play/pause on the embedded player"""
        if not self.mpv_process or self.mpv_process.poll() is not None:
            self._play_search_result()
            return
        self.player_paused = not self.player_paused
        self._mpv_set_property("pause", self.player_paused)
        self.play_pause_btn.config(text="Play" if self.player_paused else "Pause")

    def _stop_player(self):
        """Stop mpv and clean up"""
        if self.player_update_id:
            self.root.after_cancel(self.player_update_id)
            self.player_update_id = None

        if self.mpv_process:
            try:
                self.mpv_process.terminate()
                self.mpv_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.mpv_process.kill()
            except Exception:
                log.debug("Tearing down the mpv process failed", exc_info=True)
            self.mpv_process = None

        if self.mpv_socket_path and os.path.exists(self.mpv_socket_path):
            try:
                os.unlink(self.mpv_socket_path)
            except Exception:
                log.debug("Removing the mpv IPC socket %s failed",
                          self.mpv_socket_path, exc_info=True)

        self.player_paused = False
        self.play_pause_btn.config(text="Play")
        self.now_playing_var.set("")
        self.player_time_var.set("--:-- / --:--")
        self.seek_var.set(0)
        self.player_status_label.config(text="No video loaded",
                                        fg=get_theme().FG_DIM)
        self.player_status_label.place(relx=0.5, rely=0.5, anchor="center")

    def _on_volume_change(self, value):
        """Update mpv volume"""
        if self.mpv_process and self.mpv_process.poll() is None:
            self._mpv_set_property("volume", int(float(value)))

    def _on_seek_release(self, event):
        """Seek to position when user releases the seek bar"""
        self._user_seeking = False
        if self.mpv_process and self.mpv_process.poll() is None:
            duration = self._mpv_get_property("duration")
            if duration:
                position = self.seek_var.get() / 100 * duration
                self._mpv_command(["seek", position, "absolute"])

    def _update_player_state(self):
        """Poll mpv for position/duration and update the seek bar"""
        if not self.mpv_process or self.mpv_process.poll() is not None:
            if self.mpv_process and self.mpv_process.poll() is not None:
                self._stop_player()
            return

        pos = self._mpv_get_property("time-pos")
        dur = self._mpv_get_property("duration")

        if pos is not None and dur is not None and dur > 0:
            if not self._user_seeking:
                self.seek_var.set((pos / dur) * 100)

            self.player_time_var.set(
                f"{format_duration(pos)} / {format_duration(dur)}")

        interval = self.POLL_PAUSED_MS if self.player_paused else self.POLL_PLAYING_MS
        self.player_update_id = self.root.after(interval, self._update_player_state)
