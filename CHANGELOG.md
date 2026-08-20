# Changelog

All notable changes to Snatch are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- **Right-click to paste, copy or cut in any box (SNAT-0041)**
  Every text box in Snatch — the URL bar, the search boxes, the
  cookies and save-location fields — now has a right-click menu with
  Cut, Copy, Paste and Select All. Pasting a link no longer means
  reaching for the Paste button or Ctrl+V.

  The media information panel is read-only, so it offers Copy and
  Select All only.

- **Snatch can now update its own downloader (SNAT-0016)**
  When YouTube changes something, yt-dlp — the tool Snatch uses to
  fetch videos — has to be updated to keep up. Until now that meant
  waiting for a whole new version of Snatch on all three platforms.

  Snatch now checks on startup and offers to fetch a newer yt-dlp for
  itself. It saves it inside Snatch's own folder, so it survives
  restarts and works in the packaged Windows, Linux and macOS builds
  alike. Nothing downloads without you saying yes.

  The copy that shipped with Snatch is always kept. A download that
  arrives broken is thrown away rather than installed, and if a newer
  one ever misbehaves the button offers "Revert to bundled yt-dlp" to
  put things back.

### Fixed

- **Snatch was never using its bundled JavaScript helper, so YouTube hid most video qualities (SNAT-0043)**
  YouTube makes downloaders solve a small puzzle before it will hand
  over the picture qualities, and Snatch ships a helper program to
  solve it. Snatch had been naming that helper in a way yt-dlp could
  not read, so it was never used — on every release, on every platform.
  The result was videos that appeared to have sound-only versions, or
  that failed outright with "Requested format is not available".

  Snatch now names it correctly. On the reported video that is the
  difference between 4 sound-only entries and 37 with 25 picture
  qualities.

- **Queued downloads now use the quality you chose (SNAT-0039)**
  Anything added to the queue was downloaded at whatever quality
  yt-dlp picked, ignoring the resolution and format Snatch had saved
  from your last choice. Queued items now follow that preference, and
  fall back to the best available if it cannot be matched.

- **A video that YouTube served as sound-only no longer empties the format list (SNAT-0042)**
  For some videos, the saved cookies made YouTube hand back only
  sound-only versions. Snatch then showed either "Requested format is
  not available" and nothing else, or a list with no picture qualities
  in it at all.

  Snatch now tries again without the cookies and keeps whichever answer
  actually has picture in it, telling you in the status line when it
  has skipped them. On the reported video that is the difference
  between 4 sound-only entries and 53 with 37 picture qualities.

- **Updating no longer asks for your password or touches system files**
  The old path installed yt-dlp system-wide via a password prompt.
  The new one writes only inside Snatch's own folder, so nothing
  outside the app is changed and no admin rights are needed.

- **The update button no longer offers a version that cannot play YouTube**
  It checked yt-dlp's *stable* releases and offered to install one.
  Stable is the channel that does not play YouTube — the exact problem
  fixed in 1.0.1 — so taking that offer would have broken playback.
  It now tracks the same nightly channel Snatch bundles.

### Security

- **Updated the bundled image library to close 12 known advisories (SNAT-0030)**
  Snatch ships Pillow, which is what opens the picture previews it
  fetches from whatever site you are downloading from. The version in
  v1.0.0 and v1.0.1 had 12 published security advisories against it;
  all 12 are fixed in the version now bundled. Confirmed with
  pip-audit, which reports none remaining.

## [1.0.1] - 2026-08-20

### Fixed

- **Videos play again** (SNAT-0014)
  Most YouTube videos refused to play. The copy of yt-dlp inside Snatch was
  five months old and YouTube had changed how it serves video since. Updating
  it fixed every video we tested — 1 in 5 played before, 5 in 5 now.

  Worth knowing: this is pinned to yt-dlp's *nightly* channel rather than its
  stable releases. The current stable release does not fix the problem.
  YouTube changes faster than the stable channel ships, so a stable pin would
  mean a player that doesn't play.

- **Video plays inside the app again on Linux** (SNAT-0018)
  On a Wayland desktop the video opened in its own separate window instead of
  playing inside Snatch. mpv is now told to use XWayland, where embedding
  works. Windows was never affected.

- **Fullscreen** — double-click the video, use the Fullscreen button, or press
  Escape to come back. There was previously no way to do this.

- **In-app player on Windows** (SNAT-0013, partial)
  Windows builds now carry mpv, so the video player works without installing
  anything. Previously the Play button quietly opened a browser.

### Changed

- **The window title shows the version**, e.g. "Snatch v1.0.1".

## [1.0.0] - 2026-08-19

First public release. Snatch is a desktop app for downloading videos with
yt-dlp, and this is the first version published as a ready-to-run download
rather than something you clone and run from source.

### Added

- **Self-contained Windows build** (`snatch.exe`) (SNAT-0001)
  One file with Python, yt-dlp and ffmpeg inside it. Nothing to install.
- **Self-contained Linux build** (`Snatch-x86_64.AppImage`) (SNAT-0003)
  Download, mark it executable, run it.
- **Self-contained macOS build** (`Snatch-<arch>.dmg`) (SNAT-0004)
  A normal Mac app. It is not signed by Apple, so the first launch needs a
  right-click and Open — the README explains this.
- **Per-platform build scripts** in `scripts/`, called by both the local
  gate and GitHub Actions, so a local pass and a CI pass cannot drift apart.
- **Local CI gate** (`scripts/local-ci.sh`) that executes the real workflow
  through `act` instead of imitating it, and states plainly which jobs it
  could not run.
- **Seven-theme picker**: Dark, Nord, Monokai, YouTube, Dracula, Gruvbox
  and Solarized.

### Fixed

- **YouTube works without installing anything else** (SNAT-0010)
  Snatch now includes the small JavaScript engine yt-dlp needs to unscramble
  YouTube downloads. Previously it told you to go and install Node.js, which
  rather defeated the point of a one-file download.
- **The Play button no longer pretends to play** (SNAT-0012)
  On Windows there is no in-app player unless you install mpv, and Snatch was
  quietly opening the video in a browser instead. The button now says "Open in
  Browser" when that is what it will do, and the advice on how to get in-app
  playback is written for the system you are actually on — it used to say
  "sudo apt install mpv" on Windows and Mac.
- **The window title now shows the version**
  It said just "Snatch"; it now reads "Snatch v1.0.0".
- **Search returns in seconds, not most of a minute** (SNAT-0011)
  Searching looked like it did nothing. It was working — it just fetched full
  details for every result before showing any of them. A 20-result search went
  from about 40 seconds to a little over 3. The Resolution column in search
  results is blank as a result; everything else is unchanged.

### Changed

- **Renamed from YT-DLP GUI to Snatch** (SNAT-0002)
  Package, entry point, main class, window title, desktop entry, built
  artefact and the GitHub repository. The old repository address still
  redirects.
- **User data now goes to the right place on each platform.**
  Windows keeps data next to the .exe so the app stays portable. macOS uses
  `~/Library/Application Support/Snatch`, because writing inside a .app
  bundle breaks on upgrade. Linux uses the XDG data directory, because an
  AppImage's executable lives in a temporary directory that is deleted on
  exit.
- **One pinned source for bundled ffmpeg and ffprobe** across all three
  platforms, so there is a single version to bump.

[Unreleased]: https://github.com/milnet01/snatch/compare/v1.0.1...HEAD
[1.0.1]: https://github.com/milnet01/snatch/releases/tag/v1.0.1
[1.0.0]: https://github.com/milnet01/snatch/releases/tag/v1.0.0
