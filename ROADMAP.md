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

- ✅ [SNAT-0019] **build-linux still hangs on apt-get intermittently.**
  The "Install Tk runtime and X libraries" step in build-linux
  intermittently hangs. Observed 2026-08-19 on run 32299765938 (commit
  ceb4cd4): 25 minutes with no progress, cancelled manually.

  What is already ruled out, so it is not retried: ceb4cd4 INCLUDES the
  workflow-level DEBIAN_FRONTEND=noninteractive + NEEDRESTART_MODE=a fix
  from 881420e. That fix is real but partial -- it took static-checks from
  780s+ (hanging) to 135s -- and it did not stop this. So needrestart was
  not the whole cause, and the earlier claim that the class was fixed was
  premature.

  It is INTERMITTENT, not deterministic: run for f991184 passed build-linux
  normally in between two hanging runs. That points at runner-side apt
  contention (an unattended-upgrades lock, or a slow mirror) rather than
  anything in this repo.

  Not urgent because timeout-minutes: 30 bounds it -- the job fails in 30
  minutes instead of GitHub's 6-hour default -- but it wastes a full CI
  cycle each time and makes a red run ambiguous.

  Worth trying, cheapest first:
    - -o DPkg::Lock::Timeout=120 so apt waits for the lock instead of
      blocking forever on it.
    - Retry the step (2 attempts) rather than failing the run.
    - Check which of these packages the ubuntu-22.04 runner image ALREADY
      ships; if only libxcursor1 and friends are genuinely missing, the
      step shrinks and so does the exposure.
    - Last resort: drop apt entirely and vendor what PyInstaller needs.

  Cannot be reproduced locally: act's container has no needrestart and no
  unattended-upgrades, which is the same blind spot documented in
  scripts/local-ci.sh and docs/building.md.
  Resolved (2026-08-20): a1cf34c. Cause was never pinned down, so all
  three plausible ones are bounded rather than guessed between:
  DPkg::Lock::Timeout=120 makes apt wait for a held lock instead of
  blocking on it, Acquire::Retries=3 + Acquire::http::Timeout=30 make a
  stalled mirror fail and retry, and timeout(1) at 300s per attempt kills
  one that hangs anyway so the outer 2-attempt retry can happen.

  Both apt call sites now go through scripts/apt-install.sh rather than
  repeating the options inline -- fixing build-linux and missing
  static-checks is exactly what happened with needrestart, and ci.yml's
  env block says so in its own comment, so the shared script makes that
  recurrence structural rather than a thing to remember.

  Verified on the runner, not just locally: run 32348969527 (a1cf34c) and
  run 32349272675 (v1.0.1 tag) both took all four jobs green, build-linux
  included. The hang is intermittent so this is not proof it can never
  recur, but the 30-minute unbounded case is now bounded at ~10.

  Side effect worth knowing: static-checks installs shellcheck with
  --no-install-recommends now, which it did not before. That follows from
  sharing the helper and only narrows what gets installed.
  **Layman:** One of our automated build steps sometimes freezes and has to be killed. It is not consistent, so it has not been pinned down yet.
  Kind: fix.
  Source: in-session-2026-08-19.
  Lanes: ci.

- 📋 [SNAT-0024] **CI builds three artifacts and never starts one.**
  build-linux, build-windows and build-macos each produce a file and
  upload it. Nothing anywhere launches the thing that was produced. A
  bundle that builds cleanly and then dies on startup -- a missing shared
  library, a bad PyInstaller hidden import, a broken entry point -- is
  green in CI and broken for the user.

  This class of failure is not hypothetical here. SNAT-0010 and SNAT-0013
  were both "the build was fine, the thing it produced could not do its
  job", and the libXcursor finding during the SNAT-0018 work was caught
  only because someone ran the job under act and read the log.

  A smoke test does not need to drive the GUI. Starting the app, letting
  it initialise, and exiting cleanly would catch the whole class. Options,
  cheapest first:
  - A --version or --selftest flag that constructs nothing GUI-shaped,
  prints, and exits 0. Cheap, and useful to a user diagnosing a
  problem too.
  - xvfb-run on Linux to start the real GUI headless and close it. The
  Windows and macOS runners have a desktop session and need no
  equivalent.

  Pairs with SNAT-0020, which covers the logic underneath; this one
  covers the packaging, which is where this project's failures have
  actually been.
  **Layman:** Our automated builds check that the app can be packaged, not that the packaged app actually opens.
  Kind: test.
  Source: in-session-2026-08-20.
  Lanes: ci, packaging.

- 📋 [SNAT-0025] **Nobody has ever run the macOS build.**
  SNAT-0004 shipped a macOS .app and .dmg and SNAT-0005 published it;
  v1.0.1 attaches Snatch-arm64.dmg today. No human has ever launched it.
  SNAT-0007 did exactly this job for Windows and found real problems, and
  the Mac has had no equivalent.

  What makes it more than routine caution rather than less:
  - The build is arm64 only. An Intel Mac has nothing to run.
  - It is deliberately unsigned (SNAT-0004), so first launch needs the
  Gatekeeper workaround the README describes -- and that workaround
  has never been performed by anyone either.
  - yt-dlp's macOS asset is a different file (yt-dlp_macos) from the
  other two platforms, and SNAT-0016's self-update names it in
  snatch/version.py with no test and no run behind it.
  - mpv is NOT bundled for macOS, so in-app playback falls back to a
  browser there.

  This is an investigate item, not a fix: the deliverable is knowing
  whether it works. It needs Mac hardware, which this project does not
  have -- so the honest options are to find someone with a Mac, add a
  smoke test on CI's macos runner (SNAT-0024, which would at least prove
  it starts), or say plainly in the README that the Mac build is
  untested. The last is free and should probably happen regardless.
  **Layman:** We ship a Mac version that no one has ever opened. It might not work at all.
  Kind: investigate.
  Source: in-session-2026-08-20.
  Lanes: packaging, macos.

