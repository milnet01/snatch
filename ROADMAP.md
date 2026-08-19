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
  Decision (2026-08-19, user): code signing is DEFERRED, not pending. An Apple Developer account is ~$99/yr and is not worth it until these projects earn an income. So the unsigned bundle plus the README's right-click to Open instructions is the intended shipping state, not a gap to close. Do not re-raise signing as a defect; revisit only if the project starts making money.

- ✅ [SNAT-0005] **Publish the first release, v1.0.0.**
  Tag `v1.0.0` and attach the Windows .exe, the Linux AppImage and the
  macOS .dmg to a single GitHub Release. Blocked on SNAT-0003 and
  SNAT-0004 producing artefacts CI has actually built.
  Layman: The first proper download page, with a file for each system.
  Kind: release.
  Source: user-request-2026-08-19.
  Lanes: release, ci.
  Resolved (2026-08-19): published at https://github.com/milnet01/snatch/releases/tag/v1.0.0 — not a draft, not a prerelease, with all three artefacts attached: snatch.exe (93 MB), Snatch-x86_64.AppImage (92 MB), Snatch-arm64.dmg (86 MB). Release notes came from the CHANGELOG [1.0.0] section rather than generated from the commit log. The release job needs all three builds to succeed, so a partial set cannot be published; this was its first ever execution and it passed unchanged.

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

