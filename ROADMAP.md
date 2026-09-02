<!-- ants-roadmap-format: 1 -->
# Snatch — Roadmap

A tkinter frontend for yt-dlp. This roadmap tracks packaging, distribution
and application work. IDs are allocated from `.roadmap-counter`.

## Packaging and distribution

- ✅ [SNAT-0001] **Windows one-file build via GitHub Actions.**
  PyInstaller `--onefile` on a `windows-latest` runner, bundling
  `yt-dlp.exe` and `ffmpeg.exe` downloaded at build time. Spec in
  `pyinstaller.spec`; built by `scripts/build-windows.sh`, called from
  `.github/workflows/ci.yml`. The plan is
  `docs/plans/SNAT-0001-windows-onefile-build.md`.
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

- ✅ [SNAT-0008] **Upgrade act past CVE-2026-34041 and CVE-2026-34042.**
  scripts/local-ci.sh drives `act`, and act 0.2.84 on this machine prints
  its own warning: vulnerable to CVE-2026-34041 and CVE-2026-34042,
  fixed in 0.2.86. Latest at time of writing is 0.2.89. The gate works,
  but it is running a tool that is telling us to upgrade it.
  Resolved (2026-09-02): upgraded to act 0.2.89, and the gate now refuses
  to run below the fixed version.

  The distro is the reason this needed more than an upgrade. openSUSE
  ships act 0.2.84 and reports it up-to-date, so `zypper up` does not fix
  it and never will on this release. The upstream binary is installed to
  ~/.local/bin/act, which precedes /usr/bin on PATH; the rpm copy is
  untouched, so zypper stays consistent and reverting is deleting one
  file. The download was checked against the published checksums.txt
  before installing -- installing an unverified binary while SNAT-0031 is
  open about exactly that would be poor form.

  A hand-fix on one machine is not a fix. scripts/local-ci.sh now reads
  act's version and exits non-zero below 0.2.86, rather than warning: the
  gate runs untrusted workflow code in a container on this machine, and a
  warning printed partway up a passing run is one nobody reads. The
  comment above the check carries the upgrade recipe, because the obvious
  remedy does not work here.

  Verified by running the comparison, including the cases that would
  refute it: 0.2.84 and 0.2.85 blocked, 0.2.86, 0.2.89, 0.2.100, 0.3.0 and
  1.0.0 allowed. 0.2.100 is the one that matters -- a lexical compare
  rejects it, sort -V does not. An unreadable version warns that the check
  did not run instead of passing silently.

  Full local-ci.sh passes under 0.2.89, including the AppImage build, so
  the upgrade does not break the pipeline it gates.
  **Layman:** The tool that runs our checks locally has a known security hole and should be updated.
  Kind: security.
  Source: in-session-2026-08-19.
  Lanes: ci, security.

