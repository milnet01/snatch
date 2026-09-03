# ADR-0001: Pin and checksum everything the build fetches

- **Status:** Accepted
- **Date:** 2026-09-03
- **Roadmap:** SNAT-0057 (this record), SNAT-0035 (the one open exception)

## Context

Snatch ships helper programs it did not write. A release bundles yt-dlp,
ffmpeg, ffprobe, a QuickJS runtime and — on Windows — mpv. The Linux build
additionally fetches `appimagetool`, which runs on the build host, and the
AppImage type2 runtime, which becomes the first bytes of the file every Linux
user executes.

Every one of those is downloaded from a third-party GitHub release at build
time. Whoever controls those repositories can change what a given tag points
at. If the build follows a rolling tag, they can change what Snatch ships, and
what the build machine executes, without a commit in this repository and
without anyone here noticing.

Two things made that concrete rather than theoretical:

- The AppImage runtime was fetched from the `continuous` tag, and the cache
  test was `[ ! -s "$runtime" ]` — non-emptiness. Once any file landed it was
  trusted forever, whatever it was.
- Resolving the mpv asset through `api.github.com` returned HTTP 403 under the
  unauthenticated rate limit, so a build failed on a JSON parse for reasons
  that had nothing to do with the build (SNAT-0064).

The project has no reproducible-build machinery and no signing. Pinning plus a
checksum is the whole of the defence.

## Decision

**Every artifact the build downloads is pinned to an immutable identifier and
verified against a recorded SHA-256 before it is used.**

Three rules follow from that, and they are the part worth remembering:

1. **A digest mismatch is a hard failure.** It is never skipped, never warned
   past, and the check is never removed to make a build go green. The scripts
   say so at the point of failure: *"add it to `digest_for()` above rather than
   removing the check"*.
2. **A pin moves only by a deliberate commit.** Change the version, run the
   build, and replace the digest with the one the mismatch message prints.
   Both halves move in the same commit, because a version without its matching
   digest is a build that cannot succeed.
3. **Nothing is resolved at build time that can be written down instead.** The
   mpv asset name is a literal in `scripts/fetch-binaries.sh`, not the result
   of an API query, because a query is a runtime dependency on a service that
   can rate-limit, change shape, or lie.

`docs/building.md` holds the mechanics — which file each pin lives in, and the
step-by-step for bumping the bundled yt-dlp before a release. This record holds
only why the policy exists.

### The pins a future reader will want to "fix", and why not to

These four look wrong at a glance. Each is deliberate.

- **`TYPE2_RUNTIME_VERSION` is a dated tag older than `continuous`.** That is
  the point. `continuous` is mutable; the dated tag is the only immutable
  identifier that repository offers. An older immutable pin is worth more here
  than a newer moving one.
- **`APPIMAGETOOL_VERSION` is a fixed release, and a system `appimagetool` on
  the build host is deliberately not preferred over it.** Whatever is installed
  on a given machine is not a thing this repository controls.
- **`MPV_WIN_TAG`, `MPV_WIN_ASSET` and the asset's digest move together.** The
  asset filename carries a build hash, so bumping the tag alone names a file
  that does not exist, and bumping tag and name without the digest fails the
  check. Treat the three as one value.
- **`softprops/action-gh-release` is pinned to a commit SHA, not a tag.** It is
  the action that publishes the release, so it is the one with the most to gain
  from being changed underneath us. Read the SHA as a pin, not as something
  behind and due a bump.

### The exception

The `actions/*` steps in `.github/workflows/ci.yml` are pinned to major-version
tags rather than commit SHAs. `zizmor` reports each as `unpinned-uses`, and the
reports are correct.

This is a known gap, tracked as SNAT-0035, and left open rather than closed
quietly. **It is a sequencing decision, not a judgement that the risk is
acceptable.** SNAT-0035 states the position: a tag is a pointer its owner can
move, and that code runs in a job holding a token that can write to this
repository. What has kept it open is that pinning these commits the project to
a SHA-update routine, and the same bullet already proposes running `pinact` and
adding `zizmor` to the static-checks job — which should land together rather
than piecemeal, so that the pins cannot silently regress once made.

Third-party actions are pinned ahead of first-party ones.
`softprops/action-gh-release` was pinned first for that reason: it is the only
non-GitHub action here, and it runs in the one job that holds
`contents: write`. Its SHA is the commit `v2` pointed at when it was pinned —
a pin, not a bump. A newer major version exists, and whether to move to it is a
dependency question rather than a pinning one.

## Consequences

- A release build downloads its dependencies fresh rather than reusing a cache
  a pull-request run could have written (SNAT-0047). Pinning decides *what* is
  fetched; that decides *from where*.
- Bumping a bundled tool is a two-step edit — version, then digest — and cannot
  be done from a version number alone. This is the intended friction.
- A pinned tool goes stale silently. Nothing in this repository watches for a
  newer yt-dlp, so `docs/building.md` makes bumping it a step in the release
  procedure rather than something that happens on its own.
- A future security review will re-derive the `unpinned-uses` findings above.
  They are expected. SNAT-0035 is where that conversation belongs.

## Alternatives considered

- **Follow the upstream rolling tags.** Cheapest to maintain, and it is what
  the project did until the checks landed. Rejected: it makes what Snatch ships
  a function of someone else's repository state at build time.
- **Vendor the binaries into this repository.** Immutable by construction, but
  it puts tens of megabytes of third-party executables into git history where
  they cannot be removed, and updating one rewrites the repository's size
  forever.
- **Verify signatures rather than digests.** Stronger, and the right answer if
  every upstream signed its releases. They do not, so it would apply to some
  artifacts and not others — and a rule that covers only part of the surface is
  worse than a uniform weaker one, because nobody can tell from the outside
  which artifacts are covered.
