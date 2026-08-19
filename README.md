# Snatch

A tkinter-based graphical frontend for [yt-dlp](https://github.com/yt-dlp/yt-dlp), built for Linux desktops.

Four tabs in one window: download videos, search YouTube with embedded playback, inspect local media files, and browse download history. Seven themes (Dark, Nord, Monokai, YouTube, Dracula, Gruvbox, Solarized), drag-and-drop URL support, optional embedded mpv player, browser cookie import, and yt-dlp self-update from the GUI.

## Download for Windows

A single-file `snatch.exe` is published on the [Releases page](https://github.com/milnet01/snatch/releases) — no Python install needed. Double-click to run; user data is created next to the .exe. See [docs/windows-build.md](docs/windows-build.md) for build internals.

## Features

- **Download tab** — paste a URL (or drag-and-drop), pick format/resolution, queue multiple downloads, watch live progress
- **Search tab** — search YouTube and preview results in an embedded mpv player before downloading
- **Media Info tab** — inspect any local video/audio file via `ffprobe` (codec, bitrate, duration, streams)
- **History tab** — browse and manage previous downloads (stored locally, max 200 entries)
- **Browser cookie import** — pull cookies from Firefox/Chrome for age-gated or member-only videos
- **yt-dlp version check + update** — one-click self-update via `pkexec`
- **SponsorBlock + subtitle support** — toggle per-download
- **Speed limit + audio merging** — configurable per session

## Screenshots

_(Add screenshots here — `icon.png` ships with the repo.)_

## Requirements

**Required:**
- Python 3.10+
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) on `PATH`
- Tkinter (`python3-tk` on Debian/Ubuntu, usually preinstalled on most distros)

**Optional (auto-detected):**
- [`mpv`](https://mpv.io/) — enables the embedded player in the Search tab
- [`ffprobe`](https://ffmpeg.org/) — required for the Media Info tab
- [`tkinterdnd2`](https://pypi.org/project/tkinterdnd2/) — enables drag-and-drop URL support (`pip install tkinterdnd2`)
- [`Pillow`](https://pypi.org/project/Pillow/) — enables thumbnail rendering (`pip install Pillow`)
- `zenity` — nicer native file picker on GNOME/KDE

## Install

```bash
git clone https://github.com/milnet01/snatch.git
cd snatch
# Optional extras:
pip install --user tkinterdnd2 Pillow
```

## Run

```bash
python3 snatch.py
```

or as a module:

```bash
python3 -m snatch
```

### Desktop launcher

`YT-DLP.desktop` is provided but its `Exec=` and `Path=` lines point at the original author's install location. Edit both lines to your actual checkout path, then drop it into `~/.local/share/applications/`.

## Configuration

Three files are created at runtime in the project root, all mode `0600`:

| File | Purpose |
|------|---------|
| `config.json` | UI preferences (save path, default format, theme, window geometry) |
| `history.json` | Download history (max 200 entries) |
| `cookies.txt` | Browser-exported cookies (when used) |

These are git-ignored and never uploaded.

## Architecture

The main `SnatchApp` class in `snatch/app.py` is composed of seven mixins (one per concern: each tab, the player, version checks, the download engine). All blocking work runs in daemon threads and posts back to the Tk event loop via `root.after(0, ...)`.

See [STANDARDS.md](STANDARDS.md) for the full architecture, mixin contracts, theme system, security rules, and coding conventions.

## Security notes

- All subprocess calls use argument lists with a `--` separator before URLs (no shell, no command injection surface).
- URLs are validated as `http`/`https` only before being passed to `yt-dlp`.
- Network fetches (thumbnails, update check) are HTTPS-only.
- The mpv IPC socket lives in a directory whose ownership is checked before connecting.
- User data files are written with `0600` permissions.

## License

[MIT](LICENSE) © 2026 milnet01