- 📋 [SNAT-0026] **Every launch unpacks ~100 MB to a temp directory before anything appears.**
  Measured 2026-08-20 on this machine (NVMe, warm page cache), on the
  v1.0.1 AppImage, three runs: 0.97s, 0.97s, 0.96s from exec to the point
  Python gives up on the display. That is unpack plus import, BEFORE any
  window is drawn, and before Tk initialises. A cold cache or a spinning
  disk is worse.

  Where it goes. The AppImage's own squashfs extraction is 0.06s -- fast
  and not the problem. Inside it sits a single 101 MB PyInstaller
  ONE-FILE binary, and one-file means the embedded archive is
  decompressed to /tmp/_MEIxxxx on every start, used, and deleted.
  Roughly a second of that ~0.97s is paying for a 100 MB decompress that
  produces exactly the same bytes it produced last time.

  The key point: an AppImage is ALREADY a single-file distribution. It
  mounts a squashfs and runs from it. Wrapping a PyInstaller one-file
  archive inside one is double-packing -- paying the extraction cost
  twice over for a property the outer format already provides. Building
  --onedir inside the AppImage would let it mount and execute in place,
  removing essentially all of that second.

  Same argument for macOS: a .app is a directory bundle by nature, so
  one-file buys nothing there either.

  Windows is the exception and should KEEP one-file. A single portable
  snatch.exe is the point on that platform, and app_data_dir() is built
  around it. Note this is also the cause of the stale-_MEI confusion in
  the 2026-08-19 Windows testing, so if one-file stays there, the
  mitigation is documentation rather than a build change.

  Pairs with SNAT-0027: less to unpack is the other half of this, and the
  two multiply.
  **Layman:** Snatch takes about a second to start because it unpacks itself from scratch every single time you open it.
  Kind: perf.
  Source: in-session-2026-08-20.
  Lanes: packaging, performance.

- 📋 [SNAT-0027] **ffmpeg and ffprobe are 153 MB of near-duplicate binary.**
  Measured in bin/ on 2026-08-20: ffmpeg 77 MB, ffprobe 76 MB, yt-dlp
  3.0 MB, qjs 2.5 MB. So 153 MB of a ~158 MB payload is those two, and
  they come from the same static build (eugeneware/ffmpeg-static b6.1.1)
  with different entry points -- the great majority of those bytes are
  the same codec and container code linked twice.

  What it costs, in order of who feels it:
  - Every launch, via SNAT-0026: the one-file archive decompressed on
  start is mostly these two files.
  - Every download: 92 MB AppImage, 138 MB snatch.exe, 88 MB dmg.
  - Every CI run, on three runners.

  Worth trying, cheapest first:
  - Check whether ffprobe is needed at all. yt-dlp is given
  --ffmpeg-location and can use ffmpeg for muxing; the Media Info tab
  is the one place that genuinely calls ffprobe (tabs/media_info.py).
  If that tab can read what it needs from ffmpeg, one 76 MB file goes.
  - Look for a smaller static build. b6.1.1 is a full-feature build
  with every codec; a downloader front-end needs a fraction of them.
  BtBN and John Van Sickle publish leaner variants.
  - Last resort, and only if the above fail: accept the size and let
  SNAT-0026 recover the launch time instead.

  Do NOT solve this by dropping to a system ffmpeg. Bundling is
  deliberate -- it is why a downloaded release works with nothing
  installed -- and SNAT-0028's distro packages are the place where
  depending on the system copy is the right answer.
  **Layman:** Two of the bundled tools are almost the same program shipped twice, and together they are most of the download.
  Kind: perf.
  Source: in-session-2026-08-20.
  Lanes: packaging, performance.

- 📋 [SNAT-0028] **Publish Snatch on the openSUSE Build Service for as many distros as it will build for.**
  Asked by the user 2026-08-20. The account already has home:milnet on
  build.opensuse.org with two subprojects (ants-terminal, finbreak), so
  the pattern and the credentials exist -- this is home:milnet:snatch
  alongside them.

  Why it is worth doing beyond reach: OBS builds one source package for
  many targets at once. openSUSE Tumbleweed and Leap, Fedora, RHEL
  derivatives, Debian, Ubuntu and Arch are all reachable from one spec,
  and the user's own machine is Tumbleweed, so the first target is also
  the one that can be tested immediately.

  The real prize is size and updates. A native package does NOT bundle
  ffmpeg, mpv or Python -- it declares them as dependencies, so the
  package is the ~180 KB of Snatch's own code instead of 92 MB, it
  unpacks nothing at startup (SNAT-0026 stops applying entirely), and it
  updates through the user's package manager like everything else.

  The tension to decide before starting, because it shapes the spec:
  SNAT-0014 pins yt-dlp to the NIGHTLY channel because stable does not
  play YouTube, and no distro ships a nightly yt-dlp -- most are months
  behind. So a package depending on the distro's yt-dlp is a package
  that cannot play YouTube on the day it lands. SNAT-0016 is the way
  out: the packaged app fetches its own yt-dlp into app_data_dir()/bin
  and prefers it. That has to be verified working from a distro package,
  where the app itself is read-only and installed system-wide, before
  this is worth publishing.

  Other things not to get wrong:
  - Needs python3-tkinter as a hard dependency. It is a separate
  package on most distros and the app cannot start without it.
  - mpv and ffmpeg become Recommends or Requires rather than bundled
  content; the in-app player already degrades gracefully without mpv
  (SNAT-0012).
  - The desktop file and icon become real installed files rather than
  AppImage internals.
  - Needs a source tarball per release, which the GitHub release does
  not currently produce in a form OBS can consume directly.
  - OBS can watch a git repo and rebuild on a tag; worth wiring so
  this does not become a manual step per release.

  Does NOT replace the AppImage. That stays for distros OBS does not
  cover and for users who want no installation at all.
  **Layman:** Put Snatch in the normal software installers for Linux, so people can install and update it the way they install everything else.
  Kind: package.
  Source: user-request-2026-08-20.
  Lanes: packaging, distribution.

- 📋 [SNAT-0035] **Harden the CI workflow: unpinned actions, repo-wide write, persisted credentials.**
  zizmor --persona=auditor on .github/workflows/ci.yml, 2026-08-20.
  Three distinct issues, worst first.

  1. unpinned-uses, 13 occurrences. Every `uses:` names a mutable tag
  (actions/checkout@v4, actions/setup-python@v5,
  actions/upload-artifact@v4, softprops/action-gh-release and so on).
  A tag is a pointer its owner can move. Whoever controls one of those
  repos can change what our workflow executes without a commit here,
  and that code runs in a job holding a token that can write to this
  repository and publish releases. Fix: pin each to a full commit SHA
  with the version as a trailing comment. `pinact run` does this
  mechanically. Note this is the same class SNAT-0009 already tracks
  for the appimagetool runtime, and the same class as SNAT-0031 for
  binaries -- three instances of one habit.

  2. excessive-permissions at line 17. `permissions: contents: write` is
  set at WORKFLOW scope, so all five jobs get it -- including
  static-checks and the three builds, which only read. Only `release`
  needs to write. Fix: `contents: read` at the top and a job-level
  `permissions: contents: write` on release alone. This shrinks what a
  compromised action from issue 1 can reach, which is why the two are
  one item.

  3. artipacked, 5 occurrences. actions/checkout persists the credential
  in .git/config by default, and these jobs upload build artifacts.
  Fix: `persist-credentials: false` on every checkout; no step here
  needs the token afterwards.

  None is exploited or exploitable today, and no evidence suggests
  otherwise -- this is a public repo whose workflow currently has more
  authority than any job in it uses. Worth doing because the release job
  can publish artifacts under the project's name, which is the thing an
  attacker would actually want.

  Worth adding zizmor to static-checks afterwards so this cannot silently
  regress; the tool is already installed on the dev machine.
  **Layman:** Our automated build has more power over the project than it needs, and trusts outside code that could change under us.
  Kind: security.
  Source: in-session-2026-08-20.
  Lanes: security, ci, supply-chain.