- ✅ [SNAT-0010] **Bundle a JavaScript runtime so YouTube works out of the box.**
  Reported by the user with a screenshot of Snatch's own "JavaScript
  Runtime Required" dialog on Windows. yt-dlp needs a JS runtime to solve
  YouTube's nsig challenges; without one, extraction is deprecated and
  formats go missing. The app bundled yt-dlp and ffmpeg but no runtime, so
  every release told the user to go install Node.js -- which contradicts
  the whole point of a self-contained download.

  Resolved (2026-08-19): bundle QuickJS (quickjs-ng v0.16.1, ~2 MB against
  Deno's ~40 MB) on all three platforms, and pass it to yt-dlp explicitly
  as --js-runtimes quickjs:<path>, since only deno is enabled by default.
  Verified: with the bundled binary yt-dlp exits 0 and the runtime warning
  disappears; without it the warning fires. Detection previously used
  shutil.which() only, so it could never have seen a bundled copy --
  _ensure_runtime_cache now lists the bundled runtime first so a release
  behaves the same on every machine. The dialog now fires only when there
  is no runtime at all, and says a downloaded release already includes one.
  **Layman:** YouTube downloads needed a separate program installed. Now it comes inside Snatch, so there is nothing extra to install.
  Kind: fix.
  Source: user-report-2026-08-19.
  Lanes: packaging, downloader.

- ✅ [SNAT-0011] **Make YouTube search return in seconds instead of most of a minute.**
  Reported as "when I try and search nothing happens", with the UI stuck
  on a "Searching......" label. The search was not failing: it ran
  yt-dlp -J, which FULLY EXTRACTS every result. Measured 2026-08-19 on a
  20-result search: ~40 s and 11.5 MB of JSON, with the UI showing no
  output until the very end.

  Resolved (2026-08-19): pass --flat-playlist, which lists results without
  extracting each video -- 3.3 s and 23 KB for the same search, and it
  emits none of the per-video JS-runtime warnings. Cost: flat entries
  carry no height/resolution, so that column in the results table is now
  blank. Everything else the table and the Play/Download buttons read
  (title, channel, duration, view_count, url) is present and verified.
  **Layman:** Searching looked like it did nothing. It was working, just very slowly -- now results come back almost immediately.
  Kind: perf.
  Source: user-report-2026-08-19.
  Lanes: search.

- ✅ [SNAT-0012] **Stop the Play button pretending to play when there is no player.**
  Reported as "tried to play multiple videos but they wouldn't play except
  for one" on Windows. Root cause: the embedded player shells out to mpv,
  which is neither bundled nor installed there -- confirmed on the test
  machine, where mpv, yt-dlp, ffmpeg, node and deno are all absent from
  PATH. With HAS_MPV false the code silently calls open_path(), so the
  video opens in a browser and nothing ever plays inside Snatch.

  Two earlier hypotheses were wrong and are recorded so nobody retries
  them: it is NOT the missing JS runtime (all five sampled GTA6 videos
  resolve 5/5 without one), and it is NOT a bad URL (full extraction
  leaves entry["url"] empty and the code correctly falls back to
  webpage_url).

  Resolved (2026-08-19): the button reads "Open in Browser" when no
  player is available, and the message explaining how to get in-app
  playback is now written for the platform it is shown on -- it said
  "sudo apt install mpv" on every platform, including Windows and macOS,
  the two least likely to have mpv already.
  **Layman:** On Windows the Play button quietly opened a web browser instead of playing in the app. Now it says so.
  Kind: fix.
  Source: user-report-2026-08-19.
  Lanes: player, ux.

- 📋 [SNAT-0013] **Bundle mpv so the in-app player works with nothing installed.**
  Chosen by the user 2026-08-19, deferred out of v1.0.0 as too large to
  block a release on. Scope and known costs, measured that day:

    Windows -- shinchiro build, 26 MB .7z, ships mpv.exe PLUS a set of
      DLLs, so this is a directory to bundle rather than one binary.
    Linux   -- pkgforge static AppImage, 42 MB. Bundling an AppImage
      inside our AppImage works but needs APPIMAGE_EXTRACT_AND_RUN.
    macOS   -- no plain binary exists; a .dmg containing a .app with
      frameworks. Hardest of the three and may not be worth it.

  Adds ~40 MB to every download (95 -> ~135 MB). Neither the Windows nor
  the macOS path can be tested locally, so expect several CI round trips.

  Also required, and easy to miss: bundled mpv must be told where the
  bundled yt-dlp is (--script-opts=ytdl_hook-ytdl_path=...) because mpv
  uses its OWN yt-dlp via ytdl_hook and never sees the app's command
  line -- which is also why bundling QuickJS alone did not fix playback.

  Rejected alternative: writing our own player. That means codecs, A/V
  sync and hardware acceleration; months of work for something worse than
  mpv, which is why the app shells out to mpv in the first place.
  **Layman:** Make the video player work inside the app on every system without the user installing anything.
  Kind: package.
  Source: user-request-2026-08-19.
  Lanes: packaging, player.

- ✅ [SNAT-0014] **Fix YouTube playback by pinning yt-dlp to a version that still works.**
  Reported as "most videos wouldn't play except for one" on BOTH Windows
  and Linux. The Linux half is what cracked it: mpv IS installed there,
  so a missing player could not be the cause.

  Measured on the five sampled GTA6 videos, using the app's own mpv
  invocation:
    yt-dlp 2026.03.17 (what we shipped)  1/5 play  <- matches the report
    yt-dlp 2026.07.04 (latest STABLE)    1/5 play  <- stable does NOT fix it
    yt-dlp 2026.08.18 (nightly)          5/5 play

  The failure mode was 403 Forbidden on the DASH stream URLs, which is the
  same error that killed the ffpyplayer prototype earlier the same day --
  one root cause, not two.

  Resolved (2026-08-19): scripts/fetch-binaries.sh now pulls yt-dlp from
  the nightly channel, pinned to the exact tag 2026.08.18.122307. Pinning
  to nightly is deliberate: YouTube breaks yt-dlp faster than the stable
  channel ships, so a stable pin here means a player that does not play.
  Bump the tag when playback or downloads start failing.

  Two corrections recorded so they are not repeated. Bundling mpv
  (SNAT-0013) would NOT have fixed this -- it was in progress when the
  Linux report arrived, and would have shipped 32 MB to Windows with
  playback still broken. And the JS runtime is not the fix either: the
  nightly plays 5/5 with no runtime supplied.
  **Layman:** Most videos would not play. The downloader tool inside Snatch was five months old and YouTube had changed; updating it fixed all of them.
  Kind: fix.
  Source: user-report-2026-08-19.
  Lanes: downloader, player, packaging.

- 📋 [SNAT-0015] **Add a Donate button pointing at the FUNDING.yml sources.**
  The three sources already live in .github/FUNDING.yml and are the ones
  to use:
    github  : milnet01            -> https://github.com/sponsors/milnet01
    patreon : AntsProjectsHub     -> https://patreon.com/AntsProjectsHub
    custom  : https://paybru.co.za/tip/ants-projects-hub

  Design notes for whoever picks this up.

  FUNDING.yml is NOT shipped inside a packaged build -- it is a repo file
  GitHub reads, and pyinstaller.spec bundles only icons and bin/. So the
  app cannot read it at runtime as things stand. Two options: add it to
  the spec's datas and parse it, or embed the URLs in code. If they are
  embedded, say in a comment that FUNDING.yml is the source of truth, or
  the two drift the first time a funding source changes.

  Use platform_utils.open_path() rather than a hand-rolled opener; it is
  already the cross-platform, injection-safe route and is what the History
  and Download tabs use. STANDARDS.md section 5 requires https-only for
  network URLs, which all three sources already are -- assert it rather
  than assume it, since the custom entry is free text in a YAML file.

  Placement is open. The header row next to the theme picker and version
  label is the obvious spot; a menu entry is the less intrusive one.
  **Layman:** A button in the app so people who like Snatch can support it, opening the same donation pages the GitHub page offers.
  Kind: feature.
  Source: user-request-2026-08-19.
  Lanes: ui, packaging.

- 📋 [SNAT-0016] **Let a packaged build fetch a newer yt-dlp into its own data directory.**
  Asked by the user 2026-08-19: can the Windows build download the latest
  yt-dlp? Today, no -- on any platform. A packaged build's yt-dlp sits in
  the PyInstaller extraction directory, which is read-only and deleted on
  exit, so it cannot replace itself. SNAT-0016's sibling fix made the app
  say so instead of failing confusingly.

  Why this matters rather than being a nicety: YouTube breaks yt-dlp
  faster than we cut releases. That is not hypothetical -- it is exactly
  what SNAT-0014 was. Without this, every such break needs a new Snatch
  release on three platforms, and users are stuck until then.

  Shape of the fix. app_data_dir() is already writable and already
  platform-correct (next to the .exe on Windows, ~/Library/Application
  Support on macOS, XDG data dir under an AppImage). Download the release
  asset for the platform into <app_data_dir>/bin/, and have find_ytdlp()
  prefer that copy over the bundled one when it exists. The bundled copy
  stays as the floor, so a failed or half-written download can never leave
  the app with no yt-dlp.

  Things not to get wrong:
    - Verify the download RUNS (--version) before preferring it; a
      truncated file must not replace a working bundled binary.
    - Download to a temp name and rename, so a crash mid-write leaves the
      previous state intact.
    - 0700 on the directory, executable bit on the binary.
    - HTTPS only, per STANDARDS.md section 5.
    - Offer a way back to the bundled copy when a fetched one misbehaves.
    - Which channel? SNAT-0014 pins NIGHTLY because stable does not play
      YouTube. A self-update that pulls stable would be a downgrade.
  **Layman:** Let the app update its downloader by itself, so when YouTube changes you do not have to wait for a new version of Snatch.
  Kind: feature.
  Source: user-request-2026-08-19.
  Lanes: downloader, packaging.
