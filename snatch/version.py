"""yt-dlp version checking and update logic"""

import os
import re
import json
import subprocess
import threading
import tkinter as tk
from tkinter import messagebox
import tempfile
import urllib.request

from .platform_utils import (find_ytdlp, is_windows, is_macos, is_frozen,
                             user_bin_dir, updated_ytdlp_path)

# yt-dlp's NIGHTLY channel, matching scripts/fetch-binaries.sh.
#
# The stable channel does NOT play YouTube (SNAT-0014): 1 in 5 videos played
# on the then-current stable, 5 in 5 on the nightly. So a self-update that
# pulled stable would be a downgrade wearing an upgrade's clothes -- and this
# module used to do exactly that, downloading yt-dlp/yt-dlp's latest release.
#
# Keep the repo and the asset names in step with fetch-binaries.sh, which
# pins the copy each release bundles. The two cannot share a definition
# across a shell script and a Python module, so they are kept honest by this
# comment and by the version check running against the same repo it downloads
# from.
YTDLP_NIGHTLY_REPO = "yt-dlp/yt-dlp-nightly-builds"
YTDLP_RELEASE_API = (
    f"https://api.github.com/repos/{YTDLP_NIGHTLY_REPO}/releases/latest")
YTDLP_DOWNLOAD_TIMEOUT = 180
YTDLP_PROBE_TIMEOUT = 30
YTDLP_CHUNK_BYTES = 256 * 1024
# yt-dlp's own binaries run ~30 MB. The cap only has to stop a redirect to
# something enormous from filling the user's disk.
YTDLP_MAX_BYTES = 128 * 1024 * 1024


def _ytdlp_asset_name():
    """Release asset for this platform, mirroring scripts/fetch-binaries.sh."""
    if is_windows():
        return "yt-dlp.exe"
    if is_macos():
        return "yt-dlp_macos"
    return "yt-dlp"