- 📋 [SNAT-0036] **Releases publish no checksums, so a download cannot be verified.**
  v1.0.1 attaches exactly three assets -- Snatch-arm64.dmg,
  Snatch-x86_64.AppImage, snatch.exe -- and nothing else. No
  SHA256SUMS file, no signature, no attestation.

  So a user who downloads a 138 MB snatch.exe has no way to tell it is
  ours, and neither do we if a report comes in. That matters more than
  usual for this project on two counts: the macOS build is deliberately
  unsigned (SNAT-0004), so Gatekeeper is explicitly bypassed by a
  README-documented workaround, and the Windows .exe is unsigned too --
  checksums are the only integrity signal on offer for either.

  Cheapest useful version: have the release job emit a SHA256SUMS file
  over the three artifacts and attach it, then document the one-line
  verify command per platform in the README next to the download links.
  That costs a few lines in ci.yml and is worth doing regardless of what
  follows.

  Better, and not much harder now that it is a public repo: GitHub's
  build attestations (actions/attest-build-provenance) sign artifacts
  with the workflow identity and need no key management. Worth choosing
  between the two rather than doing both.

  Deliberately NOT proposing paid code signing -- SNAT-0004 settled that
  for macOS on cost grounds and that decision stands. Checksums and
  attestation are the free part of what signing would have given, and
  they are not a substitute for it.

  This is SNAT-0031's question turned around: that one is about verifying
  what we consume, this is about letting others verify what we ship.
  **Layman:** Someone downloading Snatch has no way to check the file they got is the one we published.
  Kind: security.
  Source: in-session-2026-08-20.
  Lanes: security, release, supply-chain.

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
  Progress (2026-08-20): diagnosed, still open, and the obvious fix is
  already in the code and does nothing.

  All three write sites DO request 0600 today, and have since 40b5c9e:
  app.py:147 and tabs/history.py:72 both use
  os.open(path, O_WRONLY|O_CREAT|O_TRUNC, 0o600), and cookies.py does the
  same at :93 plus explicit chmods at :72 and :77.

  The files on disk are still wrong. Measured today in the project root:
  config.json 664, cookies.txt 664, history.json 644.

  Why: the mode argument to os.open applies ONLY when the call creates
  the file. These files already existed, so O_TRUNC reuses the existing
  inode and its existing permissions, and the 0o600 is silently ignored.
  Every one of these users' files was created before the mode argument
  was added, and no amount of re-saving will ever narrow them.

  So this item cannot be closed by auditing the write sites -- they
  already pass. It needs an explicit os.chmod(path, 0o600) after opening
  an EXISTING file, or a one-time tightening pass over app_data_dir() at
  startup. The second is better: it also catches a file a user copied in
  from an old install, which is exactly how the current ones got here.

  Worth calling out because this is the shape of bug that gets marked
  fixed while staying broken -- the code review passes, the code looks
  right, and the permissions never change. A test asserting the mode of
  an existing file after a save would have caught it (SNAT-0020).

  cookies.txt is the one that matters: it carries session tokens.

- ✅ [SNAT-0007] **Verify the GUI renders on Windows from a real desktop session.**
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
  Resolved (2026-08-19): confirmed by the user on the real machine. The GUI renders, the theme and icon load, search returns results, and video plays inside the app's own player frame. This was open because every earlier Windows test ran over SSH, which has no interactive desktop -- MainWindowHandle was 0 and mpv drew into a window nobody could see, so the embedding path (mpv into a Tk frame via --wid) was the one thing a headless test could never exercise.

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

- ✅ [SNAT-0013] **Bundle mpv so the in-app player works with nothing installed.**
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
  Windows half SHIPPED and user-confirmed (2026-08-19): the build bundles mpv v0.41.0 (32 MB, mpv.exe plus its DLLs) and points it at the bundled yt-dlp via ytdl_hook-ytdl_path. Verified on real hardware with no mpv, yt-dlp, ffmpeg or Python installed; the user then confirmed video plays in the app window.

  STILL OPEN for macOS: no plain mpv binary exists there, only a .dmg carrying a .app with frameworks. Linux needs nothing -- system mpv is used and works.

  Recorded so it is not misread later: bundling mpv was NOT what fixed playback. SNAT-0014 was -- a five-month-stale yt-dlp. This item makes an in-app player EXIST on Windows, where none was installed.
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

- ✅ [SNAT-0016] **Let a packaged build fetch a newer yt-dlp into its own data directory.**
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
  Resolved (2026-08-20): 5a733ad. Built to the shape this bullet
  describes. user_bin_dir() adds a writable bin/ inside app_data_dir();
  find_ytdlp() prefers a copy there and falls back to the bundled binary,
  which stays as the floor.

  Every item on this bullet's "things not to get wrong" list is covered:
  --version probe before promoting, temp name + os.replace in the SAME
  directory so the rename is atomic, 0700 on the file and the directory,
  HTTPS-only, revert-to-bundled offered whenever a fetched copy is in use,
  and the nightly channel -- not stable.

  Scope was narrowed to yt-dlp alone by user decision 2026-08-20. It is
  the only bundled tool that goes stale on someone else's schedule; mpv
  alone is 26 MB to re-download for a problem that does not occur. The
  trigger is check-on-startup-and-ask, also user-chosen: automatic was
  rejected as downloads nobody asked for, manual-only as no hint when
  YouTube breaks.

  One thing this bullet did not anticipate, found while building.
  app_data_dir() is described here as "already writable" and on Windows it
  is not always: it returns the directory holding the .exe, which needs
  admin rights under C:\Program Files. Only bin/ falls back, to
  %LOCALAPPDATA%\Snatch\bin -- config.json and history.json stay where
  they are, because moving them would strand an existing user's settings.

  Two live bugs fixed on the way, both worse than the missing feature.
  The version check AND the download both used yt-dlp/yt-dlp's latest
  release -- the STABLE channel that SNAT-0014 established does not play
  YouTube -- so pressing Update would have moved a working setup onto a
  broken one. And the install shelled out to curl plus a pkexec write into
  /usr/local/bin, asking for a password to change a file outside the app;
  staying inside Snatch's own directory removed the privileged step rather
  than guarding it.

  Verified end to end on Linux from source: the check resolved nightly
  2026.08.19.233000 against the bundled 2026.08.18.122307, downloaded it,
  probed it, landed it 0700 with no temp file left behind, find_ytdlp()
  then preferred it, a junk file was refused by the probe, and deleting it
  fell back to the bundled copy. local-ci.sh full run green; CI run
  32350687160 green on all four jobs.

  NOT verified: the Windows %LOCALAPPDATA% fallback and the macOS asset
  name (yt-dlp_macos) are exercised by no test here -- act cannot run
  those jobs. Both are one real run away from being confirmed, and the
  Windows box at 192.168.0.102 can settle the first.
  **Layman:** Let the app update its downloader by itself, so when YouTube changes you do not have to wait for a new version of Snatch.
  Kind: feature.
  Source: user-request-2026-08-19.
  Lanes: downloader, packaging.

