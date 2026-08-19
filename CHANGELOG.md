# Changelog

All notable changes to Snatch are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

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

[Unreleased]: https://github.com/milnet01/snatch/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/milnet01/snatch/releases/tag/v1.0.0
