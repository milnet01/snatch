"""yt-dlp version checking and update logic"""

import os
import re
import json
import subprocess
import threading
import tkinter as tk
from tkinter import messagebox
import urllib.request

from .platform_utils import find_ytdlp, is_windows, is_frozen


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
            url = "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest"
            req = urllib.request.Request(url, headers={"User-Agent": "Snatch"})
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
                self.latest_version = data.get("tag_name", "").lstrip("v")
                del data  # Free API response JSON

                if self.latest_version and self.current_version:
                    if self._version_compare(self.latest_version, self.current_version) > 0:
                        self.root.after(0, self._show_update_available)
                    else:
                        self.root.after(0, lambda: self.update_btn.config(
                            text="Up to date", state=tk.DISABLED))
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
        """Show update available button and prompt user (Linux only)."""
        if is_windows():
            # Bundled yt-dlp.exe is shipped with each Snatch release — the user
            # updates by downloading a new snatch.exe. Show a passive label
            # only; don't prompt or wire the update button to run pkexec/curl.
            self.update_btn.config(
                text=f"v{self.latest_version} available — download new Snatch",
                state=tk.DISABLED,
            )
            self.status_var.set(
                f"yt-dlp {self.latest_version} is out — grab the latest "
                f"snatch.exe from GitHub Releases to update."
            )
            return

        self.update_btn.config(text=f"Update to {self.latest_version}", state=tk.NORMAL)
        self.status_var.set(f"Update available: {self.current_version} -> {self.latest_version}")

        if messagebox.askyesno("Update Available",
                               f"A new version of yt-dlp is available!\n\n"
                               f"Current: {self.current_version}\n"
                               f"Latest: {self.latest_version}\n\n"
                               f"Would you like to update now?"):
            self._do_update()

    def update_ytdlp(self):
        """Update yt-dlp to latest version (called from button).

        A PACKAGED build cannot do this. Its yt-dlp lives inside the bundle,
        in a read-only temp directory that is deleted on exit, and
        find_ytdlp() prefers that copy — so updating the system one changes
        nothing the app will ever use. Gating this on is_windows() meant the
        Linux AppImage ran the update, kept using its bundled copy, and then
        warned "the update completed but the version did not change".
        """
        if is_frozen():
            asset = "snatch.exe" if is_windows() else "the latest release"
            messagebox.showinfo(
                "Update Snatch instead",
                "yt-dlp is bundled inside this copy of Snatch, so it cannot\n"
                "be updated on its own.\n\n"
                f"To get a newer yt-dlp, download {asset} from\n"
                "https://github.com/milnet01/snatch/releases"
            )
            return
        if self.latest_version:
            if messagebox.askyesno("Update yt-dlp",
                                   f"Update yt-dlp to version {self.latest_version}?\n\n"
                                   f"You may be prompted for your password."):
                self._do_update()

    def _do_update(self):
        """Perform the actual update"""
        self.status_var.set("Updating yt-dlp...")
        self.update_btn.config(state=tk.DISABLED, text="Updating...")
        thread = threading.Thread(target=self._update_ytdlp_thread)
        thread.daemon = True
        thread.start()

    def _update_ytdlp_thread(self):
        try:
            # Download to a temp file first, then move into place
            import tempfile
            tmp_fd, tmp_path = tempfile.mkstemp(prefix="yt-dlp-update-")
            os.close(tmp_fd)

            try:
                # Download without elevated privileges
                download_cmd = [
                    "curl", "-L", "--fail", "--proto", "=https",
                    "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp",
                    "-o", tmp_path
                ]
                result = subprocess.run(download_cmd, capture_output=True, text=True, timeout=120)
                if result.returncode != 0:
                    self.root.after(0, lambda: self._update_failed(
                        "Download failed. Try running manually in terminal:\n\n"
                        "sudo curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o /usr/local/bin/yt-dlp\n"
                        "sudo chmod a+rx /usr/local/bin/yt-dlp"
                    ))
                    return

                # Use pkexec only for the install step (no shell)
                install_cmd = ["pkexec", "install", "-m", "755", tmp_path, "/usr/local/bin/yt-dlp"]
                result = subprocess.run(install_cmd, capture_output=True, text=True, timeout=30)
            finally:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

            if result.returncode == 0:
                # Verify the new version
                new_version = None
                try:
                    ver_result = subprocess.run([find_ytdlp(), "--version"], capture_output=True, text=True, timeout=10)
                    if ver_result.returncode == 0:
                        new_version = ver_result.stdout.strip()
                except Exception:
                    pass
                self.root.after(0, lambda: self._update_complete(new_version))
            else:
                self.root.after(0, lambda: self._update_failed(
                    "Update failed. Try running manually in terminal:\n\n"
                    "sudo curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o /usr/local/bin/yt-dlp\n"
                    "sudo chmod a+rx /usr/local/bin/yt-dlp"
                ))
        except subprocess.TimeoutExpired:
            self.root.after(0, lambda: self._update_failed("Update timed out"))
        except Exception as e:
            self.root.after(0, lambda: self._update_failed(f"Update error: {e}"))

    def _update_complete(self, new_version):
        """Handle successful update - verify and update display"""
        old_version = self.current_version

        if new_version:
            self.current_version = new_version
            self.version_var.set(f"v{new_version}")

        # Check if we're now up to date
        if new_version and self.latest_version and self._version_compare(self.latest_version, new_version) <= 0:
            self.update_btn.config(text="Up to date", state=tk.DISABLED)
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
                                   "The update completed but the version did not change.\n\n"
                                   "Try updating manually in terminal:\n"
                                   "sudo curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp "
                                   "-o /usr/local/bin/yt-dlp && sudo chmod a+rx /usr/local/bin/yt-dlp")

    def _update_failed(self, message):
        """Handle failed update"""
        self.status_var.set("Update failed")
        self.update_btn.config(text=f"Update to {self.latest_version}", state=tk.NORMAL)
        messagebox.showerror("Error", message)