- ✅ [SNAT-0018] **Embed the player on Wayland instead of opening a separate window.**
  Reported by the user: Windows plays inside the app, Linux opens a
  separate window. Not a regression -- a platform difference nobody had
  isolated.

  Cause: the session is Wayland (XDG_SESSION_TYPE=wayland). tkinter runs
  under XWayland, so player_frame.winfo_id() is an X11 window id, but mpv
  sees WAYLAND_DISPLAY and picks its Wayland backend, which cannot embed
  into an X11 window -- so it opens its own. Windows has no such split.

  Resolved (2026-08-19): WAYLAND_DISPLAY is dropped from mpv's child
  environment only, so mpv falls back to X11 through XWayland where --wid
  works. Guarded on DISPLAY being present, so a pure-Wayland box with no
  XWayland is left alone rather than handed a broken environment; X11
  sessions are unaffected.

  Measured, since "it looks embedded" is not evidence: with the parent
  environment mpv created 0 X11 windows (it went to Wayland). With the fix
  it created 1, geometry 620x380 -- exactly the Tk frame's size, which is
  the signature of a reparented window.

  Also added, because there was none: fullscreen via a button, a
  double-click on the video area, and Escape to leave. Known limitation --
  an embedded surface cannot go fullscreen independently of the window
  that owns it, so this makes the WINDOW fullscreen and the video grows
  with it; the rest of the UI stays on screen. True video-only fullscreen
  would mean detaching the player into its own window, which is a
  different design.
  **Layman:** On Linux the video opened in its own window instead of inside the app. It now plays inside, and there is a fullscreen button.
  Kind: fix.
  Source: user-report-2026-08-19.
  Lanes: player, ui.

- 📋 [SNAT-0020] **The app has no automated tests at all.**
  3,865 lines of Python across four platforms' worth of behaviour, and
  the only Python check in CI is `python -m compileall`, which proves the
  files parse and nothing more.

  This is not theoretical. On 2026-08-20, while building SNAT-0016, two
  live bugs were found in snatch/version.py that had shipped through both
  v1.0.0 and v1.0.1: the update path downloaded from yt-dlp's STABLE
  channel, which SNAT-0014 had already established does not play YouTube,
  so pressing Update would have moved a working install onto a broken one;
  and it shelled out to pkexec to write into /usr/local/bin, asking for a
  password to modify a file outside the app. Neither was caught by
  anything. They were found by a person reading the file for an unrelated
  reason.

  What is worth testing first, in value order -- this does NOT need to be
  a suite covering everything:
  - The pure logic that already has no GUI in it: _version_compare,
  _is_valid_url, _safe_resolve_path, format filtering and sorting.
  These are the cheapest tests in the codebase and cover the parts
  where a silent wrong answer is most likely.
  - Binary resolution: find_ytdlp / user_bin_dir / _find_updated_binary,
  including the Windows LOCALAPPDATA fallback. The ad-hoc scripts
  written during SNAT-0016 already do exactly this and were thrown
  away afterwards; they should have been committed.
  - The self-update promotion rule, which is the one place a bad file
  can replace a working binary.

  Deliberately out of scope for a first pass: driving the tkinter GUI.
  That is a large, flaky category of test and the value is in the logic
  underneath it.

  Needs a `test` job in ci.yml, or the suite exists and nothing runs it.
  Correction (2026-08-20, same day): this bullet's "no automated tests at
  all" overstates it, and the overstatement is worth fixing rather than
  leaving as rhetoric.

  scripts/verify_platform_utils.py exists and runs in ALL THREE build
  scripts (build-linux.sh:20, build-windows.sh:20, build-macos.sh:22)
  plus local-ci.sh:68. It carries two real asserts -- app_data_dir()
  exists, and find_ytdlp() did not fall through to the bare literal --
  so a failure does fail the build. That is a genuine gate, and it runs
  on Windows and macOS where nothing else does.

  What the bullet gets right is unchanged: two asserts over one module is
  not a test suite for 3,865 lines, and neither assert would have caught
  either version.py bug. The accurate claim is "one two-assert smoke
  check on one module, run at build time", not "nothing".

  This also revises the starting point. The item is no longer "introduce
  testing", it is "there is a place tests already run from -- grow it and
  give it a real runner". That is a cheaper first step than the bullet
  implies, and verify_platform_utils.py is where the binary-resolution
  tests it asks for should probably live.

  Found by measuring for SNAT-0026 and noticing the file in scripts/. The
  original bullet was written from a `wc -l snatch/*.py` that also missed
  snatch/tabs/ entirely -- the same glob, the same blind spot, and the
  reason its line count read 2,712 rather than 3,865.
  **Layman:** Nothing automatically checks that Snatch still works after a change, so a mistake can reach users unnoticed.
  Kind: test.
  Source: in-session-2026-08-20.
  Lanes: testing, ci.

