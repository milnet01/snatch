"""Media Info tab UI and ffprobe integration"""

import os
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from ..theme import get_theme
from ..utils import zenity_file_dialog
from ..platform_utils import find_ffprobe, is_windows


class MediaInfoTabMixin:
    """Mixin providing the Media Info tab UI and logic."""

    def _create_media_info_tab(self, parent):
        """Build the media info tab contents"""
        # File selection
        file_frame = ttk.LabelFrame(parent, text="Select Media File", padding="12")
        file_frame.pack(fill=tk.X, pady=(0, 12))

        file_entry = ttk.Entry(file_frame, textvariable=self.media_file_var, font=("Helvetica", 10))
        file_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        ttk.Button(file_frame, text="Browse...",
                   command=self.browse_media_file).pack(side=tk.LEFT, padx=(0, 5))

        ttk.Button(file_frame, text="Analyze",
                   command=self.analyze_media_file).pack(side=tk.RIGHT)

        # Media info display
        info_frame = ttk.LabelFrame(parent, text="Media Information", padding="12")
        info_frame.pack(fill=tk.BOTH, expand=True)

        theme = get_theme()
        text_scroll = ttk.Scrollbar(info_frame, orient=tk.VERTICAL)
        self.media_info_text = tk.Text(
            info_frame,
            wrap=tk.WORD,
            font=("Courier", 10),
            bg=theme.ENTRY_BG,
            fg=theme.FG,
            insertbackground=theme.FG,
            selectbackground=theme.ACCENT,
            selectforeground=theme.BUTTON_FG,
            borderwidth=1,
            relief="solid",
            highlightbackground=theme.BORDER,
            highlightcolor=theme.ACCENT,
            state=tk.DISABLED
        )
        text_scroll.config(command=self.media_info_text.yview)
        self.media_info_text.config(yscrollcommand=text_scroll.set)

        self.media_info_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        text_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Auto-analyze if a file was remembered
        if self.media_file_var.get() and os.path.isfile(self.media_file_var.get()):
            self.root.after(100, self.analyze_media_file)

    def browse_media_file(self):
        """Browse for a media file to analyze"""
        initial_dir = os.path.dirname(self.media_file_var.get()) if self.media_file_var.get() else self.save_path_var.get()
        path = zenity_file_dialog(initial_dir=initial_dir, title="Select Media File")
        if path:
            self.media_file_var.set(path)
            self.analyze_media_file()
            return
        filepath = filedialog.askopenfilename(
            initialdir=initial_dir, title="Select Media File",
            filetypes=[
                ("Video files", "*.mp4 *.mkv *.webm *.avi *.mov *.flv *.wmv *.m4v *.ts"),
                ("Audio files", "*.mp3 *.m4a *.aac *.ogg *.opus *.flac *.wav *.wma"),
                ("All files", "*.*")])
        if filepath:
            self.media_file_var.set(filepath)
            self.analyze_media_file()

    def analyze_media_file(self):
        """Run ffprobe on the selected file and display results"""
        filepath = self.media_file_var.get().strip()
        if not filepath:
            messagebox.showwarning("Warning", "Please select a media file")
            return
        if not os.path.isfile(filepath):
            messagebox.showerror("Error", f"File not found:\n{filepath}")
            return

        self._set_media_info_text("Analyzing...")

        thread = threading.Thread(target=self._analyze_media_thread, args=(filepath,))
        thread.daemon = True
        thread.start()

    def _analyze_media_thread(self, filepath):
        """Run ffprobe in a background thread"""
        try:
            cmd = [
                find_ffprobe(),
                "-hide_banner",
                "-show_format",
                "-show_streams",
                "-pretty",
                "--", filepath
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                output = result.stderr.strip() or "ffprobe returned an error."
            else:
                output = self._format_ffprobe_output(result.stdout, result.stderr)

            self.root.after(0, lambda: self._set_media_info_text(output))

        except FileNotFoundError:
            install_hint = (
                "Install ffmpeg from https://www.gyan.dev/ffmpeg/builds/ "
                "and add it to your PATH."
                if is_windows()
                else "Install ffmpeg:\n  sudo apt install ffmpeg"
            )
            self.root.after(0, lambda: self._set_media_info_text(
                f"ffprobe not found.\n\n{install_hint}"))
        except subprocess.TimeoutExpired:
            self.root.after(0, lambda: self._set_media_info_text("Analysis timed out."))
        except Exception as e:
            self.root.after(0, lambda: self._set_media_info_text(f"Error: {e}"))

    @staticmethod
    def _format_ffprobe_output(stdout, stderr):
        """Parse ffprobe output into a readable summary"""
        lines = []

        for line in stderr.splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("Input"):
                lines.append(stripped)

        lines.append("")
        lines.append("=" * 50)

        current_section = None
        stream_num = 0
        for line in stdout.splitlines():
            stripped = line.strip()
            if stripped == "[STREAM]":
                stream_num += 1
                current_section = "stream"
                lines.append("")
                lines.append(f"--- Stream #{stream_num} ---")
                continue
            elif stripped == "[/STREAM]":
                current_section = None
                continue
            elif stripped == "[FORMAT]":
                current_section = "format"
                lines.append("")
                lines.append("--- Container Format ---")
                continue
            elif stripped == "[/FORMAT]":
                current_section = None
                continue

            if current_section and "=" in stripped:
                key, _, value = stripped.partition("=")
                if value and value != "N/A" and value != "unknown":
                    display_key = key.replace("_", " ").title()
                    lines.append(f"  {display_key}: {value}")

        return "\n".join(lines)

    def _set_media_info_text(self, text):
        """Set the media info text widget content"""
        self.media_info_text.config(state=tk.NORMAL)
        self.media_info_text.delete("1.0", tk.END)
        self.media_info_text.insert("1.0", text)
        self.media_info_text.config(state=tk.DISABLED)
