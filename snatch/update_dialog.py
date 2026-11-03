"""The "Snatch X available" dialog: notes, then install on request (SNAT-0038).

Non-modal, so the app keeps working while the notes are read or the build
downloads. The download runs in a daemon thread and reports back through
root.after(0, ...); installing happens on the main thread, because it has to
stop and save the app first.
"""

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from . import __version__
from .logging_setup import get_logger
from .self_update import (UpdateCancelled, UpdateError,
                          UpdateVerificationError, download_verified)
from .theme import get_theme
from .update_installer import (UpdateInstallError, discard,
                               install_and_relaunch)

log = get_logger(__name__)

DOWNLOAD_FAILED = "Couldn't download the update. Try again later."
VERIFY_FAILED = "The update could not be verified, so it was not installed."
NOTES_HEIGHT_LINES = 18
NOTES_WIDTH_CHARS = 80
BYTES_PER_MB = 1024 * 1024


class UpdateDialog(tk.Toplevel):
    def __init__(self, app, offer, installer):
        super().__init__(app.root)
        self.app, self.offer, self.installer = app, offer, installer
        self._cancel = threading.Event()
        self._closed = False
        theme = get_theme()

        self.title(f"Snatch {offer.version}")
        self.configure(bg=theme.BG)
        self.transient(app.root)
        self.protocol("WM_DELETE_WINDOW", self.close)

        frame = ttk.Frame(self, padding="16")
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text=f"Snatch {offer.version} is available. "
                              f"You have {__version__}.",
                  style="Title.TLabel").pack(anchor=tk.W, pady=(0, 10))

        notes_frame = ttk.Frame(frame)
        notes_frame.pack(fill=tk.BOTH, expand=True)
        scroll = ttk.Scrollbar(notes_frame, orient=tk.VERTICAL)
        notes = tk.Text(notes_frame, wrap=tk.WORD, height=NOTES_HEIGHT_LINES,
                        width=NOTES_WIDTH_CHARS, bg=theme.ENTRY_BG,
                        fg=theme.FG, insertbackground=theme.FG,
                        selectbackground=theme.ACCENT,
                        selectforeground=theme.BUTTON_FG, borderwidth=1,
                        relief="solid", highlightbackground=theme.BORDER,
                        highlightcolor=theme.ACCENT,
                        yscrollcommand=scroll.set)
        scroll.config(command=notes.yview)
        notes.insert("1.0", offer.notes or "No release notes.")
        notes.config(state=tk.DISABLED)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        notes.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Shown once Update now is pressed.
        self.progress = ttk.Progressbar(frame, mode="determinate", maximum=100)
        self.progress_text = tk.StringVar()
        self.progress_label = ttk.Label(frame, textvariable=self.progress_text,
                                        style="Version.TLabel")

        buttons = ttk.Frame(frame)
        buttons.pack(fill=tk.X, pady=(12, 0))
        self.later_btn = ttk.Button(buttons, text="Later", command=self.close)
        self.skip_btn = ttk.Button(buttons, text="Skip this version",
                                   command=self._skip)
        self.update_btn = ttk.Button(buttons, text="Update now",
                                     style="Accent.TButton",
                                     command=self._start)
        self.cancel_btn = ttk.Button(buttons, text="Cancel", command=self.close)
        for button in (self.update_btn, self.later_btn, self.skip_btn):
            button.pack(side=tk.RIGHT, padx=(6, 0))
        self._buttons = buttons

    # ── Buttons ──────────────────────────────────────────────────────

    def close(self):
        """Later, Cancel and the window's close button. Cancels a download."""
        self._cancel.set()
        if not self._closed:
            self._closed = True
            self.destroy()

    def _skip(self):
        self.app._dismiss_app_update()
        self.close()

    def _start(self):
        for button in (self.update_btn, self.later_btn, self.skip_btn):
            button.config(state=tk.DISABLED)
        self.cancel_btn.pack(side=tk.LEFT)
        self.progress.pack(fill=tk.X, pady=(12, 0), before=self._buttons)
        self.progress_label.pack(anchor=tk.W, before=self._buttons)
        self.progress_text.set("Downloading...")
        thread = threading.Thread(target=self._download_thread, daemon=True)
        thread.start()

    # ── Download, on its own thread ──────────────────────────────────

    def _download_thread(self):
        after = self.app.root.after
        try:
            path = download_verified(
                self.offer, str(self.installer.target.parent),
                on_progress=lambda done, total: after(
                    0, lambda: self._show_progress(done, total)),
                cancelled=self._cancel.is_set)
        except UpdateCancelled:
            return
        except UpdateVerificationError:
            log.warning("Snatch %s failed verification", self.offer.version,
                        exc_info=True)
            after(0, lambda: self._failed(VERIFY_FAILED))
            return
        except UpdateError:
            log.warning("Snatch %s did not download", self.offer.version,
                        exc_info=True)
            after(0, lambda: self._failed(DOWNLOAD_FAILED))
            return
        except Exception:
            # Anything unnamed would otherwise die silently in this thread.
            log.exception("Snatch update failed unexpectedly")
            after(0, lambda: self._failed(DOWNLOAD_FAILED))
            return
        after(0, lambda: self._install(path))

    # ── Back on the main thread ──────────────────────────────────────

    def _show_progress(self, done, total):
        if self._closed:
            return
        if total:
            self.progress["value"] = done * 100 / total
            self.progress_text.set(f"{done / BYTES_PER_MB:.1f} of "
                                   f"{total / BYTES_PER_MB:.1f} MB")
        else:
            self.progress_text.set(f"{done / BYTES_PER_MB:.1f} MB")

    def _failed(self, message):
        if not self._closed:
            messagebox.showerror("Update Snatch", message, parent=self)
        self.close()

    def _install(self, path):
        if self._closed:
            # Closed in the moment between the download ending and this.
            discard(path)
            return
        self.progress_text.set("Installing...")
        try:
            install_and_relaunch(self.app, self.installer, path)
        except UpdateInstallError as exc:
            log.error("Could not install Snatch %s: %s", self.offer.version, exc)
            messagebox.showerror(
                "Update Snatch",
                f"Couldn't install the update:\n{exc}\n\n"
                f"Snatch {__version__} is still installed and running.",
                parent=self)
        # Reached only when nothing was installed.
        self.close()