- 📋 [SNAT-0021] **Nothing tells the user a newer Snatch exists.**
  SNAT-0016 gave the app a way to keep yt-dlp current. Snatch itself
  still has no way to say "there is a 1.1.0" -- a user who downloaded
  v1.0.0 has no signal that anything newer was ever published, short of
  visiting the releases page on a hunch.

  This is the cheap half of the problem SNAT-0016 solved, and most of the
  parts already exist: version.py already queries a GitHub releases API,
  parses a tag and compares versions, and the app already knows its own
  version because SNAT-0018 put it in the window title.

  Scope this as NOTIFY, not self-replace. Downloading and swapping the
  running executable is a materially harder and riskier job on all three
  platforms -- and on macOS an unsigned replacement is worse than no
  replacement (SNAT-0004). Checking github.com/milnet01/snatch's latest
  release and showing a dismissible "v1.1.0 is available" with a link is
  the whole feature.

  Things not to get wrong:
  - Do not nag. Once per launch at most, and remember a dismissal.
  - Fail silently when offline. A version check must never block
  startup or produce an error dialog for a user with no network.
  - Compare against the app's own version, not yt-dlp's. Those are two
  unrelated version lines and version.py already holds the other one.
  Superseded (2026-08-20) by SNAT-0038. Do not build this one.

  This bullet deliberately scoped the feature to NOTIFY ONLY, on the
  grounds that downloading and swapping a running executable is a
  materially harder job on three platforms. The user asked the same day
  for the full thing -- offer, cumulative changelog, install, relaunch --
  and named /mnt/Games/Scripts/Linux/finbreak as a working reference.
  That decision stands and SNAT-0038 carries it.

  The caution was not wrong, it was just answerable: finbreak has shipped
  exactly this since v0.1.0 and its hard-won parts are readable rather
  than theoretical -- the AppImage FUSE-mount swap, the Windows locked
  .exe helper, the inert-when-unsupported branch, HTTPS on redirects, and
  an anti-rollback gap still open over there.

  The one part of this bullet's reasoning SNAT-0038 keeps: macOS stays
  out. Unsigned (SNAT-0004), never run by anyone (SNAT-0025), and no
  reference implementation to copy.

  The other part it keeps is the small stuff this bullet got right and
  which is easy to lose in a bigger feature: do not nag, fail silently
  when offline, and compare against the APP's version rather than
  yt-dlp's -- version.py holds the other version line and the two are
  unrelated.
  **Layman:** Snatch can now update its downloader, but it cannot tell you when Snatch itself has a new version.
  Kind: feature.
  Source: in-session-2026-08-20.
  Lanes: application.

- 📋 [SNAT-0022] **Failures vanish -- there is no log and 11 handlers swallow errors silently.**
  The app imports no logging module anywhere. Alongside that there are
  11 handlers whose body is `pass`, and 15 `except Exception` clauses
  across five modules.

  Some of those are correct -- ignoring an OSError while unlinking a temp
  file is right. Others silently discard the reason a real feature did
  not work: a thumbnail that never appears, a config that never saves, a
  cookie extraction that quietly returns nothing. From the user's side
  these are indistinguishable from the app deciding not to bother.

  The cost lands on the user, and it landed on this project already: the
  Windows "binary missing" report on 2026-08-19 turned out to be a stale
  _MEI extraction directory, and finding that took a round trip to real
  hardware because there was no log to read.

  Shape of the fix:
  - A rotating log file in app_data_dir(), written 0600 like every other
  user data file, capped so it cannot grow without bound.
  - A way to open it from the GUI, so a bug report can carry it.
  - Then walk the 11 silent handlers and split them: keep the ones that
  are genuinely ignorable and say so in a comment, log the rest.

  Not a rewrite of the error handling. The point is that a failure
  leaves a trace somewhere, not that every failure becomes a dialog.
  **Layman:** When something goes wrong, Snatch often says nothing and keeps no record, so there is nothing to send when reporting a problem.
  Kind: fix.
  Source: in-session-2026-08-20.
  Lanes: application.

- 📋 [SNAT-0023] **The download queue is lost when the app closes.**
  self.download_queue is a plain list built at startup (app.py:70) and
  reset on close (app.py:327). It is never written anywhere. Every other
  preference the app holds is persisted -- _save_config writes twelve
  keys including window geometry and the last tab you were on -- so the
  queue is the one piece of user intent that is thrown away.

  The case that hurts: queueing a long playlist, closing the laptop, and
  finding an empty queue. The work of re-adding it is exactly the work
  the queue existed to save.

  Already in place: entries carry a status field ("Done", "Failed") and
  _refresh_queue_tree rebuilds the view from the list, so restoring is
  repopulating that list rather than new UI.

  Things not to get wrong:
  - The queue holds URLs the user pasted. Persist it 0600 like config
  and history, not world-readable.
  - Restore items as pending, never mid-download -- a partially written
  file from a killed process must not be treated as resumable without
  checking.
  - Offer to clear it. A stale queue from three weeks ago that starts
  downloading on launch is worse than losing it.
  **Layman:** If you queue up a batch of videos and close Snatch, the queue is gone when you reopen it.
  Kind: enhancement.
  Source: in-session-2026-08-20.
  Lanes: downloader.

- 📋 [SNAT-0029] **Pillow is imported at startup for a feature most launches never use.**
  Measured 2026-08-20 with `python3 -X importtime -c "import snatch.app"`:
  134 ms total, of which PIL.Image accounts for 77 ms -- 57% of the app's
  entire import cost. PIL._imaging alone, the C extension, is 56 ms.

  It is imported at the top of snatch/downloader.py:20 and used in exactly
  one place, downloader.py:237, to decode a thumbnail after formats have
  been fetched for a URL. So every launch pays for it, and a launch that
  goes to the Search, Media Info or History tab -- or that opens and
  closes without pasting a URL -- never touches it.

  Moving the import inside the thumbnail branch cuts app import time
  roughly in half. HAS_PIL is the only complication: it is used as a
  module-level flag at the call site, so the pattern needs to become a
  cached check rather than an import-time constant. That is a small,
  contained change and the flag has one reader.

  Worth doing even though SNAT-0026 dwarfs it (~970 ms of unpack against
  77 ms here). They are independent: SNAT-0026 is a packaging change,
  this is a source change, and a distro package (SNAT-0028) has no unpack
  cost at all -- so on the platform where startup is otherwise instant,
  this becomes the largest remaining item.

  Also worth a look while in there: urllib.request costs 15 ms at import
  in snatch/version.py and is only ever used inside worker threads.

  NOT worth chasing, measured and ruled out the same day: 4x shutil.which
  for JS runtime detection is 0.2 ms and already cached at class level;
  inserting 200 history rows into the Treeview is 1.6 ms; Tk() itself is
  51 ms and is not ours to optimise. The format filter already reads
  pre-computed video_only / audio_only booleans rather than re-parsing,
  the download loop already throttles UI updates to 150 ms, history is
  cached in memory, and search already uses --flat-playlist (SNAT-0011).
  The hot paths are in good shape -- the cost is in packaging.
  **Layman:** Snatch loads its image library every time it opens, even though it is only needed to show a video's thumbnail.
  Kind: perf.
  Source: in-session-2026-08-20.
  Lanes: application, performance.