class VersionMixin:
    """Mixin providing yt-dlp version check and update functionality.
    Expects the host class to have: root, version_var, status_var,
    update_btn, current_version, latest_version.
    """

    def check_version(self):
        """Check current yt-dlp version and compare with latest"""
        thread = threading.Thread(target=self._check_version_thread)
        thread.daemon = True
        thread.start()

    def _check_version_thread(self):
        # Get current installed version
        try:
            result = subprocess.run([find_ytdlp(), "--version"], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                self.current_version = result.stdout.strip()
                self.root.after(0, lambda: self.version_var.set(f"v{self.current_version}"))
            else:
                self.root.after(0, lambda: self.version_var.set("Version unknown"))
                return
        except Exception:
            self.root.after(0, lambda: self.version_var.set("yt-dlp not found"))
            return

        # Check latest version from GitHub
        try:
            req = urllib.request.Request(YTDLP_RELEASE_API,
                                         headers={"User-Agent": "Snatch"})
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
                self.latest_version = data.get("tag_name", "").lstrip("v")
                del data  # Free API response JSON

                if self.latest_version and self.current_version:
                    if self._version_compare(self.latest_version, self.current_version) > 0:
                        self.root.after(0, self._show_update_available)
                    else:
                        self.root.after(0, self._refresh_idle_button)
        except Exception:
            self.root.after(0, lambda: self.update_btn.config(
                text="Check failed", state=tk.DISABLED))

    @staticmethod
    def _version_compare(v1, v2):
        """Compare version strings. Returns >0 if v1>v2, <0 if v1<v2, 0 if equal"""
        def normalize(v):
            return [int(x) for x in re.sub(r'[^\d.]', '', v).split('.')]

        try:
            parts1 = normalize(v1)
            parts2 = normalize(v2)

            for i in range(max(len(parts1), len(parts2))):
                p1 = parts1[i] if i < len(parts1) else 0
                p2 = parts2[i] if i < len(parts2) else 0
                if p1 > p2:
                    return 1
                elif p1 < p2:
                    return -1
            return 0
        except Exception:
            return (v1 > v2) - (v1 < v2)

    def _show_update_available(self):
        """Offer the newer nightly. Every platform can take it now (SNAT-0016).

        This used to show Windows a passive "download a new Snatch" label,
        because a packaged build could not replace its own bundled yt-dlp.
        It can: the download goes to user_bin_dir(), which is writable and
        outlives the process.
        """
        self.update_btn.config(text=f"Update to {self.latest_version}",
                               state=tk.NORMAL)
        self.status_var.set(
            f"Update available: {self.current_version} -> {self.latest_version}")
        self._prompt_update()

    def _refresh_idle_button(self):
        """Set the button for the nothing-to-update case.

        Offers the way back to the bundled copy whenever a fetched one is in
        use -- the escape hatch for a nightly that misbehaves. Packaged
        builds only: from source there is no separate bundled copy to revert
        to, because fetch-binaries.sh fills the very directory a fetched copy
        lands in.
        """
        if is_frozen() and updated_ytdlp_path():
            self.update_btn.config(text="Revert to bundled yt-dlp",
                                   state=tk.NORMAL)
        else:
            self.update_btn.config(text="Up to date", state=tk.DISABLED)

    def update_ytdlp(self):
        """Button action: fetch the newer nightly, or go back to the bundled copy.

        One button with two jobs, because which one is available is never
        ambiguous -- there is either something newer to fetch, or a fetched
        copy in use, and _refresh_idle_button() has already said which.
        """
        newer = (self.latest_version and self.current_version and
                 self._version_compare(self.latest_version,
                                       self.current_version) > 0)
        if newer:
            self._prompt_update()
        elif is_frozen() and updated_ytdlp_path():
            self._prompt_revert()

    def _prompt_update(self):
        if not self.latest_version:
            return
        if messagebox.askyesno(
                "Update yt-dlp",
                f"Download yt-dlp {self.latest_version}?\n\n"
                f"It is saved inside Snatch's own folder. The copy that came\n"
                f"with Snatch is kept, so you can go back to it at any time."):
            self._do_update()

    def _prompt_revert(self):
        """Delete the fetched copy so find_ytdlp() falls back to the bundle."""
        path = updated_ytdlp_path()
        if not path:
            return
        if not messagebox.askyesno(
                "Revert yt-dlp",
                "Go back to the copy of yt-dlp that came with Snatch?\n\n"
                "Use this if a downloaded version stops working. You can\n"
                "download the newest one again afterwards."):
            return
        try:
            os.unlink(path)
        except OSError as e:
            messagebox.showerror(
                "Error", f"Could not remove the downloaded yt-dlp:\n{e}")
            return
        self.status_var.set("Reverted to the yt-dlp that came with Snatch")
        self.check_version()

    def _do_update(self):
        """Perform the actual update"""
        self.status_var.set("Updating yt-dlp...")
        self.update_btn.config(state=tk.DISABLED, text="Updating...")
        thread = threading.Thread(target=self._update_ytdlp_thread)
        thread.daemon = True
        thread.start()

    @staticmethod
    def _probe_version(path):
        """Run a candidate binary and return the version it reports, else None.

        This is what makes promoting a download safe. A truncated file, an
        HTML error page saved under a binary's name, or a build for the wrong
        architecture all fail here, and the caller keeps the working copy.
        """
        try:
            result = subprocess.run([path, "--version"], capture_output=True,
                                    text=True, timeout=YTDLP_PROBE_TIMEOUT)
        except (OSError, subprocess.SubprocessError):
            return None
        if result.returncode != 0:
            return None
        return result.stdout.strip() or None

    def _update_ytdlp_thread(self):
        """Download the current nightly yt-dlp into user_bin_dir().

        Written under a temp name in the SAME directory and renamed into
        place only once the downloaded file has reported a version, so a
        truncated download or a crash mid-write leaves the previous state
        intact. os.replace is atomic within one filesystem, which is why the
        temp file cannot live in /tmp.

        Replaces a curl + pkexec install into /usr/local/bin, which asked for
        a password, wrote outside the app, and pulled the stable channel that
        SNAT-0014 established does not play YouTube.
        """
        target_dir = user_bin_dir()
        asset = _ytdlp_asset_name()
        final_path = os.path.join(
            target_dir, "yt-dlp" + (".exe" if is_windows() else ""))
        url = (f"https://github.com/{YTDLP_NIGHTLY_REPO}/releases/download/"
               f"{self.latest_version}/{asset}")
        tmp_path = None
        try:
            # STANDARDS.md section 5: network fetches are HTTPS-only. The URL is
            # built from constants above, so this asserts the constants rather
            # than sanitising user input.
            if not url.startswith("https://"):
                raise ValueError("refusing a download that is not HTTPS")

            req = urllib.request.Request(url, headers={"User-Agent": "Snatch"})
            fd, tmp_path = tempfile.mkstemp(prefix=".yt-dlp-new-", dir=target_dir)
            written = 0
            with os.fdopen(fd, "wb") as out:
                with urllib.request.urlopen(
                        req, timeout=YTDLP_DOWNLOAD_TIMEOUT) as resp:
                    while True:
                        chunk = resp.read(YTDLP_CHUNK_BYTES)
                        if not chunk:
                            break
                        written += len(chunk)
                        if written > YTDLP_MAX_BYTES:
                            raise ValueError("download far larger than expected")
                        out.write(chunk)
            if not written:
                raise ValueError("the download was empty")

            os.chmod(tmp_path, 0o700)
            new_version = self._probe_version(tmp_path)
            if not new_version:
                raise ValueError(
                    "the downloaded file does not run, so it was discarded")

            os.replace(tmp_path, final_path)
            tmp_path = None
            self.root.after(0, lambda: self._update_complete(new_version))
        except Exception as e:
            detail = str(e) or e.__class__.__name__
            self.root.after(0, lambda: self._update_failed(
                f"Could not update yt-dlp.\n\n{detail}\n\n"
                f"Snatch is still using the copy it had before."))
        finally:
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    def _update_complete(self, new_version):
        """Handle successful update - verify and update display"""
        old_version = self.current_version

        if new_version:
            self.current_version = new_version
            self.version_var.set(f"v{new_version}")

        # Check if we're now up to date
        if new_version and self.latest_version and self._version_compare(self.latest_version, new_version) <= 0:
            self._refresh_idle_button()
            self.status_var.set(f"Updated from {old_version} to {new_version}")
            messagebox.showinfo("Success", f"yt-dlp updated successfully!\n\n{old_version} -> {new_version}")
        elif new_version and new_version != old_version:
            self.update_btn.config(text=f"Update to {self.latest_version}", state=tk.NORMAL)
            self.status_var.set(f"Updated to {new_version}, but {self.latest_version} is available")
            messagebox.showinfo("Partial Update",
                                f"yt-dlp updated from {old_version} to {new_version},\n"
                                f"but version {self.latest_version} is still newer.")
        else:
            self.update_btn.config(text=f"Update to {self.latest_version}", state=tk.NORMAL)
            self.status_var.set("Update may not have applied")
            messagebox.showwarning("Update Warning",
                                   "The download finished but the version did not change.\n\n"
                                   "Snatch is still working — this usually means the\n"
                                   "newest yt-dlp is the one you already had.")

    def _update_failed(self, message):
        """Handle failed update"""
        self.status_var.set("Update failed")
        self.update_btn.config(text=f"Update to {self.latest_version}", state=tk.NORMAL)
        messagebox.showerror("Error", message)
