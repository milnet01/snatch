"""yt-dlp version checking and update logic"""

import os
import re
import json
import hashlib
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
# The checksum manifest every nightly release publishes alongside the binaries.
# Lines are "<64 hex>  <asset name>".
YTDLP_SUMS_ASSET = "SHA2-256SUMS"
YTDLP_SUMS_MAX_BYTES = 64 * 1024
# A release tag is a yt-dlp nightly datestamp such as 2026.08.30.232658. It
# arrives from the GitHub API and is interpolated into a download path, so a
# value containing "/" or ".." would re-point that path within github.com.
YTDLP_TAG_RE = re.compile(r"\A[0-9][0-9.]{0,31}\Z")


def _open_https(url, timeout):
    """Open an HTTPS URL and refuse a redirect that left HTTPS.

    urllib follows redirects, and its HTTPRedirectHandler permits an
    https -> http downgrade. Checking only the URL passed in asserts what we
    asked for rather than what we got, so the response URL is checked too.
    """
    if not url.startswith("https://"):
        raise ValueError("refusing a request that is not HTTPS")
    req = urllib.request.Request(url, headers={"User-Agent": "Snatch"})
    resp = urllib.request.urlopen(req, timeout=timeout)
    if not resp.geturl().startswith("https://"):
        resp.close()
        raise ValueError("refusing a download redirected off HTTPS")
    return resp


def _expected_digest(tag, asset):
    """Return the published SHA-256 for one release asset, else raise.

    This is the only thing standing between the update and running whatever
    the network returned. Fetched from the same release as the binary, so it
    is not a defence against a compromised release -- it is a defence against
    anything that can alter bytes in transit or serve a substitute.
    """
    url = (f"https://github.com/{YTDLP_NIGHTLY_REPO}/releases/download/"
           f"{tag}/{YTDLP_SUMS_ASSET}")
    with _open_https(url, YTDLP_DOWNLOAD_TIMEOUT) as resp:
        body = resp.read(YTDLP_SUMS_MAX_BYTES).decode("utf-8", "replace")
    for line in body.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1] == asset:
            digest = parts[0].lower()
            if len(digest) != 64 or not all(c in "0123456789abcdef" for c in digest):
                raise ValueError(f"{YTDLP_SUMS_ASSET} gave a malformed digest")
            return digest
    raise ValueError(f"{YTDLP_SUMS_ASSET} does not list {asset}")


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

        Detects a truncated file, an HTML error page saved under a binary's
        name, or a build for the wrong architecture; the caller then keeps the
        working copy.

        This is NOT what makes promoting a download safe, and it used to say
        that it was. It runs the candidate, so by the time it can report
        anything the file has already executed as the user. What makes the
        promotion safe is the SHA-256 comparison the caller performs BEFORE
        calling this.
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
        place only once the downloaded bytes have matched the digest the
        release publishes AND the file has reported a version, so a truncated
        download or a crash mid-write leaves the previous state intact.
        os.replace is atomic within one filesystem, which is why the temp file
        cannot live in /tmp.

        Replaces a curl + pkexec install into /usr/local/bin, which asked for
        a password, wrote outside the app, and pulled the stable channel that
        SNAT-0014 established does not play YouTube.
        """
        target_dir = user_bin_dir()
        asset = _ytdlp_asset_name()
        final_path = os.path.join(
            target_dir, "yt-dlp" + (".exe" if is_windows() else ""))
        tag = self.latest_version or ""
        tmp_path = None
        try:
            # The tag comes from the GitHub API response and is interpolated
            # into a download path, so its shape is checked before it can
            # re-point that path with a "/" or a "..".
            if not YTDLP_TAG_RE.match(tag):
                raise ValueError(f"refusing an implausible release tag: {tag!r}")

            # Fetched first: with no expected digest there is nothing to verify
            # against, and a download nobody can verify should not be written.
            expected = _expected_digest(tag, asset)

            url = (f"https://github.com/{YTDLP_NIGHTLY_REPO}/releases/download/"
                   f"{tag}/{asset}")
            fd, tmp_path = tempfile.mkstemp(prefix=".yt-dlp-new-", dir=target_dir)
            written = 0
            digest = hashlib.sha256()
            with os.fdopen(fd, "wb") as out:
                with _open_https(url, YTDLP_DOWNLOAD_TIMEOUT) as resp:
                    while True:
                        chunk = resp.read(YTDLP_CHUNK_BYTES)
                        if not chunk:
                            break
                        written += len(chunk)
                        if written > YTDLP_MAX_BYTES:
                            raise ValueError("download far larger than expected")
                        digest.update(chunk)
                        out.write(chunk)
            if not written:
                raise ValueError("the download was empty")

            actual = digest.hexdigest()
            if actual != expected:
                raise ValueError(
                    "the download does not match the checksum this release "
                    f"publishes (expected {expected[:16]}..., "
                    f"got {actual[:16]}...), so it was discarded")

            # Only now is it safe to make the file executable and run it.
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