- ✅ [SNAT-0030] **Shipped Pillow has 12 known advisories, and it decodes images from the internet.**
  pip-audit against requirements.txt on 2026-08-20 reports 12 advisories
  against Pillow 12.2.0, every one of them fixed in 12.3.0:
  PYSEC-2026-2253/2254/2255/2256, 3451/3452/3453/3454, 3493/3494/3495/3496.

  This is the one finding on the roadmap with a live attack path rather
  than a hardening argument. downloader.py:237-244 takes the thumbnail
  URL out of yt-dlp's JSON for whatever URL the user pasted, fetches it,
  and hands the bytes to PIL.Image.open. So the input to a decoder with
  12 open advisories is an image chosen by whoever controls the site
  being downloaded from. For a tool whose entire purpose is pasting links
  from arbitrary sites, that is not a remote scenario.

  Pillow is bundled into all three released artifacts, so v1.0.0 and
  v1.0.1 both carry it.

  The fix is one line -- Pillow==12.3.0 in requirements.txt -- plus a
  rebuild. Verify with pip-audit afterwards rather than assuming.

  Not assessed here: which of the 12 are reachable through the specific
  call path above, or their individual severities. That triage is worth
  less than the upgrade, because the upgrade closes all 12 regardless
  and costs a version bump.

  The systemic half is SNAT-0037: nothing was watching, and these have
  been public for some time.
  Resolved (2026-08-20): requirements.txt now pins Pillow==12.3.0.
  Verified rather than assumed -- `pip-audit -r requirements.txt`
  reported the 12 advisories before the bump and "No known
  vulnerabilities found" after it. A full scripts/local-ci.sh run is
  green, so the Linux AppImage builds against 12.3.0; the Windows and
  macOS wheels are unexercised locally and are covered by the push.
  The systemic half -- nothing was watching for this -- is still
  SNAT-0037.
  **Layman:** The image library Snatch ships has 12 published security problems, and it is what opens picture previews downloaded from the web.
  Kind: security.
  Source: in-session-2026-08-20.
  Lanes: security, dependencies.

- 📋 [SNAT-0031] **Five bundled binaries are downloaded and executed with no integrity check.**
  scripts/fetch-binaries.sh's fetch() curls a URL, moves the result into
  bin/, and chmod +x it. There is no hash comparison, no signature check,
  and no checksum file anywhere in the repo -- grepping for
  sha256/shasum/checksum/gpg across scripts/ and the workflow returns
  nothing but an unrelated comment in build-macos.sh.

  Five third-party executables arrive this way and are bundled into a
  release users run: yt-dlp (yt-dlp/yt-dlp-nightly-builds), ffmpeg and
  ffprobe (eugeneware/ffmpeg-static), qjs (quickjs-ng/quickjs) and mpv
  (Windows). Around 158 MB of code executing with the user's privileges.

  What HTTPS does and does not buy: it proves the bytes came from
  github.com unmodified in transit. It says nothing about whether the
  release asset behind a pinned tag is still the artifact that was
  reviewed. A GitHub release asset can be replaced in place, and an
  account compromise on any of those four upstreams reaches every Snatch
  user through our own signed-by-nobody release. Pinning the TAG, which
  this project does carefully, does not pin the CONTENT.

  SNAT-0016 extended the same gap to runtime, and this session introduced
  that half: the self-update downloads a yt-dlp release asset onto the
  user's machine, chmods it 0700 and executes it. It verifies the file
  RUNS (--version) before promoting it, which catches corruption and a
  truncated download -- it does not catch a substituted binary, because a
  malicious one would answer --version perfectly well.

  Shape of the fix:
  - Record the expected SHA-256 of each asset next to its version pin in
  fetch-binaries.sh, and verify after download, before chmod +x.
  - Same for the runtime path in version.py. A nightly's hash is not
  known ahead of time, so that one needs either GitHub's attestation
  API or a hash fetched from a second source -- decide which, and if
  neither is workable, say so in the code rather than leaving it
  silently unverified.
  - Bumping a pin then means updating a hash, which is the point: it
  makes an upstream content change visible instead of automatic.

  Pairs with SNAT-0036, which is the same question asked about what WE
  publish rather than what we consume.
  **Layman:** Snatch downloads its helper programs from the internet and runs them without checking they are the files we expect.
  Kind: security.
  Source: in-session-2026-08-20.
  Lanes: security, packaging, supply-chain.

- 📋 [SNAT-0037] **Nothing watches for vulnerabilities, and nobody can report one privately.**
  Two gaps in one item, because they are the same gap from opposite
  directions: nothing tells us about a vulnerability, and nobody can tell
  us either.

  No monitoring. There is no .github/dependabot.yml, and CI runs no
  dependency audit. That is how SNAT-0030 happened -- twelve public
  Pillow advisories, all fixed upstream in 12.3.0, shipped in two
  releases, and found only because a person ran pip-audit by hand today.
  Nothing would have surfaced the thirteenth either.

  No reporting path. There is no SECURITY.md at the repo root or in
  .github/. The repo is public and distributes unsigned executables for
  three platforms, so a researcher who finds something has the choice of
  a public issue -- which discloses it to everyone at once -- or saying
  nothing.

  Shape of the fix, all cheap:
  - dependabot.yml covering pip and github-actions. The second also
  keeps SNAT-0035's SHA pins current, which is the standard objection
  to pinning and its standard answer.
  - pip-audit as a step in static-checks so a new advisory fails a build
  rather than waiting for someone to think of it.
  - SECURITY.md naming what is in scope, which versions are supported,
  and how to make contact. GitHub private vulnerability reporting is a
  repo setting and needs no email address published.

  Worth being honest about scope: this is a small project and a
  vulnerability report may never arrive. The monitoring half is what
  earns its keep -- it has already missed something real once.
  **Layman:** We have no early warning when a part we use turns out to be unsafe, and a person who spots a problem has nowhere private to tell us.
  Kind: security.
  Source: in-session-2026-08-20.
  Lanes: security, process.

