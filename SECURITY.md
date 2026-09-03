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
scale, and no document here does — reviews use CRITICAL/HIGH/MEDIUM informally
and the reviewing tool supplies the ranking. What this file removes is the
step before that, which the 2026-08-31 review had to guess at and said so.

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

**The content Snatch is asked to handle.** Snatch itself does not parse the
page or the media file — yt-dlp does. What Snatch handles is the URL the user
pasted, the JSON and progress output yt-dlp returns, and the paths it is told
to write to. None of those may become command execution, an unbounded read, or
a write outside the download folder. The defences are URL validation, a `--`
separator before any URL or path argument, never using a shell, and bounding
what is read into memory.

Where this meets the yt-dlp bullet under § Out of scope: a page that exploits
yt-dlp's own extraction is upstream's. The same page reaching Snatch's argument
construction, its output parsing or its destination paths is ours.

### Real but secondary

**Another person logged into the same computer.** Snatch is built for a
single-user desktop, so this is not the case it is designed around — but the
cheap defences are taken anyway: user data files are owner-only, the player's
control socket lives in a private directory, and symlinks are resolved before
a path is opened. A finding that requires a hostile local user on a shared
machine is graded below one that does not; it is not dismissed.

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
- **Flaws inside yt-dlp's own parsing and extraction.** Snatch bundles it and
  updates the pin; those are reported upstream. How Snatch *invokes* it and
  consumes its output is not covered by this bullet — see the boundary note
  above. If an upstream flaw changes what Snatch should do, say so and it will
  be treated as in scope.

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
- `docs/decisions/ADR-0001-supply-chain-pinning.md` — why every fetched binary
  is pinned and checksummed, and which gaps are known.