- ✅ [SNAT-0009] **Pin the appimagetool runtime rather than tracking continuous.**
  scripts/build-linux.sh downloads the AppImage type2 runtime from the
  `continuous` tag, which moves. Everything else in the build is pinned
  (yt-dlp 2026.03.17, ffmpeg-static b6.1.1, pyinstaller 6.11.1). A moving
  runtime can break a build with no change on our side.
  Resolved (2026-09-02): already done, and this status was stale rather
  than the work being open.

  scripts/build-linux.sh pins APPIMAGETOOL_VERSION and
  TYPE2_RUNTIME_VERSION to explicit versions and verifies each download
  against a recorded SHA-256, per architecture. The bullet's body still
  described the runtime as coming from the moving `continuous` tag, which
  has not been true for some time.

  Worth noting for anyone reading the pin later: the runtime tag is an
  OLDER dated release than the `continuous` build it replaced. That is
  deliberate -- it is the only immutable tag available -- and it is not a
  version to bump. Moving it means moving the pin and its digest together.

  Found while surveying open items, not by a ledger sweep; other bullets
  in this roadmap may carry the same kind of staleness.
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
  Progress (2026-08-31): issues 2 and 3 are done; issue 1 is not.

  Issue 2 (excessive-permissions) closed: ci.yml now sets
  `permissions: contents: read` at workflow scope, with a job-level
  `contents: write` on `release` alone.

  Issue 3 (artipacked) closed: all five actions/checkout steps now pass
  `persist-credentials: false`.

  Issue 1 (unpinned-uses) partially closed: 1 of 14. Only
  softprops/action-gh-release was pinned — the third-party action, in the
  one job that holds contents: write. It is pinned to
  3bb12739c298aeb8a4eeaf626c5b8d85266b0e65, the commit `v2` pointed at on
  2026-08-31 (v2.6.2). That is a pin, not a bump: `v2` remains the version
  in use, and v3.0.3 is current, which is a separate question for
  check-dependencies.

  Still open: the 13 first-party actions/* pins (checkout, setup-python,
  upload-artifact, download-artifact). Left for a deliberate pass because
  pinning them commits the project to a SHA-update routine, and the bullet
  already proposes `pinact run` plus adding zizmor to static-checks — both
  of which should land together rather than piecemeal.

  zizmor now reports 17 findings, down from 24.
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
  Correction (2026-09-01): this bullet's evidence line is now false and
  its subject is not.

  The body says "no checksum file anywhere in the repo -- grepping for
  sha256/shasum/checksum/gpg across scripts/ and the workflow returns
  [nothing]". Re-derived today rather than re-read: that grep now returns
  16 matches. build-linux.sh records and verifies SHA-256 digests for the
  AppImage runtime and appimagetool (SNAT-0031), and snatch/version.py
  verifies the self-update against the SHA2-256SUMS file the yt-dlp
  release publishes.

  None of that changes what this bullet asks for. Those are checksums this
  project CONSUMES; SNAT-0036 is about checksums this project PUBLISHES,
  so that someone downloading a Snatch release can verify it. The release
  job still emits no SHA256SUMS, no signature and no attestation. The
  bullet stands; only its "nothing anywhere" framing has expired.

  Worth noting for whoever picks it up: the yt-dlp nightly releases carry
  both SHA2-256SUMS and SHA2-256SUMS.sig, which is a working example of
  the shape this bullet proposes, published by a project of comparable
  size.
  **Layman:** Someone downloading Snatch has no way to check the file they got is the one we published.
  Kind: security.
  Source: in-session-2026-08-20.
  Lanes: security, release, supply-chain.

- ✅ [SNAT-0064] **Windows builds failed intermittently on a GitHub API rate limit.**
  Recorded because the cause is invisible from the code and the failure
  hid behind green runs.

  scripts/fetch-binaries.sh resolved the mpv asset name through
  api.github.com at fetch time, because that name carries a build hash.
  That endpoint is rate-limited per IP for unauthenticated callers. On
  2026-09-02 at 06:32 UTC a Windows CI run failed with

    curl: (22) The requested URL returned error: 403
    json.decoder.JSONDecodeError: Expecting value: line 1 column 1

  -- the throttled response, handed to a JSON parser as an empty body.
  Windows-only, since that block runs nowhere else, and intermittent, so
  every later run passed and it read as a blip rather than a defect.

  The lookup was never needed: a pinned tag has a fixed asset. Once
  SNAT-0031 gave that asset a recorded digest, the name could be pinned
  beside the tag, removing a network call, a JSON parse and the whole
  failure class. A stale name now stops the build rather than fetching
  something unverified.

  Verified on the only platform that can verify it: pushed and the real
  build-windows job went green, with the archive downloaded directly and
  its digest checked before 7z unpacked it. A local gate could not test
  this -- act runs Linux containers and the mpv block only executes on
  Windows.

  TRAP for anyone bumping the pin: MPV_WIN_TAG, MPV_WIN_ASSET and the
  digest in digest_for() now move together. docs/building.md says so in
  the pin table.
  **Layman:** Windows builds sometimes failed for no reason anyone could see; they no longer make the call that was failing.
  Kind: fix.
  Source: ci-failure-2026-09-02.
  Lanes: ci, packaging.

## Application

- ✅ [SNAT-0006] **Write user data files with 0600 permissions.**
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
  Progress (2026-09-01): the WRITE side is done. The on-disk tightening
  pass this bullet asks for is NOT, and it is the half that matters.

  utils.atomic_private_write now writes to a temp file with an explicit
  mode and os.replace's it into place, so a save installs a fresh 0600
  inode whatever the target's mode was. All three call sites use it:
  app.py (config.json), tabs/history.py (history.json), cookies.py
  (cookies.txt). Verified: a 0664 file rewritten through it comes out
  0600, where the old os.open form left it 0664.

  That closes "no amount of re-saving will ever narrow them". It does not
  close this bullet. A file that is never saved again keeps its old mode,
  and this bullet already named the better fix for exactly that reason --
  "a one-time tightening pass over app_data_dir() at startup", which also
  catches a file copied in from an old install.

  Measured on this machine immediately after the fix landed:
  config.json 600, history.json 600, cookies.txt 664. The first two had
  tightened only because the session's testing happened to re-save them.
  cookies.txt -- the one this bullet calls out as carrying session
  tokens -- had not been rewritten and was still group-readable. It was
  chmod'ed to 600 by hand on 2026-09-01, which fixes this machine and
  nothing else.

  So what remains is the startup pass over app_data_dir(), narrowing
  config.json, history.json and cookies.txt if present. Small, and it is
  the difference between the rule holding for a user who happens to
  trigger a save and holding for everyone.

  Process note worth keeping. Three lanes of the 2026-08-31 review-code
  sweep found the O_CREAT mechanism independently and reported it as new.
  It was not new: this bullet diagnosed it in full on 2026-08-20,
  mechanism and remedy included. The lane briefs carried CLAUDE.md and
  STANDARDS.md but not the ROADMAP, so the sweep paid three times for an
  analysis the project already owned -- and, worse, the resulting fix was
  scoped to what the lanes saw (the write sites) rather than to what this
  bullet already knew was insufficient. Brief the roadmap, or at least
  query it per lane, before the next sweep.
  Resolved (2026-09-02): the on-disk tightening pass this bullet asked
  for is in, so both halves are now done.

  utils.tighten_user_data_permissions(directory) chmods config.json,
  history.json and cookies.txt to 0o600 where they are not already, and
  SnatchApp.__init__ calls it right after app_data_dir(). That covers the
  file a user never saves again and the file copied in from an older
  install, which is how the loose ones arrived.

  Three deliberate limits, each with a reason rather than an oversight.
  Windows is skipped: POSIX mode bits are not the access mechanism there
  and S_IMODE never reads back 0o600, so an unconditional pass would chmod
  every startup and never converge. A symlink is skipped rather than
  followed, because chmod follows a link and would re-mode a file outside
  the data directory. Nothing raises: a permission pass that stops the app
  launching is worse than the mode it was fixing.

  Verified by running, not reading. scripts/verify_permissions.py builds
  the loose state in a scratch directory -- the project's own files are
  already 0600, so asserting against them would pass without the code
  under test -- and checks the fix, idempotency, a missing file, the
  symlink case and that atomic_private_write still installs 0600 over a
  loose target. Proved red first: stubbing the pass to return [] fails it
  on the first assert. And the real app, launched under Xvfb with
  app_data_dir pointed at a directory of 0664 files, built all four tabs
  and left all three at 0600.

  The test is wired into scripts/local-ci.sh beside the platform_utils
  smoke test, so it is part of the pre-push gate rather than a script
  nobody runs. This is the second entry in what SNAT-0020 calls an absent
  test suite; it does not close that item.
  Follow-up (2026-09-02): the test now runs in CI as well, which the
  note above claimed less than it should have.

  It was wired into scripts/local-ci.sh only, so it ran on one machine at
  push time and never on GitHub. CI's static-checks job runs compileall
  and shellcheck; verify_platform_utils.py reaches CI solely through the
  three build scripts, and this test is not part of a build. A regression
  test only one machine runs is the same shape as the bug this item was
  about -- code that looks right and never takes effect.

  Added as a static-checks step in .github/workflows/ci.yml, verified
  through act rather than by reading the YAML: the step ran inside the
  real job and passed.
  Windows verification (2026-09-02): the skip is now confirmed by running
  it, which the original note could not claim.

  The Windows branch of tighten_user_data_permissions was argued from
  S_IMODE behaviour and never executed on Windows -- CI proved the build
  compiled and packaged, not that the app starts or that the pass is
  harmless there.

  Tested on the real machine (ssh wintest, Windows 10) using the
  snatch.exe artifact from the CI run for 993058b, which contains this
  change. All three user-data files were pre-created next to the .exe so
  the pass would walk existing files rather than find nothing. The app
  launched, ran 45 seconds with empty stderr, and all three files came
  back byte-for-byte unchanged in length and content. So the import of
  is_windows into utils resolves in the frozen build, the pass takes its
  early return, and it modifies nothing.

  A first run also created bin/ alongside the executable, which
  independently confirms the Windows row of STANDARDS 14: app_data_dir()
  is the directory holding the .exe.

  What this does NOT cover: an SSH session has no interactive desktop, so
  this is not evidence the GUI draws correctly -- only that startup
  completes and the permission pass is inert. SNAT-0007 owns the render
  check.

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

- ✅ [SNAT-0020] **The app has no automated tests at all.**
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
  Correction (2026-09-01): this bullet's own correction was itself wrong.
  The 2026-08-20 note says scripts/verify_platform_utils.py "carries two
  real asserts ... so a failure does fail the build. That is a genuine
  gate, and it runs on Windows and macOS where nothing else does." It did
  not gate anything on any platform.

  One assert sat behind `if pu.is_frozen():`, and sys.frozen is set only
  inside a PyInstaller bundle. All four call sites -- build-linux.sh:20,
  build-windows.sh:20, build-macos.sh:22, local-ci.sh:68 -- run it as a
  plain script, every one of them BEFORE PyInstaller, which is also the
  reverse of the file's own docstring. The other assert,
  `os.path.isdir(pu.app_data_dir())`, resolves in dev mode to the repo
  root the script was just loaded from, so it could not fail. Confirmed
  by running the pre-fix file with bin/yt-dlp hidden: exit 0.

  Fixed today. The asserts run unconditionally and cover find_ytdlp,
  find_ffmpeg, resource_path, user_bin_dir and app_data_dir, plus a
  separate _find_bundled_binary check for yt-dlp and ffmpeg. That second
  check exists because the obvious one was weaker than it looked: hiding
  bin/yt-dlp left `find_ytdlp() != "yt-dlp"` green, because it fell
  through to /usr/local/bin/yt-dlp on PATH. On a bare CI runner it would
  have worked by accident. Proved red three ways and green when restored.

  What the bullet asks for is unchanged and still open: this is a
  build-time smoke check on one module, not a test suite for 3,865 lines,
  and it would still not have caught either version.py bug. Two things
  from the 2026-08-31 review sweep sharpen the starting point. CI's only
  Python check is `python -m compileall`, which proves each file parses
  and never imports the package -- which is exactly how SNAT-0041 shipped
  a guaranteed NameError at startup that survived two sessions. A single
  line, `python -c "import snatch, snatch.app, snatch.tabs.search"`,
  would have caught it. See SNAT-0044.
  Resolved (2026-09-02): a first suite exists and CI runs it. 35 tests over
  the three areas this bullet named, in its own value order.

  Pure logic: _version_compare (numeric not lexicographic, missing
  components, leading zeros), _is_valid_url (the rejections matter more
  than the acceptances -- ftp, file, javascript, data, a bare hostname,
  and a scheme that merely contains "http"), _safe_resolve_path.

  Binary resolution: user_bin_dir from source lands in bin/updated rather
  than the bin/ that holds the pinned copy, the Windows LOCALAPPDATA
  fallback fires on unwritability and NOT merely on being Windows, and
  find_ytdlp prefers an updated copy over the bundled one.

  The promotion rule: _probe_version rejects a non-executable file, an
  HTML error page saved under a binary's name, a non-zero exit, and an
  empty version string; _expected_digest parses the published manifest and
  raises on an absent or malformed entry.

  Two findings matter more than the tests.

  The suite found a real defect on its first run, which is what this
  bullet predicted. _safe_resolve_path checked for a null byte AFTER
  os.path.realpath, and realpath raises ValueError on one -- so the guard
  was unreachable and the function raised where both callers test
  `if resolved` and expect None. Fixed by checking the input.

  And mutation testing found a defect in one of these tests. Seven
  mutations were run against the targets; one survived. Removing
  _probe_version's returncode check left the suite green, because that
  test's script exited non-zero while printing nothing, so the
  empty-stdout branch rejected it and the returncode check was never
  exercised. It passed for the wrong reason. Fixed, and the mutation is
  now caught. Without that pass this would have been reported as 35
  passing tests with one asserting nothing.

  Deliberately NOT covered, and this bullet's own scope says so: driving
  the tkinter GUI. Also uncovered, and worth naming rather than implying
  otherwise -- the config loader's corrupt shapes (SNAT-0051) and the
  parser assumptions (SNAT-0050), both open items whose fixes are pending,
  so tests now would encode behaviour that is about to change.

  CI installs python3-tk for the step, because version.py, downloader.py
  and tabs/history.py import tkinter at module level and
  actions/setup-python does not bundle _tkinter. pytest pinned 9.1.1 --
  the version these were run against.

  The two scripts/verify_*.py checks stay: they run at build time on all
  three platforms, which this job does not.
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

- 📋 [SNAT-0022] **Nothing in the app tells you where its diagnostic log is.**
  Narrowed 2026-09-02. Two of this item's three parts shipped as
  SNAT-0045: a size-capped rotating snatch.log in app_data_dir() at
  0o600, and a walk of the broad handlers that were discarding the
  reason a failure happened.

  What remains is the third: a route to that file from the GUI, so a bug
  report can carry it. Today nothing in the app names the path, so a user
  has to be told where app_data_dir() resolves to before they can find
  it.

  Any affordance has to handle the file not existing. Logging is off
  unless SNATCH_LOG is set, and even when set the file stays empty until
  something fails -- so "open the log" must not present an empty or
  absent file as a fault.
  **Layman:** Snatch keeps a troubleshooting log, but there is no button to open it, so you have to be told where the file lives.
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

- ✅ [SNAT-0031] **Five bundled binaries are downloaded and executed with no integrity check.**
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
  Progress (2026-09-01): the build TOOLING half is done; the five bundled
  binaries this bullet enumerates are untouched and still unverified.

  The 2026-08-31 review sweep found two unverified downloads this bullet
  does not cover, because they are not bundled binaries: the AppImage
  type2 runtime, which becomes the first bytes of the artifact every user
  executes, and appimagetool, which runs on the build host. Both came from
  a rolling `continuous` tag with no pin and no hash, and the runtime's
  cache test was `[ ! -s "$runtime" ]` -- non-emptiness -- so once a file
  landed it was trusted forever. appimagetool was worse: `command -v`
  silently preferred any system copy of unknown version.

  Both are now pinned to immutable tags (type2-runtime 20251108,
  appimagetool 1.9.1) with a per-arch SHA-256 recorded in build-linux.sh,
  verified before use, and an unrecorded architecture exits rather than
  skipping the check. Verified: a corrupted cached runtime is rejected
  where the old test accepted it, a digest mismatch exits 1 leaving no
  .part, and a full build with the pinned tools produces a working 98 MB
  AppImage.

  Still open, and unchanged: yt-dlp, ffmpeg, ffprobe, qjs and mpv are
  fetched by scripts/fetch-binaries.sh with no hash check at all. What
  landed there today is a version-keyed cache (a pin bump used to be
  silently ignored) and --proto '=https' on every curl, not integrity.
  The fetch_verified/cached_ok pair in build-linux.sh is the shape to
  reuse.
  Resolved (2026-09-02): both halves are done, and the runtime half was
  already done before today.

  Build half, landed now. digest_for() in fetch-binaries.sh records the
  expected SHA-256 of all 19 assets across every platform the script
  supports, and fetch() verifies before chmod +x, so an unverified file
  never becomes executable. The mpv archive is verified before 7z unpacks
  it -- unpacking an unverified archive is already executing
  attacker-chosen paths, and that asset's name carries a build hash
  resolved from the API at fetch time, so the digest is the only thing
  pinning it. The cache is keyed on content now rather than on a stamp
  file agreeing about a URL, and an unrecorded asset stops the build
  rather than being fetched unverified, which is the shape build-linux.sh
  already used.

  Runtime half: already shipped 2026-09-01, after this bullet was written.
  version.py fetches each nightly's SHA2-256SUMS manifest, streams the
  download while hashing, and refuses a mismatch. The bullet asked that if
  neither approach were workable the code should say so; what it does
  instead is state the real ceiling in _expected_digest's docstring --
  this defends against alteration in transit and substitution, not against
  a compromised release. Nothing further is owed there.

  Digests came from the GitHub API's own `digest` field rather than from
  downloading ~400 MB. That field was checked before being trusted:
  qjs-linux-x86_64 downloaded and hashed by hand matched exactly. It is
  also independently corroborated -- the four binaries already sitting in
  bin/, fetched weeks ago through the unverified path, match the recorded
  values.

  Proved in four directions, not assumed: a normal fetch verifies; a byte
  appended to bin/qjs is detected and re-fetched where the old
  stamp-keyed cache would have printed "cached"; a faked expected digest
  exits 1 leaving no binary and no .part; an unrecorded asset stops with a
  message naming digest_for().

  Bumping a pin now means updating its digest. That is the point -- it
  makes an upstream content change visible instead of automatic.
  docs/building.md carries the refresh command.

  Leaves SNAT-0036 untouched, which is the same question asked about what
  we publish rather than what we consume.
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
  Correction (2026-08-31): this shipped ✅ on 2026-08-20 and the app has
  not launched since. attach_context_menu was imported in
  snatch/tabs/download.py and called, without an import, in
  snatch/tabs/search.py and snatch/tabs/media_info.py. All four tabs are
  built eagerly at app.py:206-221, so create_widgets raised NameError at
  search.py:34 and the window never appeared. Found by check-code (ruff
  F821, pyright reportUndefinedVariable, both independently), then
  reproduced by constructing SnatchApp under Xvfb.

  Fixed today by adding the missing import to both modules. Verified by
  running: all four tabs build and Button-3 bindings are live on the
  search entry, the channel entry and the media-info report. The bullet's
  own list of six attached fields is accurate now; it was not when it was
  written.

  Status left ✅ rather than flipped back, because the claim is true as of
  this fix. What the episode actually evidences is SNAT-0020: nothing in
  CI imports the package, so a guaranteed startup crash shipped and
  survived two sessions.
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

  The blast radius is every build on a machine that ALSO has a JS runtime on PATH -- not every build, and the distinction was missed when this was first written. The comma path is taken whenever find_jsruntime() finds a bundled runtime, which is what a packaged build always has -- but joining a ONE-element list is a no-op, so the flag only breaks once a second runtime is enumerated beside the bundled one. Where the bundled quickjs is the only runtime present, the old code emitted exactly the flag the fix emits, and those builds were never broken. Measured on Windows 2026-08-20; see the verification note below. The Windows "audio streams only" report is therefore NOT explained by this defect unless that machine had deno, node, quickjs or bun on PATH. quickjs alone was verified to solve the challenge, so the
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

  Windows verified 2026-08-20 -- see the note below. macOS is still unverified for want of Mac hardware (SNAT-0025); it takes the same single-bundled-runtime branch Windows does, which is the branch the join never altered.
  Windows verification (2026-08-20). Artifact: snatch-windows from CI
  run 32378831477, commit 85b7bd9; `git diff 85b7bd9 HEAD -- snatch/
  scripts/` is empty, so the .exe is HEAD's code. Box: wintest
  192.168.0.102, Windows 10 19045, no deno/node/quickjs/bun on PATH.
  Bundled binaries lifted out of the running _MEIPASS: bin/qjs.exe
  2148722 bytes, bin/yt-dlp.exe 17798916. `qjs -e` self-test passes.

  Ran the bundled yt-dlp with the app's own flags (--ignore-config
  --remote-components ejs:github --ffmpeg-location <bundled>) against
  https://www.youtube.com/watch?v=oi2QgPH61JM, anonymous, no cookies:

    --js-runtimes quickjs:C:\...\bin\qjs.exe (the fix)
          -> "JS runtimes: quickjs-ng-0.16.1"   53 formats, 37 video
    --js-runtimes "quickjs:C:\...\qjs.exe,node" (the old comma form)
          -> "JS runtimes: none" + the deprecation warning
                                                53 formats, 37 video
    no --js-runtimes at all (control)
          -> "JS runtimes: none" + the same warning
                                                53 formats, 37 video

  Two things this settles and one it does not. It settles the risk the
  Windows branch was flagged for: a RUNTIME:PATH value whose path carries
  a drive colon parses correctly -- yt-dlp splits on the first colon, so
  `quickjs:C:\...` enables the runtime rather than reporting none. And it
  reproduces the comma defect on Windows, so the mechanism is not
  Linux-specific.

  What it does NOT show is a format difference. All three forms returned
  the same 53/37 for this video anonymously, so this box could not
  reproduce the audio-only symptom in either direction and the format
  half of the fix is unproven on Windows. The likely reason is
  --remote-components ejs:github, which lets yt-dlp fetch a solver
  instead of needing a local runtime; the original 4-format measurement
  was taken with cookies on, and no YouTube cookies were available here.

  Consequence for the record: on a Windows box with no other runtime the
  old and new code emit the byte-identical command, so this fix is a
  no-op there. The audio-only report from Windows is therefore still
  unexplained unless that machine had a second runtime on PATH -- worth
  asking the reporter.
  Follow-up (2026-08-20): the reporting machine has NO second runtime, so
  this item cannot be the cause of the Windows report.

  Asked whether wintest had node/deno/bun installed, since that is the
  only configuration in which the comma defect fires. It does not, on
  three independent checks: the registry PATH (HKLM Session Manager
  Environment + HKCU Environment) holds only OpenSSH, system32, Wbem,
  PowerShell v1.0 and dotnet, with the user half a single WindowsApps
  entry; none of node.exe / deno.exe / bun.exe / qjs.exe / quickjs.exe
  exists in any common install location (Program Files\nodejs, APPDATA\
  npm, nvm, .deno\bin, .bun\bin, chocolatey, scoop shims, WinGet Links);
  and no uninstall-registry entry matches node|deno|bun|quickjs. The SSH
  session's PATH equals the registry PATH, so the earlier `where` check
  was not a false negative from a thinner environment.

  wintest IS the reporting machine. Its install sits at
  C:\Users\aants\OneDrive\Desktop\Snatch\ -- snatch.exe dated 2026-08-19
  22:40, and history.json holding two downloads consistent with the symptom: 15:55 format "48x27 mhtml" -- a storyboard track, which nobody picks deliberately -- and 15:58 "audio only mp4", both for https://www.youtube.com/watch?v=OGaukFyC0Qw. Read that as strong circumstantial evidence, not as a record of the reported fetch: history.json logs completed DOWNLOADS only, never fetches, so a fetch that showed audio-only and was abandoned leaves no trace at all. For the same reason it does not contradict SNAT-0042's "same video (oi2QgPH61JM)" framing -- a fetch of that video on this box would be invisible here.

  That build and the fixed build are the same tool for this purpose.
  Extracted both _MEIPASS bin/ directories: identical yt-dlp
  (2026.08.18.122307 either side) and identical qjs.exe (SHA256 prefix
  55A1B69CD4FDB6B0 either side). With one runtime in the list the old
  join was a no-op, so the two builds also emit the same command. The
  only behavioural difference between them is SNAT-0042.

  The symptom does not reproduce. Same machine, same binaries, the app's
  own flags, against the reported URL:
    --js-runtimes quickjs:<bundled>  -> 182 formats, 38 video, 101 audio,
                                        4 storyboard
    no --js-runtimes at all          -> 181 formats, 37 video
  and the debug line reads "JS Challenge Providers: bun (unavailable),
  deno (unavailable), node (unavailable), quickjs".

  What this does NOT establish is what the user's session actually sent.
  No config.json exists beside their exe, and browser_var defaults to
  "none" -- but _save_config runs only on a clean window close or a theme
  change, and history.json was written twice while config.json never was,
  so that app was never closed cleanly. Its absence is therefore evidence
  of a kill, not evidence that no browser was selected. A cookie source
  picked in the dropdown that session would have left no trace. So
  SNAT-0042's account -- cookies causing YouTube to withhold video
  formats -- remains fully available for the Windows half and is the
  leading explanation; it is simply not yet demonstrated ON Windows, and
  it is a different video from the one that demonstrated it on Linux.

  Next step if it is worth closing: probe the reported URL on that box
  with --cookies-from-browser against whichever browser is installed, and
  compare the video-format count to the 38 above. Not run here because it
  reads the user's live browser cookie store.
  Method note (2026-08-20), reusable for any Windows-build verification.
  scripts/local-ci.sh cannot run the Windows job and CI only BUILDS the
  .exe, so nothing yet proved runtime behaviour on Windows. This is how
  it was done, in case it is wanted again.

  1. Get the artefact CI already built rather than building one:
     `gh run download <run-id> -n snatch-windows -D <dir>`. Prove it is
     the code under test with `git diff <run-sha> HEAD -- snatch/
     scripts/` -- empty means the .exe is HEAD.
  2. `scp` it to wintest (192.168.0.102, cmd.exe default shell). 145 MB
     moves in about 3 seconds over the LAN. Send PowerShell as a .ps1
     and run it with `powershell -NoProfile -ExecutionPolicy Bypass
     -File`; quoting a PS one-liner through cmd.exe is not worth it.
  3. To reach the bundled yt-dlp / qjs / ffmpeg WITHOUT driving the GUI:
     Start-Process the .exe, sleep ~12 s, copy `%TEMP%\_MEI*\bin\*` out,
     then Stop-Process. PyInstaller deletes the _MEI directory on exit,
     so the copy has to happen while it runs. The GUI does start over
     SSH -- tkinter builds its window in the non-interactive station
     without complaint -- which is what makes this work at all.
  4. Then drive the bundled yt-dlp directly with the app's own flags.
     `-v` prints `[debug] JS runtimes:` and `[debug] [youtube] [jsc] JS
     Challenge Providers:`, which is the fastest read on whether a
     runtime is live.

  Two traps. `rmdir /s /q` on the test directory FAILS silently while the
  app still holds snatch.exe -- kill the process, wait, then delete, and
  check afterwards rather than trusting the echo. And a frozen Windows
  build puts app_data_dir() next to the .exe, so config.json,
  history.json and cookies.txt sit in the same folder the user keeps the
  executable in; that is where to look for evidence of a real run.

  One finding worth carrying: `--remote-components ejs:github`, which
  _get_base_cmd always passes, lets yt-dlp fetch a challenge solver
  instead of needing a local runtime. The control run with NO
  --js-runtimes at all still returned 181 formats / 37 video. So "no JS
  runtime" does not reliably mean "no video formats", and a diagnosis
  that reasons from the runtime alone can reach the wrong answer. Treat
  that as an observation from one video on one day, not a rule.
  Cookie probe run 2026-09-02, with the user's approval. It closes the
  question this bullet left open, and disproves the answer it expected.

  wintest, fresh deploy of the HEAD artifact (CI run 33511414856, commit
  3fe5fc7; `git diff 3fe5fc7 HEAD -- snatch/ scripts/` empty), bundled
  binaries lifted from _MEIPASS per the method note, against the reported
  URL with the app's own flags:

    no cookies                        -> 188 formats, 37 video, 105 audio
    --cookies-from-browser chrome     -> ERROR "Failed to decrypt with
                                         DPAPI", non-zero, no JSON
    --cookies-from-browser edge       -> same

  So cookies do not yield an audio-only list on Windows; they yield
  nothing at all. SNAT-0042's account is therefore NOT the explanation for
  the Windows report, and this thread's remaining hypothesis is spent.
  SNAT-0042's fallback still stays -- it was demonstrated on Linux -- but
  it cannot reach the Windows failure, which is SNAT-0059.

  The probe's real yield is elsewhere. Reading yt-dlp's source rather than
  its output showed that a failed n challenge is a WARNING, exit 0, with
  the video formats simply absent -- and that the probe both suppresses
  warnings and reads stderr only on failure. That mechanism produces
  exactly the reported symptom and is intermittent, which is why nothing
  here ever reproduced it. Filed as SNAT-0058, with SNAT-0060 and
  SNAT-0061 for the two further defects the same reading exposed.

  Consequence for this bullet: it stays shipped and correct as a fix, and
  its Windows verification stands. What is now settled is that it never
  explained the report, and neither did SNAT-0042.
  **Layman:** Snatch was telling yt-dlp about its bundled helper program in a way yt-dlp could not read, so the helper was never used and YouTube quietly withheld all the picture qualities.
  Kind: fix.
  Source: in-session-2026-08-20.
  Lanes: downloader, packaging.

- ✅ [SNAT-0044] **No Python tooling config, so the project's own declared standards are enforced by nothing.**
  There is no pyproject.toml, ruff.toml, setup.cfg or mypy config anywhere
  in the tree. Three consequences, found by running the tools during the
  2026-08-31 whole-tree check-code pass.

  1. STANDARDS.md 10.1 declares "PEP 8 style with 100-char line limit
  (soft)". Nothing reads that. A bare `ruff check` uses its own default of
  88 and reports 79 violations; at the project's declared 100 it reports
  21. So the number a contributor sees depends entirely on how they
  invoked the tool, and the declared limit is a sentence in a document
  rather than a rule.

  2. `mypy` cannot analyse this project at all. It stops with
  `Duplicate module named "snatch" (also at "snatch.py")` and the note
  "errors prevented further checking" — the entry-point script and the
  package collide in module resolution. Zero mypy findings today is zero
  confidence, not a clean result. A `[tool.mypy]` section with an explicit
  `files` or `mypy_path` settles it.

  3. CI runs `python -m compileall` and nothing else on Python. That is
  what let SNAT-0041 ship a guaranteed NameError at startup: compileall
  proves each file parses and never imports the package, so a missing
  import is invisible to it. The cheapest possible guard is one line —
  `python -c "import snatch, snatch.app, snatch.tabs.search"` — and it
  would have caught that crash. See SNAT-0020 for the wider testing gap.

  Not urgent, but note that item 3 is a real defect class this project has
  already shipped once.
  Resolved (2026-09-02). Two of the three claims had gone stale and the
  third was wrong, so what shipped is not quite what this bullet asked
  for.

  Item 1 holds, with different numbers. pyproject.toml sets
  line-length = 100, so a bare `ruff check` now applies STANDARDS 10.1
  instead of its own 88. Re-measured today: 73 long lines at the default,
  17 at the declared limit -- the bullet said 79 and 21.

  Item 2 is no longer true. mypy 1.20.1 does not hit "Duplicate module
  named snatch"; `mypy .` analyses all 18 files. No files/mypy_path
  setting was needed. What was real is that tkinterdnd2 ships no py.typed
  and no stubs, which was every error mypy reported. With that silenced
  the run is "Success: no issues found in 18 source files", so a genuine
  type error now arrives in a report that is not already noisy.

  Item 3 was wrong, and this is the useful part. The bullet prescribes
  `python -c "import snatch, snatch.app, snatch.tabs.search"` and says it
  would have caught SNAT-0041. It would not: that fix ADDED an import for
  a name called inside a method, so the module imports cleanly and the
  NameError fires when the widget is built. Reproduced by deleting the
  import again -- compileall passed, the import check passed, and
  `ruff --select F821` reported the undefined name.

  So CI runs ruff F821,F811,F822,F823,E9, which is green today. Not the
  whole F family: F401 fires on the tkinterdnd2 re-exports and F841 on the
  Tk app object, both already adjudicated. The import check is kept for
  the class it does cover -- a missing module, a bad `from X import Y` --
  and lives in build-linux, because static-checks installs neither
  python3-tk nor the requirements and snatch.app imports tkinter at module
  level. The first gate run failed on exactly that.

  Deliberately NOT done: no project-wide ruff ignore list. 25 of the 57
  default findings are BLE001 and S110, which is SNAT-0045's whole
  subject, and silencing them here would close that item by configuration
  rather than by giving the app a logging path. The 10-file, 87-line
  import-order reformat ruff offers is also left for its own change.

  ruff pinned 0.16.4 and recorded in docs/building.md's pin table.
  **Layman:** Snatch writes down its own coding rules, but no tool is set up to check them, so nothing notices when they are broken.
  Kind: chore.
  Source: check-code-tree-2026-08-31.
  Lanes: ci, tooling.

- ✅ [SNAT-0045] **Nothing anywhere in the app records why something failed.**
  ruff S110 flags six `try/except: pass` blocks: app.py:161 (window icon),
  downloader.py:698 (closing the stdout pipe in a finally),
  downloader.py:777 and player.py:239,246 (process teardown and socket
  unlink on cancel/close), and tabs/download.py:392 (optional drag-and-drop
  registration).

  Each one is defensible in isolation — they are best-effort cleanup and
  optional-feature paths where there is genuinely no recovery action, and
  two of them are doing what CLAUDE.md mandates ("close subprocess pipes
  in finally blocks"). They were dismissed individually during the
  2026-08-31 check-code triage rather than suppressed.

  What they share is the real gap: the app imports no logging module
  anywhere, so "swallow it" is the only option available at those six
  sites. The rule's own suggestion — "consider logging the exception" —
  cannot be followed because there is nothing to log to.

  A module-level logger writing to app_data_dir(), off by default and
  enabled by an env var or a flag, would turn six silent swallows into six
  recorded ones without changing any behaviour a user sees. It would also
  give the yt-dlp subprocess failures somewhere to go.
  Resolved (2026-09-02): added snatch/logging_setup.py -- a package
  logger, off unless SNATCH_LOG is set, writing a size-capped snatch.log
  in app_data_dir() at 0o600. Wired from __main__.main() before the Tk
  root is built, so a startup failure is recorded too.

  All six try/except/pass sites now log instead of swallowing, as does the
  config-save OSError beside them, and every remaining broad handler that
  was discarding diagnostic detail: the yt-dlp download and format
  failures the bullet named, cookie extraction (whose print() reached
  nobody in a windowed build), thumbnail decode, mpv teardown and IPC, the
  system-player handoff, ffprobe, search, and all four version/self-update
  handlers.

  Measured: ruff on snatch/ went from 56 findings to 32 -- exactly the 18
  BLE001 and 6 S110 removed, none introduced. Both rules stop firing once
  a handler logs the exception, so they close by being fixed rather than
  by the pyproject.toml suppression that comment refused. 12 new tests in
  tests/test_logging_setup.py cover off-by-default, the level parsing, the
  0o600 mode, idempotence and an unwritable directory; suite is 47 green.

  Enable mechanism is the env var alone, confirmed with the user -- no
  config key and no settings-UI toggle. Documented in README (how to get
  a log to attach to an issue) and CLAUDE.md Quick Reference. STANDARDS.md
  was deliberately NOT given a new rule: ruff already fires on any fresh
  bare swallow, which is a mechanical guard rather than prose.
  **Layman:** When something goes wrong quietly, Snatch has no record of it, so a problem that does not show a message leaves no trace at all.
  Kind: enhancement.
  Source: check-code-tree-2026-08-31.
  Lanes: diagnostics.

- 📋 [SNAT-0046] **Every theme class carries a NAME attribute that nothing reads.**
  vulture flags `NAME` as unused on all seven theme classes
  (theme.py:8, 35, 62, 89, 116, 143, 170). Verified during the 2026-08-31
  check-code triage: nothing in the tree reads `.NAME`, and STANDARDS.md
  3.1's table of required theme attributes does not list it.

  The name a theme is actually known by is the key in the THEMES dict at
  theme.py:196. app.py:185 builds the combobox from `list(THEMES.keys())`
  and app.py:233 passes that string back to `set_theme`, which looks it up
  in the same dict. So each theme's name is stored twice and only one copy
  is ever consulted.

  Left unfixed rather than deleted because there are two valid
  resolutions and choosing between them is a design call, not an edit.
  Either drop the seven attributes, or make the registry and the combobox
  read `.NAME` so a theme owns its own display name and the dict key
  becomes an internal id. The second is the better shape if a theme should
  ever display differently from its key; the first is correct if it should
  not.
  **Layman:** Each colour scheme stores its own name twice, and the app only ever uses one of the two copies.
  Kind: refactor.
  Source: check-code-tree-2026-08-31.
  Lanes: ui.

- 📋 [SNAT-0047] **The three build jobs share a pip cache with pull-request runs.**
  zizmor reports cache-poisoning, three occurrences, against the `on:`
  block. All three build jobs pass `cache: "pip"` to actions/setup-python
  (ci.yml:62, 112, 147), and the workflow triggers on pull_request as well
  as on push and on v* tags.

  The shape zizmor is describing: a pull-request run populates the pip
  cache, and a later tag-triggered run — the one that produces the
  artifacts attached to a GitHub Release — restores from it. The release
  build would then be assembled partly from wheels a PR put there.

  Not in SNAT-0035's scope: that bullet enumerates exactly three issues
  from the 2026-08-20 zizmor run (unpinned-uses, excessive-permissions,
  artipacked) and this is a fourth, surfaced by the 2026-08-31 pass.

  No evidence it has been exploited, and the exposure is smaller than it
  reads: this repo has no PR history from outside contributors. The
  cheapest fix is to skip the cache on tag builds —
  `cache: ${{ startsWith(github.ref, 'refs/tags/v') && '' || 'pip' }}` or
  an explicit condition — which costs the release build one dependency
  download and nothing else. Worth doing alongside SNAT-0035 rather than
  separately, since both edit the same five job definitions.
  **Layman:** Builds reuse downloaded packages from a shared store that outside contributions can also write to.
  Kind: security.
  Source: check-code-tree-2026-08-31.
  Lanes: ci, supply-chain.

- 📋 [SNAT-0048] **Blocking work still runs on the GUI thread, and a Tk variable is still read from a worker.**
  STANDARDS.md 4.1 rule 1 ("All blocking operations run in daemon
  threads") and rule 2 ("Never modify GUI from a thread") are both
  unconditional, and three lanes of the 2026-08-31 sweep found breaches
  independently. Two of the four are fixed; these two are not.

  1. player.py:171-205 `_mpv_command` opens a socket, sendall's and
  recv's with settimeout(0.5), and every caller runs it on the MAIN GUI
  thread: `_update_player_state` (:290), `_on_volume_change` (:261),
  `_on_seek_release` (:270), `_toggle_play_pause` (:224).
  `_on_volume_change` is a Scale `command` callback, so it fires once per
  drag increment, each a full connect/round-trip/close. Against a wedged
  mpv the UI freezes 0.5 s per event, and the poller does two round-trips
  every 500 ms. Fix: hold one persistent socket, or move `_mpv_command`
  onto a worker and marshal results back with root.after(0, ...) as 4.2
  prescribes.

  2. downloader.py:223 calls `_extract_browser_cookies()` inside
  `_fetch_formats_thread`, and that method does
  `self.cookies_file_var.set(result)` at downloader.py:109 -- a Tk
  variable WRITE from a daemon thread. Fix: return the path and set the
  var inside root.after(0, ...).

  Also filed here because it is the same class: search.py:318 reads
  `self.search_duration_var.get()` inside `_search_thread`. Depending on
  the _tkinter build that takes the Tcl lock or raises RuntimeError. Fix:
  read it in `_perform_search` on the main thread and pass it as a third
  args= element, as `search_target` and `count` already are.

  Not done in the 2026-09-01 fix pass, which was scoped to CRITICAL and
  HIGH. These are the MEDIUM tail of the same contract.
  **Layman:** Some buttons talk to the video player in a way that can freeze the window, and one search setting is read from the wrong place, which can crash on some systems.
  Kind: fix.
  Source: review-code-sweep-2026-08-31.
  Lanes: threading.

- ✅ [SNAT-0049] **Search can start twice, and then claims to be searching forever.**
  search.py:223-226 `_start_search_anim` does not cancel an in-flight
  animation, and `_perform_search` has no re-entrancy guard -- the Search
  button (:47) and <Return> (:34, :43) all call it unconditionally.

  Two clicks start two `after` chains. `_tick_search_anim` (:233) stores
  its id into the same attribute, so `_stop_search_anim` can cancel only
  one of them. The survivor rewrites `search_status_var` every 400 ms
  forever, overwriting the "N results" line at :359, so the UI reads
  "Searching....." indefinitely after the search has finished.

  The same missing guard starts a second 120-second yt-dlp subprocess per
  click, and opens a window in which `self.search_results` (set from the
  thread at :331) and the tree contents (set at :355) come from DIFFERENT
  searches -- so a click downloads a different video from the one
  highlighted. That last consequence is the reason this is not merely
  cosmetic.

  Fix: call `self._stop_search_anim()` as the first line of
  `_start_search_anim`, and gate `_perform_search` on an `is_searching`
  flag that the display and error callbacks clear. The equivalent guard
  for downloads landed on 2026-09-01; this one did not.

  Related open question the lane could not settle: search.py:331 sets
  search_results from the thread while app.py:251 clears it on a theme
  switch, so a theme change during an in-flight search may leave the tree
  populated with search_results empty, and every row then reports "Select
  a search result first".
  Resolved (2026-09-02). _start_search_anim now cancels any chain already
  running before starting one, so the status label can no longer be left
  cycling by an uncancellable loop. _perform_search is gated on
  self.is_searching -- the same flag shape start_download uses -- set
  before the worker starts and cleared by both _display_search_results and
  _search_error, which are the only two ways the worker ends.

  The stale-pairing consequence is closed at its source rather than by the
  guard alone: _search_thread no longer assigns self.search_results. That
  now happens inside _display_search_results, on the main thread and in the
  same call as the tree rows, so _change_theme cannot clear the list
  between the two. This settles the open question the lane left about a
  theme switch during an in-flight search.

  Verified by running: tests/test_search_reentrancy.py, six tests, all six
  FAIL against the pre-fix source and pass after. Full suite 53 green.
  Ruff over snatch/ and tests/ is unchanged at 36 lines before and after,
  so the change introduced no new finding.
  **Layman:** Clicking Search twice leaves the box saying "Searching..." for good, runs two searches at once, and can download a different video from the one you picked.
  Kind: fix.
  Source: review-code-sweep-2026-08-31.
  Lanes: ui, search.

- 📋 [SNAT-0050] **Parsers assume shapes that yt-dlp and ffprobe do not guarantee.**
  search.py:311-332 makes two shape assumptions about
  `yt-dlp -J --flat-playlist` that the tool does not guarantee.
  `data.get("entries", [])` returns None rather than [] when a playlist
  has no listable children, because yt-dlp emits JSON null there, and
  `for entry in entries` then raises TypeError. Individual elements are
  also null for deleted, private or region-blocked videos, so
  `entry.get(...)` raises AttributeError. Inside the thread that lands in
  the catch-all at :336 and shows a bare exception string; in
  `_display_search_results` (:344, main thread, no try) it is an
  unhandled Tk traceback with the tree half-populated. Fix:
  `entries = data.get("entries") or []` then filter on isinstance dict.

  media_info.py:112 runs ffprobe with `capture_output=True` and no output
  cap. A file with thousands of streams or chapters sends unbounded stdout
  into memory and then into a tk.Text.

  Open question the lane could not settle without running it: for a
  channel path (`https://www.youtube.com/@x/videos`) does
  `-J --flat-playlist` return videos directly, or a nested tab-playlist
  whose entries are themselves playlists? search.py:311 assumes flat. If
  it is nested, the results table shows tab names rather than videos.

  Also: downloader.py:288 reads a thumbnail response with no byte cap.
  The URL comes from remote JSON (:272) and the 10 s timeout at :287
  bounds latency, not size. STANDARDS.md 6.3 requires capping network
  buffers.
  **Layman:** Some kinds of playlist or video make Snatch fail with a raw error instead of a clear message.
  Kind: fix.
  Source: review-code-sweep-2026-08-31.
  Lanes: parsing.

- 📋 [SNAT-0051] **The config loader crashes the app on four corrupt shapes it does not catch.**
  STANDARDS.md 7.3 promises "Graceful fallback: Returns {} on
  missing/corrupt config". app.py:123-129 catches only FileNotFoundError
  and json.JSONDecodeError, so four shapes escape and crash startup:
  valid JSON that is not an object (AttributeError on `saved_config.get`
  at app.py:47), UnicodeDecodeError, and PermissionError /
  IsADirectoryError.

  A fifth is type confusion rather than a parse failure: `last_tab`
  (app.py:108-109) goes straight into `0 <= last_tab < ...`, so
  `"last_tab": "2"` raises TypeError, and `window_geometry` (app.py:101)
  goes straight to `self.root.geometry(...)`, so a malformed value raises
  TclError.

  The identical defect in history.json was fixed on 2026-09-01 -- widen
  to `except (OSError, ValueError)` and validate the shape before use.
  This is the same fix in the other file; it was left because it is
  MEDIUM where the history one was HIGH (history.json is written far more
  often, so it is the one likely to be found truncated). The atomic write
  half IS already done here: app.py:148 now goes through
  utils.write_private_json.

  Related, same file: app.py:101's saved geometry is `WxH+X+Y`, not
  `WxH` as STANDARDS.md 7.1 describes, so a geometry saved on a monitor
  that is no longer attached reopens the window off-screen. And
  theme.py:215-219 falls back to DarkTheme for an unknown theme name
  while theme_var keeps the bogus string, which _save_config then writes
  back -- so a typo'd theme name is persisted forever while the app
  silently runs Dark.
  **Layman:** A damaged settings file can stop Snatch opening, and the only fix is deleting a file you cannot see is the cause.
  Kind: fix.
  Source: review-code-sweep-2026-08-31.
  Lanes: config.

- 📋 [SNAT-0052] **The mpv socket lands in a shared /tmp with a predictable name.**
  CLAUDE.md's mandatory rules say "Validate directory ownership for
  security-sensitive paths (mpv socket)" without qualification.
  player.py:100-102 validates only the XDG_RUNTIME_DIR branch: the
  fallback it jumps to is never checked at all, and the socket is then
  placed at `snatch-mpv-{os.getpid()}` -- fully predictable.

  On a Linux box with no XDG_RUNTIME_DIR (non-systemd, an su session, a
  container) that is /tmp: shared, world-writable, sticky. mpv's IPC
  accepts every input command including loadfile and run, so whoever can
  connect owns the process's command surface. Whether they can depends on
  the inherited umask, which this code does not control. Secondary: the
  check tests st_uid but not mode, so a self-owned 0777 runtime dir
  passes.

  Fix: `tempfile.mkdtemp(prefix="snatch-")`, which is 0700 by
  construction, put the socket inside it, and shutil.rmtree it in
  _stop_player. That also removes the predictable name. The same edit
  fixes player.py:103-104, where an unguarded os.unlink -- the sibling
  copy at :243-247 IS guarded -- raises an uncaught PermissionError out
  of _play_in_mpv if the path is squatted in a sticky /tmp, producing a
  traceback and no player.

  Raw severity from the lane was HIGH; calibrated to MEDIUM for the
  2026-09-01 pass because it requires a hostile local user on a shared
  machine, which is outside this app's derived threat model. Kept
  visible: it is a mandatory rule stated unconditionally and the fix is
  small. Note the project has no SECURITY.md and no written threat model,
  so that calibration was derived rather than read -- see SNAT-0054.

  Same file, lower: player.py:129 puts the cookie file path in mpv's
  argv, readable from /proc/<pid>/cmdline by any local user, against
  STANDARDS.md 5.2. A comma anywhere in that path also silently breaks
  mpv's option parsing.
  **Layman:** On a computer shared with other people, another user could in principle send commands to Snatch's video player.
  Kind: security.
  Source: review-code-sweep-2026-08-31.
  Lanes: security.

- 📋 [SNAT-0053] **Install advice, exception handling and constants have drifted apart across modules.**
  Three related classes from the 2026-08-31 sweep, none individually
  worth its own item.

  DIVERGED INSTALL ADVICE. media_info.py:122-127 branches two ways --
  Windows, else "sudo apt install ffmpeg". player.py:14-36
  `_no_player_message()` branches THREE ways and its docstring records
  why: "The advice here used to be 'sudo apt install mpv' on every
  platform, which is wrong on Windows and macOS." That fix was never
  applied to the ffmpeg copy, so a macOS user with no ffmpeg is told to
  run apt, and so is every openSUSE, Fedora and Arch user -- on a project
  whose own primary machine is openSUSE. Fix: hoist a shared
  `_install_hint(tool)` into platform_utils and have both call it.

  BROAD EXCEPT. version.py:70, :88, :110, :265 are four bare
  `except Exception:`, two of which discard the exception object
  entirely: :70 reports "yt-dlp not found" for a TimeoutExpired, a
  PermissionError or a corrupt binary alike, and :88 collapses every
  failure of the GitHub check into "Check failed".
  ~/.claude/standards/languages/python.md is explicit -- "Catch what you
  can name". This is the class of blindness that let both SNAT-0020 bugs
  ship through two releases. Same shape at player.py:204 and
  cookies.py:109.

  MAGIC NUMBERS. search.py:297 (timeout=120), :323-327 (240, 1200),
  media_info.py:112 (timeout=30), version.py:63 and :78 (timeout=10),
  utils.py:53 (timeout=300). CLAUDE.md and STANDARDS.md 6.4 both require
  named constants for timeouts and thresholds, and several of these
  modules already define some.

  Also: cookies.py:109-111 reports the whole Firefox extraction failure
  with `print()`, which in a packaged windowed build goes nowhere -- and
  the printed text carries the sqlite path, against STANDARDS.md 5.2. See
  SNAT-0045 for the underlying absence of any logging path.
  **Layman:** Snatch tells Mac and Linux users the wrong command to install a missing tool, and hides the reason when something fails.
  Kind: fix.
  Source: review-code-sweep-2026-08-31.
  Lanes: consistency.

- 📋 [SNAT-0054] **There is no written threat model, so every security judgement is derived rather than read.**
  The project has no SECURITY.md, no threat-model section in README.md or
  STANDARDS.md, and no .semgrep.yml threat block. STANDARDS.md section 5
  states security RULES -- validate URLs, use --, no shell=True, 0o600,
  realpath, HTTPS-only -- but never says who the adversary is.

  This surfaced during the 2026-08-31 review sweep, where the severity
  calibration had to be performed against a model derived from what the
  app is rather than one the project had written down. That was stated in
  the report as a weaker basis than it should be. Two findings were
  calibrated DOWN on it -- the /tmp mpv socket (SNAT-0052) and the
  unvalidated binary-execution directory in platform_utils.py:162 -- and
  two calibrated UP, the self-update integrity gap and the AppImage
  runtime, both since fixed. If the derived model is wrong, those four
  moved the wrong way.

  The model that was derived, and which is the thing to confirm or
  replace: a single-user desktop GUI run by its owner on their own
  machine; no service, no multi-tenancy, no untrusted local users
  assumed. The adversaries that reach it in practice are the remote
  endpoints it fetches from (the yt-dlp nightly releases, the GitHub API,
  thumbnail CDNs, the AppImage runtime), and the content it was asked to
  fetch and parse. A hostile local user on a shared machine is real but
  secondary.

  Writing that down is maybe twenty lines, and it converts every future
  security judgement in this project from a guess into a lookup. It also
  gives review-code's threat-model calibration step something to read,
  which is the specific thing it went without.
  **Layman:** Nobody has written down who Snatch is defending against, so each person deciding whether something is a security problem has to guess.
  Kind: doc.
  Source: review-code-sweep-2026-08-31.
  Lanes: security, docs.

- ✅ [SNAT-0055] **Eight places where STANDARDS.md or CLAUDE.md describe code that no longer works that way.**
  Each was verified against current source by a lane of the 2026-08-31
  sweep. Three sibling defects of the same class WERE fixed on
  2026-09-01 -- STANDARDS 4.1/4.2 (the lambda binding), 5.3 (the file
  permission pattern) and 12.2 (the --js-runtimes form) -- because each
  was actively teaching a shipped bug. These eight are stale rather than
  harmful, so they were deferred together rather than fixed piecemeal.

  In every case below the DOCUMENT is the wrong side, not the code.

  1. STANDARDS 5.1 quotes _is_valid_url without the empty-URL guard the
  real one carries at downloader.py:76-77.

  2. STANDARDS 8.2, 8.4 and 2.1, and CLAUDE.md's Quick Reference, all
  present HAS_MPV as the live mpv detection surface. It has ZERO readers
  tree-wide; find_mpv() (platform_utils.py:216) is the real gate and
  prefers the bundled copy, which player.py:82-85 explains. Found by two
  lanes independently. Either delete HAS_MPV or have something adopt it,
  then fix all four documents.

  3. Same paragraph: HAS_PIL is documented as living in
  snatch/__init__.py and actually lives at downloader.py:21.

  4. STANDARDS 12.3 states the cookie priority as cached file, then
  browser SQLite, then --cookies-from-browser. cookies.py:117-125 does
  the opposite -- a selected browser always wins -- and its comment says
  the inversion is deliberate. NOTE: the code half of this is a real bug
  and is filed separately as SNAT-0053's remediation-loop item; only the
  ordering is the document's fault.

  5. STANDARDS 7.1's persisted-settings table omits last_tab, which
  app.py:145 does persist, and calls window_geometry "Window size (WxH)"
  when root.geometry() returns WxH+X+Y.

  6. CLAUDE.md states "All subprocess calls need timeout" with no
  exception. downloader.py:637 and :701 are a download and its wait, and
  cannot carry a fixed one. The rule needs an explicit long-running
  carve-out or it is unfollowable as written.

  7. pyinstaller.spec:4 says it is invoked by .github/workflows/build.yml
  after that workflow downloads the binaries. No build.yml exists
  (ci.yml is the only workflow) and it is the build SCRIPTS, not the
  workflow, that call fetch-binaries.sh.

  8. scripts/local-ci.sh:59 labels its actionlint step "workflow syntax +
  action pinning". actionlint does not check pinning -- it passed clean
  on 14 mutable tags. zizmor is what catches those and the gate does not
  run it. SNAT-0035 already proposes adding zizmor to static-checks; the
  label should stop claiming coverage until it does.

  STANDARDS.md is a contract document, so a change of direction here runs
  CLAUDE.md rule 14's gate. Most of these are corrections of false claims
  and sit in its exemption; item 6 is a genuine rule change and item 2
  turns on a code decision first.
  Progress (2026-09-02): three of the eight are fixed, as collateral of
  SNAT-0056's review gate rather than by working this list.

  Item 1 (5.1 quoted without the empty-URL guard) is fixed. A lane made
  the case this list did not: re.match raises TypeError on None rather
  than rejecting it, so a validator re-derived from the snippet fails open
  into an exception instead of returning False.

  Item 4 (12.3's cookie priority) is fixed, and it was the largest single
  finding of that gate. Two lanes found it; the section now states the
  code's real order, verified by calling get_cookie_args -- a Firefox
  selection with a cached file present returns the browser flag.

  Item 5 is HALF fixed. The last_tab row is in 7.1's table. The
  window_geometry label still says "Window size (WxH)" where geometry()
  returns WxH+X+Y, and no lane raised it.

  Five remain: 2, 3, 5's label half, 6, 7 and 8.

  Worth recording about item 2: HAS_MPV having zero readers went unfound
  by all nine lanes across three loops, though every loop read 8.2. A
  cold read is good at contradiction and bad at absence -- nothing in the
  document points at the missing thing, so there is no passage to
  disbelieve. Items 7 and 8 are the same shape and should be expected to
  survive a review gate too; they need this list, not another lane.
  Resolved (2026-09-02): all eight are addressed. Three fell out of
  SNAT-0056's review gate; the other five were worked from this list
  afterwards, and that split is the useful part of the record.

  Items 1, 4 and 5's table half were found by cold lanes. Items 2, 3, 5's
  label half, 6, 7 and 8 were not, by any of the nine lanes across three
  loops -- and they are all the same shape. Each is an ABSENCE or a
  mis-attribution: a constant nothing reads, a symbol living in a
  different module, a label that understates, a rule with no carve-out, a
  citation to a file that was never created. A cold reader is good at two
  passages contradicting each other and poor at a claim with nothing
  behind it, because there is no second passage to disbelieve. A written
  list is the right instrument for that class, and running a review gate
  is not a substitute for one.

  What changed:

  2. STANDARDS 2.1, 8.2 and 8.4 and CLAUDE.md now say find_mpv() is the
  gate and that HAS_MPV is a legacy constant nothing reads. The code half
  -- delete it or adopt it -- is deliberately NOT done here; the documents
  are true either way, and they were teaching the wrong gate meanwhile.
  Verified: find_mpv() checks the bundled copy first, which is exactly
  what a shutil.which at import time misses.

  3. CLAUDE.md now names where each flag lives rather than implying both
  sit in __init__.py.

  5. The last_tab row landed during the gate. The label half is fixed
  here: root.geometry() returns WxH+X+Y, measured under Xvfb, so "Window
  size (WxH)" understated what is stored.

  6. The timeout rule now carries its carve-out. Every subprocess.run
  does have a timeout -- a first grep here said otherwise and was wrong,
  having missed one split across two lines. The real exception is the
  download: Popen plus an unbounded wait(), bounded by terminate/kill
  rather than by a duration.

  7. pyinstaller.spec cited .github/workflows/build.yml, which has never
  existed. It is invoked by the three build scripts, which fetch binaries
  first; ci.yml calls those scripts. SNAT-0001's own body cited a
  build-windows.yml that does not exist either, and was corrected with it.

  8. local-ci.sh's actionlint step no longer claims to check action
  pinning. It never did, and the gate does not run zizmor; the label now
  points at SNAT-0035 instead of implying coverage.
  **Layman:** The project's own rulebook is wrong in eight places, so anyone following it writes the wrong thing.
  Kind: doc-fix.
  Source: review-code-sweep-2026-08-31.
  Lanes: docs.

- ✅ [SNAT-0056] **STANDARDS.md 5.3 changed direction without the review gate rule 14 asks for.**
  On 2026-09-01, STANDARDS.md 5.3 was rewritten to prescribe
  utils.atomic_private_write / write_private_json in place of
  os.open(path, O_WRONLY|O_CREAT|O_TRUNC, 0o600). The old form does not
  deliver the guarantee the section states, so the correction is right
  (SNAT-0006 has the measurement).

  What did not happen is the gate. CLAUDE.md rule 14 covers a document
  that is built UNDER -- a standard qualifies -- and its trigger is
  "would someone conforming to this document now do something different?
  Name the line." Here the answer is yes and the line is nameable: a
  conformer writing a sensitive file now calls a helper rather than
  os.open. That is the gated branch, not the exemption.

  Two other STANDARDS edits in the same pass ARE exempt and are not in
  scope here: 4.2 and 12.2 both removed a contradiction in favour of a
  passage that already said the right thing and did not change, which is
  rule 14's Q2 being answered rather than a change of direction.

  The determination was recorded in the commit body of the pass, which is
  where rule 14 says to put it -- and a commit body is not where a future
  session looks, which is why it is also here.

  To close: run `review-contract STANDARDS.md --genre standard`, or
  decide on the record that the edit does not warrant it and say why.
  Either is a legitimate outcome; the current state -- gated branch,
  no gate, no visible record outside a commit message -- is not.
  Resolved (2026-09-02): the gate ran. Three cold loops, three lanes each,
  genre pinned standard. 27 verified findings, 27 fixed; cap reached at
  loop 3, which for a standard is the exit rather than a question.

  The Q3 this bullet predicted was real and was found on loop 1. 5.3
  stated the whole obligation for a sensitive file as "write it through
  atomic_private_write", when the guarantee for a file that already exists
  comes from PRIVATE_DATA_FILES driving a startup repair pass the section
  never mentioned. A conformer adding a fourth sensitive file was fully
  compliant as written and silently outside that pass. That is exactly the
  "cannot tell they have breached" shape, and it existed because the
  2026-09-01 rewrite changed direction without this review.

  What the bullet did not predict is how little of the run was about 5.3.
  Roughly 3 of the 27 findings landed inside the span that armed the gate;
  the rest were pre-existing defects elsewhere in a 577-line document that
  had never been reviewed. Rule 14 fires on a change of direction, and
  every lane reads the whole document, so this was a gate and an audit at
  once -- and the audit was where the value was.

  The largest single defect was not in 5.3 at all. 12.3 stated the cookie
  priority in exactly the reverse of the code: a selected browser wins for
  every browser, Firefox included, before the cached cookies.txt is
  considered. No lane in loops 1 or 2 read that section -- all six said so
  -- so a third loop bought coverage rather than repair. At 630 lines this
  document is large enough that two cold reads did not reach parts of it.

  A recurring theme worth carrying forward: the document repeatedly
  generalises to Windows what only holds on POSIX. Three separate findings
  were that shape, including a snippet that calls os.getuid on the build
  14 documents.

  Closes three of SNAT-0055's eight recorded items (1, 4, 5); five remain,
  and item 2 went unfound by all nine lanes.

  Loop log: docs/standards-review-log.md. The code-side defect the run
  surfaced but did not fix is SNAT-0063.
  **Layman:** A rule in the project's own standards was rewritten, and the independent check that is supposed to run on such a change did not.
  Kind: doc.
  Source: in-session-2026-09-01.
  Lanes: docs, process.

- 📋 [SNAT-0057] **The project has no specs directory, no decision records and no declared test root.**
  Found while running Phase 0 of write-code on 2026-09-01.
  invariant_check returned scanned_nothing:true with the hint
  "docs/specs does not exist", and there is no docs/decisions/ either.
  task_priors returned specs_count 0 and adrs_count 0 for the same
  reason -- so both verbs report an absence of contracts that is a fact
  about the layout rather than about the project.

  The consequence is not hypothetical. Several decisions taken during the
  2026-08-31 review pass now live ONLY in commit bodies: why the mpv
  named-pipe path was scoped out rather than implemented, why appimagetool
  was pinned to 1.9.1 rather than tracking continuous, why the Revert
  button lost its is_frozen() guard, and why the type2-runtime pin moved
  to an older dated tag than the continuous build it replaced. A commit
  body is searchable but nobody reads git log to find a contract.

  spec-format.md section 1 is explicit that most work needs no spec, and
  that is very likely true here -- this is not an argument for writing
  specs. It is an argument for having somewhere to put an ADR when a
  decision is genuinely load-bearing, which four of the above are.

  Cheapest useful version: create docs/decisions/ and write ADR-0001 for
  the supply-chain pinning policy, which is the decision most likely to be
  reopened by a future session that sees an old pin and "helpfully" bumps
  it.

  Separately, .ants/project.json was created on 2026-08-31 declaring
  source_roots, docs_dir, roadmap and changelog. test_roots and specs_dir
  were deliberately left undeclared: docs/specs does not exist, and the
  only test is a build-time smoke script under scripts/, which is not a
  test root. Every declared path must resolve or the write is rejected, so
  those two cannot be declared until they exist. Revisit alongside
  SNAT-0020.
  **Layman:** There is nowhere in this project to write down a design decision, so they only exist in commit messages and chat.
  Kind: doc.
  Source: in-session-2026-09-01.
  Lanes: docs, process.

- ✅ [SNAT-0058] **A failed JS challenge drops video formats with no sign to the user: the probe suppresses the warning and only reads stderr on failure.**
  Read out of yt-dlp's own source, 2026.08.19. When the n challenge
  cannot be solved the youtube extractor calls report_warning with "n
  challenge solving failed: Some formats may be missing" -- a WARNING.
  yt-dlp still exits 0 and still emits a payload; the video formats are
  simply absent from it.

  _probe_formats defeats that signal twice over. It passes --no-warnings,
  which suppresses the message, and _fetch_formats_thread inspects stderr
  only inside the `returncode != 0` branch, which a warning never enters.
  So a partial answer is byte-indistinguishable from a complete one and
  the user is shown whatever survived -- audio and storyboards.

  This is the first mechanism found that actually produces the reported
  Windows symptom, and it fits the evidence SNAT-0043 gathered: that
  user's history holds an "audio only mp4" and a "48x27 mhtml" storyboard
  for the reported URL, which is what a stripped format list offers. It
  also explains why the symptom does not reproduce -- the challenge
  succeeds today, so the full list comes back. It is intermittent by
  nature.

  The durable fix does not string-match yt-dlp's wording, which is what
  rots across updates. _has_video_format already exists: a non-playlist
  payload carrying no video format at all IS the signal, whatever yt-dlp
  calls it that release. Warn on that condition.
  Resolved (2026-09-02). _probe_formats no longer passes --no-warnings,
  so yt-dlp's account of a stripped answer survives, and
  _fetch_formats_thread now checks the observable after both cookie
  retries: a non-playlist payload carrying no video format at all adds a
  note to the status line.

  The trigger is the observable, never the wording. _no_video_note uses
  yt-dlp's text only to SHARPEN the sentence -- "the site's JavaScript
  challenge failed" when stderr says a solve failed, and an honest
  generic line otherwise, since a source may genuinely offer audio only.
  A reworded yt-dlp release costs the detail and not the warning.

  Collateral handled in the same change: with warnings no longer
  suppressed, the fatal branch's test for "n challenge solving failed"
  would have blamed a missing runtime for any unrelated failure that
  happened to carry the warning. A challenge failure exits 0, so it can
  never be why a run failed; that branch now tests only for a missing
  runtime.

  Verified with stubbed probe results: a challenge warning is explained,
  a quiet audio-only answer still warns without blaming, and a healthy
  fetch stays silent. A live yt-dlp run confirmed stdout still parses as
  JSON with warnings on stderr.
  **Layman:** When YouTube's puzzle-solving step fails, only the sound tracks come back and Snatch says nothing is wrong — so the user sees an audio-only list and no explanation.
  Kind: fix.
  Source: in-session-2026-09-02.
  Lanes: downloader.

- ✅ [SNAT-0059] **The retry-without-cookies fallback cannot fire on a cookied probe that exits non-zero.**
  SNAT-0042's fallback sits AFTER the `returncode != 0` guard in
  _fetch_formats_thread, so it only runs when the cookied probe succeeded
  and came back without video. A cookied probe that fails outright skips
  it and dead-ends in the generic error dialog.

  That is not hypothetical: it is the failure Windows actually produces
  (see the App-Bound Encryption bullet). Measured on wintest 2026-09-02
  with the bundled yt-dlp -- --cookies-from-browser chrome and edge both
  abort with "Failed to decrypt with DPAPI", non-zero, empty stdout, no
  JSON. The same fetch with no cookies returns the full list.

  Fix: when cookie arguments were used and the probe exits non-zero,
  retry once without them before reporting anything. Keyed on the exit
  code and on whether cookies were passed -- no message matching, so it
  survives yt-dlp rewording its errors.
  Resolved (2026-09-02). _fetch_formats_thread retries once without
  cookies when the cookied probe exits non-zero, before any error is
  reported. Keyed on the exit code and on whether cookies were sent -- no
  message matching, so no rewording of yt-dlp's errors can stop it.

  One further gap closed to make the fix actually deliver: _download_thread
  built its cookie arguments fresh, so a fetch could recover and the
  download that followed would rebuild the same failing arguments and die
  -- worse than not offering the source, because the format list looks
  healthy first. _get_cookie_args now drops a cookie source this session
  has proved unreadable. It is keyed on the arguments themselves rather
  than a flag, so choosing a different browser is tried afresh with no
  reset step.

  Verified with stubbed probe results: the hard failure recovers, is
  reported, raises no dialog, and the proven-bad source is absent from
  the next command while a different browser is retried.
  **Layman:** Snatch knows to try again without your browser cookies when they cause trouble — but only if the first try half-worked. If it fails outright, the safety net never opens.
  Kind: fix.
  Source: in-session-2026-09-02.
  Lanes: downloader.

- ✅ [SNAT-0060] **The age-restriction branch matches a string yt-dlp no longer emits, so it is unreachable.**
  _fetch_formats_thread tests stderr for "Sign in to confirm your age".
  That phrase does not occur anywhere in yt-dlp 2026.08.19 -- grepped the
  installed package including the whole youtube extractor. The extractor
  now relays whatever the site said via `Youtube said: {message}`, so the
  text is server-supplied and not a constant yt-dlp owns.

  Everything behind that test -- the cookie refresh, both tailored
  dialogs -- is therefore dead code, and an age-gated video falls to the
  generic error instead.

  This is the clearest instance of the general problem: Snatch classifies
  yt-dlp failures by matching human-readable prose, and that prose is not
  an interface. Whatever replaces this branch should key on something
  observable rather than on wording.
  Resolved (2026-09-02). The dead branch is gone. Nothing replaced it as
  a string test, because yt-dlp relays whatever the site said and there is
  no stable phrase to match.

  The generic error path now carries the useful half, gated on what the
  app itself knows: the fetch failed and no cookie source was configured.
  That covers age gates, sign-in walls and bot checks alike and cannot
  rot on a rewording. Where cookies WERE tried it stays quiet rather than
  suggesting what already failed.

  _extract_browser_cookies keeps its other caller, the Refresh Cookies
  button, so nothing was orphaned.

  Verified with stubbed probe results: a failure with no cookie source
  carries the suggestion, and a failure after cookies were tried does
  not.
  **Layman:** Snatch watches for a specific YouTube error message to offer cookie help. yt-dlp stopped using that wording, so that help can never appear.
  Kind: fix.
  Source: in-session-2026-09-02.
  Lanes: downloader.

- ✅ [SNAT-0061] **On Windows the browser dropdown offers Chromium browsers whose cookies yt-dlp cannot decrypt.**
  Chrome's App-Bound Encryption puts Chromium cookie stores out of
  yt-dlp's reach on Windows (yt-dlp issue 10927). Measured on wintest
  2026-09-02 against the reported URL: chrome and edge both fail with
  "Failed to decrypt with DPAPI" and return nothing at all.

  yt-dlp's cookies.py groups brave, chrome, chromium, edge, opera,
  vivaldi and whale as Chromium-based; firefox and safari take other
  paths, and firefox is unaffected on Windows. So the dropdown currently
  offers Windows users several choices that cannot succeed.

  Deliberately NOT fixed by hard-coding a per-platform blocklist: this is
  yt-dlp's limitation to lift, and a blocklist would outlive it silently.
  The durable half is the graceful fallback in the sibling bullet. A hint
  naming the browser when that fallback fires is the useful addition.
  Resolved (2026-09-02). No blocklist, as the bullet asked -- the dropdown
  still offers every browser, because this is yt-dlp's limitation to lift
  and a blocklist here would outlive the fix silently.

  What landed is the wording. CHROMIUM_BROWSERS carries yt-dlp's own
  grouping, and _cookie_failure_note names the browser and says Firefox is
  unaffected when the failure happens on Windows with a Chromium browser
  selected. It decides nothing: the recovery it reports was keyed on the
  exit code, so an unrecognised browser still recovers and still gets a
  note, just a generic one.

  Verified both wordings by forcing the platform check.
  **Layman:** On Windows, picking Chrome or Edge for cookies simply cannot work — Chrome locks them in a way yt-dlp can't open — yet Snatch still offers both.
  Kind: fix.
  Source: in-session-2026-09-02.
  Lanes: downloader, ui.

- ✅ [SNAT-0062] **A published build must bundle the newest yt-dlp, so the app asks the user for nothing on first launch.**
  User request. The update machinery was already correct: the app offers an
  update only when the latest nightly is NEWER than the copy in use. What
  was wrong was its input -- YTDLP_VERSION was pinned by hand with a comment
  saying to bump it when playback started failing, so a release cut today
  shipped whatever tag was last remembered. Measured at the time of this
  change: the pin was 2026.08.18.122307 against a latest of
  2026.08.30.232658, twelve days behind. A user downloading that build was
  prompted to update immediately, which is precisely the ask this item
  removes.

  scripts/update-ytdlp-pin.sh re-resolves the pin to the newest nightly and
  rewrites both scripts/fetch-binaries.sh and the versions table in
  docs/building.md, so the two cannot drift into disagreeing about what a
  build ships. --check reports without writing and exits non-zero when the
  pin is behind, so the condition is testable before publishing.

  The pin is kept rather than floated. It records exactly what a given build
  shipped, which is what makes a build reproducible and what allows a bad
  nightly to be identified afterwards; what changed is that publishing
  re-resolves it instead of trusting recall. The stale comment above the pin
  was rewritten in the same change, since it prescribed the old policy.

  Scope: the bundled binary only. requirements.txt tracks stable yt-dlp
  deliberately and is not imported as a library -- docs/building.md already
  carries that note, and moving one pin because the other moved is the
  mistake it exists to prevent.

  Verified: bumped 2026.08.18.122307 -> 2026.08.30.232658, re-run reports
  nothing to do, the fetched binary reports the new version, and a probe
  with the app's own flags returns the same 188 formats / 37 video with no
  warnings.
  **Layman:** Every release now ships the newest downloader, so the app does not immediately ask you to download an update the moment you install it.
  Kind: chore.
  Source: user-request-2026-09-02.
  Lanes: packaging.

- 📋 [SNAT-0063] **The permission test's fixture cannot grow with the list it tests.**
  scripts/verify_permissions.py builds its fixture with
  zip(PRIVATE_DATA_FILES, (0o664, 0o644, 0o664)) -- a hardcoded
  three-element tuple of modes paired against a registry meant to grow.
  zip stops at the shorter side, so adding a fourth private file creates
  three fixture files while the assertion below still compares against the
  full PRIVATE_DATA_FILES.

  CI runs this script, so the pipeline goes red -- but on an assertion
  about a file the fixture never created, which reads as "the permission
  pass is broken" when the pass is fine and the test is short. That is the
  expensive kind of failure: it points at the wrong subsystem.

  Found by the third lane of the STANDARDS.md review gate, in a script
  written the same morning. It surfaced as a documentation question --
  5.3 said a new sensitive file must be registered in two places, and this
  fixture is a third -- so the doc was corrected to name all three. This
  bullet is the code half, deliberately not fixed inside a documentation
  review.

  The fix is to derive the mode rather than index it: give every fixture
  file the same loose mode, or map name to mode and assert the map covers
  PRIVATE_DATA_FILES. That removes the silent truncation and the third
  registration point with it, which would let 5.3 go back to naming two.
  **Layman:** A safety check quietly stops covering a new private file, and the build then fails in a way that points at the wrong thing.
  Kind: test.
  Source: review-contract-standards-2026-09-02.
  Lanes: testing, security.