- 📋 [SNAT-0038] **Full in-app auto-update: offer, show notes since your version, install, relaunch.**
  Asked by the user 2026-08-20, superseding SNAT-0021's notify-only
  scope. Check GitHub for a newer release, show the accumulated changelog
  for EVERY version between the installed one and the latest, and on
  accept download it, close, install, and reopen.

  The user named /mnt/Games/Scripts/Linux/finbreak as the reference, and
  it is a good one: field-proven since v0.1.0, ~1,150 lines across six
  modules with 1,799 lines of feature test. Read it before designing
  anything. Its shape, and why each part is the way it is:

  - Platform seam (services/update_installer.py). detect_installer()
  returns AppImageInstaller on Linux, WindowsInstaller on a frozen
  .exe, else None so the feature goes INERT rather than half-working
  off an unsupported package. Snatch needs the same None branch for a
  source run and for a future distro package (SNAT-0028), where the
  package manager owns updates and an in-app updater must not fire.
  - Linux installs by swapping $APPIMAGE in place, spawning a detached
  fresh copy, and exiting -- a plain in-place re-exec cannot replace a
  busy FUSE mount.
  - Windows cannot replace a running .exe at all; the OS locks it. It
  spawns a detached PowerShell helper that waits for the image to be
  free, moves the verified new .exe over the old, and relaunches.
  - Accumulated notes is FIBR-0152, and it is exactly what the user
  asked for. /releases/latest returns ONE body, so a user three
  versions behind saw only the newest. It fetches /releases?per_page=30
  and concatenates the bodies between installed and offered. Notes
  failing to load does not cancel the offer -- the offer stands with
  poorer notes.
  - The dialog is non-blocking, offers Later / Skip this version /
  Update now, and STAYS OPEN during the download showing progress.

  Signing is not optional here, and this is the part to decide first.
  finbreak verifies every download against an Ed25519 public key
  committed to the repo, with the private half generated off-tree and
  never committed; before keygen ran, the constant held 32 zero bytes so
  verification FAILED CLOSED and a test asserted it. Snatch has no
  signing at all today (SNAT-0036) and its releases carry no checksums
  (SNAT-0031). An auto-updater without that is a channel that downloads
  code from the network and executes it as the user -- strictly worse
  than having no updater. SNAT-0036 is therefore a hard prerequisite,
  not a nice-to-have alongside.

  Two more finbreak lessons worth taking for free, both filed there
  AFTER shipping:
  - FIBR-0167: enforce HTTPS on REDIRECTS, not just the initial URL,
  or the transport can be silently downgraded mid-request.
  - FIBR-0169 is still OPEN there: anti-rollback. A correctly signed
  OLD version is a valid signature, so a downgrade attack to a
  version with a known hole passes verification. Bind the offered
  version into what is signed. Knowing this in advance is worth more
  than the rest of the list.

  Scope Linux and Windows first, matching finbreak. macOS is deliberately
  excluded for now: the build is unsigned (SNAT-0004), has never been run
  by anyone (SNAT-0025), finbreak has no .app implementation to copy, and
  silently replacing an unsigned bundle on a platform nobody has tested
  is the worst possible place to debut this. detect_installer() returning
  None there is the correct interim behaviour.

  Depends on SNAT-0036 (signing/checksums). Supersedes SNAT-0021.
  **Layman:** Snatch offers a new version, shows everything that changed since the one you have, and if you accept it updates and reopens itself.
  Kind: feature.
  Source: user-request-2026-08-20.
  Lanes: application, packaging, security.

- 📋 [SNAT-0039] **Queued downloads ignore your format choice and run strictly one at a time.**
  Two problems in one eight-line method, downloader.py:743.

  The correctness one first, because it is the one users would notice
  and it is not an optimisation at all: _process_next_queue_item sets
  `format_spec = "best"` as a literal before calling _start_download.
  So every queued item ignores preferred_resolution and preferred_ext --
  the two settings the app persists in config.json specifically to
  remember what you want, and which the non-queue path honours through
  _auto_select_preferred. Queue a 1080p-preferring session and you get
  whatever yt-dlp calls best, silently.

  The throughput one: the queue is strictly serial. _download_complete
  advances queue_index and starts the next, one at a time. For a queue of
  ten videos on a connection that is not saturated by one download --
  which is most connections, since YouTube throttles per stream -- two or
  three at once would finish the batch materially faster. This is the
  real throughput lever for this app, and much more promising than
  fragment concurrency (SNAT-0040, measured and inconclusive).

  Things not to get wrong:
  - Concurrency needs a cap and it should be small. Unbounded parallel
  downloads is a good way to get rate-limited by the site.
  - self.download_process is a single handle and _reset_ui / cancel /
  the 150ms progress throttle all assume one active download. That
  assumption is the actual work; the parallelism is the easy part.
  - Fix the format bug FIRST and separately. It is a two-line change
  with a clear right answer, and it should not wait behind a
  refactor.

  Related: SNAT-0023 persists the queue across restarts.
  Progress (2026-08-20): the CORRECTNESS half is fixed and shipped; this
  bullet stays open for the throughput half only.

  _process_next_queue_item no longer hardcodes format_spec = "best". A
  stored format_id is meaningless to a different video, so the saved
  preference is re-expressed as a selector yt-dlp resolves per item:
  bestvideo[height<=H][ext=E]+bestaudio, degrading through looser
  candidates to plain "best" so an unusual preference never leaves a queue
  item with nothing to download. merge is set alongside it, since the
  leading candidates pair a video-only stream with audio. An ext that is
  not alphanumeric is dropped rather than pasted into the selector, and no
  stored preference keeps the old ("best", False) behaviour exactly.

  Still open: the queue is strictly serial. As this bullet's body already
  says, the work there is that self.download_process is a single handle
  which _reset_ui, cancel and the 150ms progress throttle all assume --
  the parallelism itself is the easy part.
  **Layman:** Anything you add to the queue is downloaded at whatever quality yt-dlp picks, not the one you chose — and they run one after another rather than together.
  Kind: fix.
  Source: in-session-2026-08-20.
  Lanes: downloader, performance.

