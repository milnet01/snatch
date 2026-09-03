# Security

*Review history: `docs/security-md-review-log.md`.*

## Reporting a vulnerability

Use GitHub's **Report a vulnerability** button on the
[Security tab](https://github.com/milnet01/snatch/security). It opens a private
advisory only the maintainer can see.

Please do not open a public issue for a security problem. Snatch distributes
executables for Windows, macOS and Linux that carry no publisher identity — the
Windows and Linux builds are unsigned, and the macOS bundle is ad-hoc signed so
that it will launch on Apple Silicon, which is neither notarisation nor a
statement of who built it. A public report therefore discloses the problem to
everyone before there is anything to upgrade to.

There is no service to take offline and no user data held anywhere but on your
own machine, so expect a fix to arrive as a new release rather than as an
immediate mitigation.

## Supported versions

The most recent release only. Snatch has one maintainer and no long-term
support branches; a fix ships in the next release and older downloads are not
patched.

## Threat model

This model settles **scope**: whether a finding is something Snatch defends
against, and roughly how much weight it carries. It does not define a severity
scale, and no document here does — reviews use CRITICAL/HIGH/MEDIUM
informally and nothing defines them. What this file settles is the step before
that, which the 2026-08-31 review had to guess at and said so.

**What Snatch is.** A desktop program with a window, run by the person who
installed it, under their own account, on their own machine. It is not a
service, it has no server, it listens on no network port, and it has no notion
of users or accounts.

### Adversaries this project defends against

**The things Snatch downloads from.** yt-dlp nightly releases, the GitHub API,
thumbnail servers, the AppImage runtime, and every helper binary the build
fetches. These are the real attack surface: they are outside anyone's control
here and they reach every user. The defences are pinning and checksums,
HTTPS-only fetches, and verifying the in-app yt-dlp update against the
publisher's own manifest. `docs/decisions/ADR-0001-supply-chain-pinning.md`
holds both the policy and the gaps in it, which are enumerated there rather
than implied away here.

**A vulnerable or compromised package Snatch ships.** Pillow and tkinterdnd2
are bundled into every release and run inside the app's process, and Pillow is
what decodes remote image bytes. Which half of that is ours is settled in the
bundled-dependency bullet under § Out of scope and not repeated here. Nothing
currently watches for such an advisory: SNAT-0037 is that gap, open because a
real one was missed once already.

**The content Snatch is asked to handle.** yt-dlp parses the page and the
media file; Snatch handles the URL the user pasted, the JSON and progress
output yt-dlp returns, the paths it is told to write to — and it decodes
thumbnail images in its own process, through Pillow, from a URL that arrived
in that JSON — the shortest path there is from a remote server into this app's
memory. None of these may become command execution, an unbounded read, or a
write outside the download folder. The defences are URL validation, a `--`
separator before any URL or path argument, never using a shell, and bounding
what is read into memory.

Two of those inputs are handed to a bundled dependency — yt-dlp parses the
page, Pillow decodes the image — and the line between their bugs and ours is
drawn once, in the bundled-dependency bullet under § Out of scope. It is not
restated here, so the two cannot drift apart.

### Real but secondary

**Another person logged into the same computer.** Snatch is built for a
single-user desktop, so this is not the case it is designed around — but the
cheap defences are taken anyway: user data files are written owner-only, the
player's control socket lives in a directory of its own, and symlinks are
resolved before a path is opened.

**On Windows those defences are weaker, and two are absent.** POSIX mode bits
are not the access-control mechanism there, so neither the 0o600 write nor the
startup pass that repairs an already-loose file does anything
(`STANDARDS.md` § 5.3 and § 14). And the player is not covered by the socket
defence either: Snatch never connects to mpv's IPC on Windows, but it still
launches mpv with `--input-ipc-server`, which there is a named pipe rather
than a file. That endpoint exists and this project has not assessed who can
reach it — say so if you know.

A finding that requires a hostile local user on a shared machine is graded
below one that does not; it is not dismissed.

### Out of scope

- **An attacker who already runs code as you.** They can read the same files
  Snatch can. Nothing here defends against that, and nothing can.
- **What the sites Snatch downloads from allow.** Whether a given download is
  permitted is between the user and that site.
- **Physical access to an unlocked machine.**
- **The integrity of the download you already have.** The builds carry no
  publisher identity, so nothing in the file proves it came from here. That is
  a stated limitation rather than an open finding — a report that releases are
  unsigned is accurate and will be closed as known. What is in scope is a way
  to *check* a download that this project has and does not offer; the release
  checksums SNAT-0036 asks for are that gap.
- **Defects inside a bundled dependency's own code** — a parser bug in
  yt-dlp, a decoder bug in Pillow. Those are upstream's to fix, for every
  bundled component and not yt-dlp alone. **This is the whole boundary; no
  other section restates it.**

  Three things stay ours, and none of them is a defect in someone else's code:

  - **How Snatch reaches that code.** Which URL is fetched, over what
    transport, how many bytes are read in, which path is written to. A crafted
    page reaching Snatch's argument construction, its output parsing or its
    destination paths is in scope.
  - **Which version we ship.** A dependency with a published advisory is ours
    to move off, whoever wrote the bug. SNAT-0030 is the precedent and it was
    closed exactly that way — by moving the Pillow pin, not by changing how
    Snatch handles content.
  - **Telling you.** A report about an unpatched defect on a path Snatch
    reaches is worth sending even though the fix is upstream's: it decides
    whether we ship, pin back, or disable the feature meanwhile.

### If you think this model is wrong

Say so in a report. A finding that only matters under a different model is
still worth sending — the answer may be that the model needs changing, which is
more valuable than the individual finding.

## Where the rules live

This file says who the adversary is. What follows from that is written
elsewhere, and is not repeated here:

- `STANDARDS.md` § 5.1 to § 5.5 — the rules code must follow: URL validation,
  subprocess safety, file permissions, player socket, path validation. The
  HTTPS-only rule is a bullet inside § 5.2, not a subsection of its own.
- `STANDARDS.md` § 6.3 — bounding what is read into memory. The recv-buffer
  cap is there, not in § 5, and this file names it as a defence.
- `docs/decisions/ADR-0001-supply-chain-pinning.md` — why every fetched binary
  is pinned and checksummed, and which gaps are known.
