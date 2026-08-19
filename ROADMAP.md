<!-- ants-roadmap-format: 1 -->
# Snatch — Roadmap

A tkinter frontend for yt-dlp. This roadmap tracks packaging, distribution
and application work. IDs are allocated from `.roadmap-counter`.

## Packaging and distribution

- ✅ [SNAT-0001] **Windows one-file build via GitHub Actions.**
  PyInstaller `--onefile` on a `windows-latest` runner, bundling
  `yt-dlp.exe` and `ffmpeg.exe` downloaded at build time. Spec in
  `pyinstaller.spec`; workflow in `.github/workflows/build-windows.yml`.
  Verified 2026-08-19 on real hardware (Windows 10 22H2, no Python
  installed): the .exe reaches the Tk main loop without crashing.
  Layman: Windows users get one file they can double-click, with no
  Python install needed.
  Kind: package.
  Source: in-session-2026-05-27.
  Lanes: packaging, ci.

- ✅ [SNAT-0002] **Rename the project from YT-DLP GUI to Snatch.**
  Package `ytdlp_gui/` to `snatch/`, entry point, main class, window
  title, Tk class name, built artefact, desktop entry and the GitHub
  repository. New application icon cropped to its alpha bounding box.
  Layman: The app is now called Snatch everywhere, including its name on
  GitHub.
  Kind: chore.
  Source: user-request-2026-08-19.
  Lanes: packaging, docs.

- ✅ [SNAT-0003] **Ship a self-contained Linux AppImage.**
  One file a user downloads, marks executable and runs, with no Python
  or tkinter install required. Built in CI so it is reproducible, on a
  base old enough that the glibc it links against is widely available.
  Must bundle `yt-dlp` and `ffmpeg` the way the Windows build does.
  Layman: Linux users get one file they can download and run.
  Kind: package.
  Source: user-request-2026-08-19.
  Lanes: packaging, ci.
  Resolved (2026-08-19): built by scripts/build-linux.sh and verified twice — natively on this machine and inside the CI container under act, then green on GitHub run 32276726723. The AppImage launches, reaches the Tk main loop and creates its XDG data directory 0700; all three bundled binaries execute. Two defects found and fixed on the way: PyInstaller could not resolve libXcursor.so.1 (so tkinterdnd2's drag-and-drop would have failed on a user machine), and appimagetool hangs indefinitely fetching its own runtime, so the script now passes --runtime-file.

- ✅ [SNAT-0004] **Ship a self-contained macOS application.**
  A `.dmg` containing `Snatch.app`, built by PyInstaller on a macOS
  runner. Unsigned and un-notarised, so Gatekeeper will block a
  double-click until the user right-clicks and chooses Open; the README
  must say so plainly rather than leaving them at a dead end.
  Layman: Mac users get a normal Mac app, with one extra step the first
  time they open it because it is not signed by Apple.
  Kind: package.
  Source: user-request-2026-08-19.
  Lanes: packaging, ci.
  Resolved (2026-08-19): built by scripts/build-macos.sh, green on its first ever execution (GitHub run 32276726723). Produces Snatch.app, ad-hoc signed so an arm64 bundle will launch, packaged into Snatch-<arch>.dmg. NOT verified beyond the build: nobody has run the app on a Mac. It is unsigned and un-notarised, so Gatekeeper blocks the first double-click; README documents the right-click to Open workaround.

- 📋 [SNAT-0005] **Publish the first release, v1.0.0.**
  Tag `v1.0.0` and attach the Windows .exe, the Linux AppImage and the
  macOS .dmg to a single GitHub Release. Blocked on SNAT-0003 and
  SNAT-0004 producing artefacts CI has actually built.
  Layman: The first proper download page, with a file for each system.
  Kind: release.
  Source: user-request-2026-08-19.
  Lanes: release, ci.

- 📋 [SNAT-0008] **Upgrade act past CVE-2026-34041 and CVE-2026-34042.**
  scripts/local-ci.sh drives `act`, and act 0.2.84 on this machine prints
  its own warning: vulnerable to CVE-2026-34041 and CVE-2026-34042,
  fixed in 0.2.86. Latest at time of writing is 0.2.89. The gate works,
  but it is running a tool that is telling us to upgrade it.
  **Layman:** The tool that runs our checks locally has a known security hole and should be updated.
  Kind: security.
  Source: in-session-2026-08-19.
  Lanes: ci, security.

- 📋 [SNAT-0009] **Pin the appimagetool runtime rather than tracking continuous.**
  scripts/build-linux.sh downloads the AppImage type2 runtime from the
  `continuous` tag, which moves. Everything else in the build is pinned
  (yt-dlp 2026.03.17, ffmpeg-static b6.1.1, pyinstaller 6.11.1). A moving
  runtime can break a build with no change on our side.
  **Layman:** One piece of the Linux build always grabs the newest version, which could break without warning.
  Kind: chore.
  Source: in-session-2026-08-19.
  Lanes: packaging, ci.

## Application

- 📋 [SNAT-0006] **Write user data files with 0600 permissions.**
  `CLAUDE.md` and `STANDARDS.md` section 5 require 0600 on `config.json`,
  `history.json` and `cookies.txt`. Observed 2026-08-19: the files on
  disk are 0644 and 0664, so the rule is not being applied at write
  time. They are gitignored, so nothing has leaked, but cookies.txt in
  particular carries session tokens.
  Layman: The files holding your settings and browser cookies should be
  readable only by you, and right now they are readable by anyone with
  an account on the machine.
  Kind: security.
  Source: in-session-2026-08-19.
  Lanes: security, config.

- 📋 [SNAT-0007] **Verify the GUI renders on Windows from a real desktop session.**
  The 2026-08-19 test reached the Tk main loop over SSH, but SSH runs in
  a non-interactive window station (`MainWindowHandle=0`), so nothing
  confirmed a window is drawn, that the icon and theme load, or that the
  graceful-close config write fires. Needs a run from the machine's own
  desktop.
  Layman: We know the Windows build starts; we have not yet seen its
  window with our own eyes.
  Kind: test.
  Source: in-session-2026-08-19.
  Lanes: packaging, test.