- 📋 [SNAT-0040] **Expose yt-dlp fragment concurrency as a setting -- measured, and the default is not obvious.**
  _get_base_cmd passes no -N / --concurrent-fragments, so yt-dlp uses
  its default of 1 and fetches DASH fragments one after another.

  Measured 2026-08-20 rather than assumed, and the measurement is why
  this bullet is not "just turn it on". Three pairs, Big Buck Bunny at
  720p (68 MB) through the repo's pinned yt-dlp:

    -N 1 : 5.27s, 4.83s, 4.25s   (mean ~4.78)
    -N 8 : 3.82s, 3.76s, 4.53s   (mean ~4.04)

  So roughly 1.2x on average, and the third pair REVERSED -- N=8 was
  slower than N=1. On this connection the result is inside the noise, and
  the widely repeated "3-5x faster" is not what this machine shows.

  That does not make it worthless. Fragment concurrency helps most where
  per-connection throughput is the limit -- a high-latency link, or a
  site throttling a single stream -- and this machine on a fast
  connection is close to the worst case for demonstrating it. It means
  the honest move is a setting with a conservative default, not a silent
  change to how everyone's downloads run.

  Suggested: a small dropdown next to the existing speed-limit control,
  default 1 (current behaviour, no change for anyone), and a note in the
  README about when raising it helps. If someone on a slow connection
  measures a real gain, revisit the default then -- with their numbers.

  Do NOT combine with --limit-rate without checking: the two interact,
  and the app already exposes a rate limit.

  For batch throughput see SNAT-0039 --
  running queued downloads in parallel is the bigger and better-evidenced
  win.
  **Layman:** There is a yt-dlp option that can fetch a video in several pieces at once. On a fast connection it made little difference here, so it should be a setting rather than something we force on.
  Kind: perf.
  Source: in-session-2026-08-20.
  Lanes: downloader, performance.

- ✅ [SNAT-0041] **Right-click Cut/Copy/Paste is available on every text field.**
  Requested by the user 2026-08-20: pasting a URL required either the
  Paste button next to the URL bar or Ctrl+V, and right-click did nothing
  anywhere in the app.

  widgets.attach_context_menu(widget, editable=True) builds a tk.Menu as a
  CHILD of the widget it serves. That is the whole cleanup story: a theme
  switch destroys main_frame and calls create_widgets again, so the menu
  dies with its widget and is rebuilt in the new theme's colours. No trace
  callbacks, nothing to release on close.

  Right-click is Button-3 except on macOS, where Tk reports it as
  Button-2. The binding is chosen per platform rather than bound to both,
  because Button-2 on X11 is middle-click paste of the primary selection
  and covering it would take a working paste away from Linux users.

  Attached to: the URL, cookies-file and save-path entries (download tab),
  the search and channel entries (search tab), and the media-file entry
  (media info tab). The media-info report is state=DISABLED, so it gets
  Copy and Select All with editable=False.

  Unexercised: the macOS Button-2 binding, since nobody has ever run the
  macOS build (SNAT-0025).
  **Layman:** You can now right-click any box in Snatch to paste a link, copy text or select everything.
  Kind: feature.
  Source: user-request-2026-08-20.
  Lanes: ui.

- ✅ [SNAT-0042] **A cookied fetch that returns audio only killed the whole format list.**
  Reported twice on 2026-08-20 for the same video (oi2QgPH61JM): on Linux
  Fetch Formats raised "ERROR: [youtube] oi2QgPH61JM: Requested format is
  not available", and on Windows the format list held audio streams only.

  One cause, reproduced at the command line. With
  --cookies-from-browser firefox YouTube answers that video with 4
  formats, every one of them audio. With no cookies it answers with 53, of
  which 37 carry video.

  Two defects follow.

  -J is not a pure metadata dump -- yt-dlp still runs its default format
  selection, and an audio-only answer cannot satisfy it. So the whole dump
  aborts and the user sees NO formats, not even the audio ones that do
  exist. _probe_formats passes --ignore-no-formats-error, which turns the
  Linux error dialog into a list.

  And cookies that yield no video are worth nothing for that fetch. A
  single video whose cookied probe carries no video format is probed once
  more with no cookie arguments; whichever answer has video is the one
  kept, and the status line says the cookies were skipped. A playlist
  payload is excluded. A retry that times out or returns junk leaves the
  cookied answer standing, so the fallback can never make things worse.

  Not addressed here: WHY cookies cause YouTube to withhold video
  formats. The retry routes around it rather than fixing it, and if that
  behaviour ever spreads to the un-cookied path there is nothing left to
  fall back to.
  **Layman:** When Snatch's saved cookies made YouTube hand back sound-only versions of a video, Snatch either showed an error or listed no picture qualities at all; it now retries without the cookies.
  Kind: fix.
  Source: user-report-2026-08-20.
  Lanes: downloader.

- ✅ [SNAT-0043] **Every build has been running with NO JavaScript runtime: --js-runtimes is not comma-separated.**
  Root cause of the SNAT-0042 reports, found by reading yt-dlp's own
  --help after the user asked whether a permanent fix existed.

  `--js-runtimes` takes ONE `RUNTIME[:PATH]` and is repeatable -- "This
  option can be used multiple times to enable multiple runtimes". It is
  not a comma-separated list. _get_base_cmd joined the list with commas,
  so yt-dlp parsed `quickjs:/path/to/qjs,node` as the single runtime
  quickjs at the nonexistent path "/path/to/qjs,node", found it
  unavailable, and reported `JS runtimes: none`.

  Measured on this machine with the app's own binary and command builder,
  same video, cookies on:
    --js-runtimes "quickjs:<path>,node"   ->  4 formats,  0 video
    --js-runtimes quickjs:<path>          -> 37 formats, 25 video
    --js-runtimes node                    -> 37 formats, 25 video
    one flag each (the fix)               -> 37 formats, 25 video,
                                             "JS runtimes: node-24.18.1,
                                             quickjs-ng-0.16.1"

  The blast radius is every build, not this machine. The comma path is
  taken whenever find_jsruntime() finds a bundled runtime, which is
  exactly what a packaged Windows, Linux or macOS build always has. So
  every released artifact has been solving no JS challenge at all, and the
  Windows "audio streams only" report is the same defect seen from the
  other side. quickjs alone was verified to solve the challenge, so the
  bundled runtime was always capable -- it was simply never enabled.

  Two secondary corrections came with it. The docstring claimed the
  bundled runtime "is listed first so it wins"; order carries no meaning,
  since yt-dlp picks by its own priority (deno > node > quickjs > bun)
  among whatever is enabled and available. And _has_any_runtime was
  therefore answering about a list that yt-dlp never accepted.

  SNAT-0042's retry-without-cookies stays as a net rather than being
  reverted: it costs one extra probe only when a cookied fetch really does
  come back without video, and it is the only thing standing if YouTube
  withholds formats for some reason other than this one.

  Not verified here: the Windows and macOS builds, where the bundled
  quickjs is the only runtime. Proven locally that quickjs alone solves
  the challenge, which is the same code path those builds take.
  **Layman:** Snatch was telling yt-dlp about its bundled helper program in a way yt-dlp could not read, so the helper was never used and YouTube quietly withheld all the picture qualities.
  Kind: fix.
  Source: in-session-2026-08-20.
  Lanes: downloader, packaging.
