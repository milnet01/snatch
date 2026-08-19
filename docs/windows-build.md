# Building the Windows .exe

The Windows binary is produced automatically by GitHub Actions
(`.github/workflows/build-windows.yml`). You don't need a Windows machine.

## Triggering a build

- **Automatic** — every push to `main` and every `v*` tag triggers a build.
- **Manual** — go to the Actions tab on GitHub, pick "build-windows",
  click "Run workflow", choose the branch.

## Downloading the artifact

After the workflow finishes (~3-5 minutes):

1. Open the run page (Actions tab → click the latest "build-windows" run).
2. Scroll to "Artifacts" → click `snatch-windows`.
3. A `snatch-windows.zip` downloads; inside is `snatch.exe`.

Artifacts are kept 30 days. Tagged releases attach the .exe to the
GitHub Release page permanently.

## What's inside the .exe

- Python 3.12 runtime (embedded)
- tkinter, Pillow, tkinterdnd2
- `bin/yt-dlp.exe` and `bin/ffmpeg.exe` (PyInstaller extracts to a temp dir at runtime)
- App icons (icon.png, icon_48.png, icon_64.png)

Expected size: ~80-120 MB.

## First-run user instructions

Send your friend the .exe and these two lines:

> Double-click `snatch.exe`. Windows SmartScreen may show a "Windows protected your PC" dialog the first time — click **More info** → **Run anyway**. The app will create `config.json`, `history.json`, and a `Downloads` folder in the same folder as the .exe.

The SmartScreen warning is normal for unsigned binaries from small open-source projects. Removing it requires a paid code-signing certificate (~$100/year), which is overkill for personal distribution.

## Updating yt-dlp

The bundled `yt-dlp.exe` is fixed at build time. To update, push a commit that bumps `yt-dlp` in `requirements.txt` (and the matching `$ytdlpVersion` in the workflow) — the next build ships the new yt-dlp.

The in-app "Check version" button on Windows shows the latest yt-dlp release but disables the auto-update (the bundled copy can't update itself while the .exe is running; the user must download a new `snatch.exe`).
