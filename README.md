# Snatch

**Save videos from the web to your computer.**

Snatch is a simple window with buttons that does the hard part for you. Paste a
link, pick a quality, click Download. It handles YouTube and around a thousand
other sites.

It's a friendly face on a powerful tool called
[yt-dlp](https://github.com/yt-dlp/yt-dlp) — Snatch does the clicking so you
never have to type a command.

---

## Download

Grab the file for your computer from the
**[Releases page](https://github.com/milnet01/snatch/releases/latest)**.
Everything is inside that one file — you do **not** need to install Python,
yt-dlp, ffmpeg or anything else.

| Your computer | File to download | How to open it |
|---|---|---|
| **Windows** | `snatch.exe` | Double-click it. |
| **Mac** | `Snatch-arm64.dmg` | Open it, drag Snatch to Applications. **First time only:** right-click the app and choose **Open** (see below). |
| **Linux** | `Snatch-x86_64.AppImage` | Right-click → Properties → tick "allow executing as program", then double-click. |

<details>
<summary><b>Windows says "Windows protected your PC"</b></summary>

That's SmartScreen. It shows this for any program it hasn't seen many people
run yet — it is not a virus warning. Click **More info**, then **Run anyway**.
</details>

<details>
<summary><b>Mac says "Snatch cannot be opened because the developer cannot be verified"</b></summary>

Apple charges a yearly fee to sign apps, and Snatch isn't signed. The app is
fine; macOS is just being cautious about software it can't trace to a paid
developer account.

To open it the first time: **right-click** (or Control-click) the Snatch app
and choose **Open**, then click **Open** in the box that appears. You only do
this once — after that it opens normally.
</details>

<details>
<summary><b>Linux: the AppImage won't run</b></summary>

The file needs permission to run. In a terminal:

```bash
chmod +x Snatch-x86_64.AppImage
./Snatch-x86_64.AppImage
```
</details>

---

## What you can do with it

**Download tab** — Paste a link (or drag one onto the window), choose the
quality you want, and click Download. You can queue several at once and watch
the progress bar for each.

**Search tab** — Search YouTube without opening a browser. Preview a result to
check it's the right video before you download it.

**Media Info tab** — Point it at a video file already on your computer and it
tells you what's inside: how long it is, the quality, the file type.

**History tab** — Everything you've downloaded, with a button to open the file
or the folder it went to.

**Other things it does**

- **Seven colour themes** — Dark, Nord, Monokai, YouTube, Dracula, Gruvbox and
  Solarized.
- **Skip sponsor segments** — optionally cuts sponsor reads out of YouTube
  videos automatically (SponsorBlock).
- **Subtitles** — download them alongside the video.
- **Speed limit** — stop Snatch from eating your whole connection.
- **Audio only** — pull just the sound out, for music or podcasts.
- **Private videos** — import cookies from Firefox or Chrome so Snatch can
  reach age-restricted or members-only videos you already have access to.

---

## Where Snatch keeps your files

Downloads go wherever you choose in the app. Snatch also keeps a few small
files of its own — your settings and your download history:

| Your computer | Where |
|---|---|
| **Windows** | Next to `snatch.exe`. Move the .exe and your settings move with it. |
| **Mac** | `~/Library/Application Support/Snatch` |
| **Linux** | `~/.local/share/snatch` |

These stay on your computer. Nothing is uploaded anywhere.

---

## Something's not working

**"No video formats found"** — the site may have changed. Click **Check
version** in the app; a newer yt-dlp usually fixes it.

**Download stops partway** — check the disk isn't full, then try again. Snatch
resumes where it left off.

**The video and audio are separate files** — Snatch normally joins them for
you using a bundled tool. If you built Snatch yourself rather than downloading
it, you may be missing `ffmpeg`.

**Something else** — please [open an
issue](https://github.com/milnet01/snatch/issues) and say what you clicked and
what happened.

**Getting a log to attach.** Snatch normally records nothing. Start it with
`SNATCH_LOG=1` and it writes `snatch.log` next to your settings (the same
folder as `config.json` — see *Where Snatch keeps your files*), noting what
failed and why. Nothing else about the app changes.

```
SNATCH_LOG=1 ./Snatch-x86_64.AppImage      # Linux
set SNATCH_LOG=1 && Snatch.exe             # Windows, from a cmd window
```

The file is readable only by you and is capped in size, but it does contain
the links you downloaded — skim it before attaching it to an issue.

---

## Running from source

Only needed if you want to change the code — the downloads above are complete
on their own.

**You'll need:** Python 3.10 or newer, Tkinter (`python3-tk` on Debian and
Ubuntu), and `yt-dlp` available on your `PATH`.

```bash
git clone https://github.com/milnet01/snatch.git
cd snatch
pip install -r requirements.txt
python3 snatch.py
```

Optional extras: `mpv` for the preview player, `ffmpeg`/`ffprobe` for merging
and Media Info, `zenity` for a nicer file picker on GNOME and KDE.

`Snatch.desktop` is a Linux launcher entry. Its `Exec=`, `Path=` and `Icon=`
lines point at `/mnt/Games/Scripts/Linux/Snatch`; edit them to match wherever
you cloned the repo, then copy it into `~/.local/share/applications/`.

### Building the downloadable files yourself

Each platform has one script, and GitHub Actions runs those same scripts — so
what you build locally is what CI builds.

```bash
scripts/build-linux.sh      # -> dist/Snatch-x86_64.AppImage   (run on Linux)
scripts/build-windows.sh    # -> dist/snatch.exe               (run on Windows)
scripts/build-macos.sh      # -> dist/Snatch-<arch>.dmg        (run on macOS)
```

Before pushing, run the local gate. It executes the real
`.github/workflows/ci.yml` through [`act`](https://github.com/nektos/act)
rather than imitating it, and tells you which jobs it could not run:

```bash
scripts/local-ci.sh          # lint + execute the Linux jobs in a container
scripts/local-ci.sh --lint   # lint only — enough for a docs-only change
```

### How the code is laid out

`SnatchApp` in `snatch/app.py` is assembled from seven mixins — one per tab,
plus the player, version checks and the download engine. Anything slow runs on
a background thread and posts results back to the UI via `root.after(0, ...)`.

See [docs/building.md](docs/building.md) for how the downloads are produced
and where every version is pinned, [STANDARDS.md](STANDARDS.md) for the
architecture, theme system, security rules and coding conventions,
[ROADMAP.md](ROADMAP.md) for what's planned, and
[CHANGELOG.md](CHANGELOG.md) for what changed.

---

## Licence

See [LICENSE](LICENSE). Snatch bundles [yt-dlp](https://github.com/yt-dlp/yt-dlp)
(Unlicense) and [ffmpeg](https://ffmpeg.org/) (LGPL/GPL), each under its own
licence.
