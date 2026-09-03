# ADR-0001: Pin and checksum the binaries the build fetches

- **Status:** Accepted
- **Date:** 2026-09-03
- **Roadmap:** SNAT-0057 (this record).
  Open items this record names: SNAT-0035, SNAT-0065, SNAT-0066, SNAT-0067
- **Review history:** `docs/adr-0001-review-log.md`

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

**Every binary the build scripts fetch is pinned to a fixed identifier and
verified against a recorded SHA-256 before it is used.**

Deliberately narrower than "everything the build downloads": CI also installs
Python tooling from PyPI, pinned by version and not by hash. The scope of this
decision is what `scripts/fetch-binaries.sh` and `scripts/build-linux.sh`
fetch; § Known exceptions has the rest.

The rules that follow are the part worth remembering:

1. **A failed or absent digest is a hard failure.** Never skipped, never
   warned past, and the check is never removed to make a build go green. There
   are two stops, and they print differently: a *mismatch* prints the expected
   and computed hashes, while an asset with no recorded digest at all prints
   *"add it to `digest_for()` above rather than removing the check"*. Where a
   path does reach a tool without comparing a digest, § Known exceptions names
   it.
2. **A pin moves only by a deliberate commit**, version and digest together.
   Where to get the digest depends on the pin. If the asset's *filename* is
   unchanged the build reaches a mismatch and prints the computed hash. If the
   filename also changes — mpv, or a new platform — `digest_for` has no entry,
   so the stop is the missing-digest one and prints no hash to copy; there the
   digest comes from upstream's published `.digest` field, via the `gh api`
   query in `docs/building.md`. Prefer that query in either case: it records
   what upstream vouches for rather than what this machine happened to
   receive.
3. **Nothing is resolved at build time that can be written down instead.** The
   mpv asset name is a literal in `scripts/fetch-binaries.sh`, not the result
   of an API query, because a query is a runtime dependency on a service that
   can rate-limit, change shape, or lie.

`docs/building.md` holds the mechanics — which file each pin lives in, and the
step-by-step for bumping the bundled yt-dlp before a release. This record holds
only why the policy exists.

### The pins a future reader will want to "fix", and why not to

These look wrong at a glance. Each is deliberate.

- **`TYPE2_RUNTIME_VERSION` is a dated tag older than `continuous`.** That is
  the point. `continuous` is rewritten on every upstream build, where a dated
  release tag is not expected to move — and a tag is not immutable either way,
  which is why the runtime also carries a recorded digest. The digest is what
  makes the pin binding; the dated tag is what makes it stable enough to be
  worth recording. An older stable pin beats a newer moving one.
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

### Known exceptions

Each is recorded here rather than quietly tolerated.

**1. `actions/*` steps are pinned to major-version tags, not commit SHAs.**
Run by hand, `zizmor` reports each as `unpinned-uses`, and the reports are
correct. It is not wired into any job or into the local gate, so nothing
reports this on its own today.

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

**2. Python tooling from PyPI is pinned by version, not by hash.** CI installs
`ruff`, `pytest` and `pyinstaller` at exact versions and `requirements.txt` by
version, with no `--require-hashes` — and each build job additionally runs
`pip install --upgrade pip`, which is pinned by nothing at all. So a version
pin here is a weaker control than a recorded digest, and the Decision above is
scoped to exclude it rather than quietly claiming it. Closing this means a
hash-pinned lock file and a routine for regenerating it, and it has to cover
the `pip` self-upgrade too. Tracked as SNAT-0066.

**3. `SNATCH_APPIMAGETOOL` reaches `chmod +x` with no digest compared.** Setting
it substitutes a caller's own `appimagetool` for the pinned download. That is
deliberate — it is the supported way to build with a specific packer — and it is
not a hole in rule 1 so much as an opt-out from it. Two things keep it honest:
it is off unless explicitly set, and `scripts/build-linux.sh` announces itself
in the build log, printing `(unverified, caller's choice)`. CI never sets it.
Do not add a digest check to that branch; it would defeat the purpose. Do not
delete the branch either.

**4. The mpv cache is keyed on the tag, not on content.** Every other asset's
reuse path is `cached_ok "$dest" "$want"`, a SHA-256 comparison whose comment
says why: "a tampered or truncated cached file is re-fetched rather than
trusted because a stamp file happens to agree". mpv's is
`stamp_matches "$BIN_DIR/mpv/mpv.exe" "mpv:${MPV_WIN_TAG}"`, so a cached
`mpv.exe` whose stamp matches is used with no digest compared. A fresh fetch is
still verified; it is the reuse that is not. Unlike the exception above this
looks like an inconsistency rather than a decision, and is filed as SNAT-0065
rather than defended. Until it closes, do not copy the stamp pattern for a
new binary.

## Consequences

- Pinned artifacts are reused from local caches, keyed on content so a
  tampered or truncated file is re-fetched rather than trusted. There are two
  locations, not one: `bin/` for what `fetch-binaries.sh` downloads, and
  `.cache/runtime-*` plus the repo-root `appimagetool` for what
  `build-linux.sh` does. Anything that cleans, ignores or audits these caches
  has to cover both. mpv is the exception, keyed on the tag rather than
  content — known exception 4. The cache SNAT-0047 dealt with is a different
  thing again, GitHub's pip cache, outside this decision's scope and no longer
  restored on a tag build.
- Bumping a bundled tool is a two-step edit — version, then digest — and cannot
  be done from a version number alone. For mpv it is three: tag, asset name and
  digest, per the bullet above. This is the intended friction.
- A pinned tool goes stale silently, and nothing here runs on a schedule to
  notice. `scripts/update-ytdlp-pin.sh` re-resolves the yt-dlp pin on demand and
  has a `--check` mode that exits non-zero when the pin is behind; running it is
  a release step in `docs/building.md`, not something that happens on its own.
  Reach for that script rather than writing a second resolver.
- **That script moves the version half only.** It rewrites `YTDLP_VERSION` and
  the version named in `docs/building.md`, and does not touch `digest_for()`,
  which holds a digest per yt-dlp asset. So a bump is the script plus a digest
  refresh in the same commit, and rule 2 is discharged by the pair.
- **Running the script alone fails safely on a clean checkout and silently on a
  warm one.** `digest_for` is keyed on the asset filename and the destination
  is version-independent, so with a populated `bin/` the previous binary still
  matches the still-unchanged digest: `cached_ok` succeeds, nothing is fetched,
  and the build goes green having bundled the old nightly. A clean checkout —
  which is what CI runs — has nothing cached, downloads the new version and
  hard-stops on the compare. So CI catches a version-only bump and a local
  rebuild does not. Tracked as SNAT-0067.
- A future security review will derive the `unpinned-uses` findings above.
  They are expected. SNAT-0035 is where that conversation belongs.
- **This policy governs the build, not the running app, and the difference is
  deliberate.** A build-time fetch is for a version chosen here, so a digest can
  be recorded here. The in-app yt-dlp self-update is for a version chosen at run
  time, where no digest could have been written down in advance, so it verifies
  against the `SHA2-256SUMS` manifest the same release publishes
  (`snatch/version.py`). A new runtime download follows that second model.
  Conforming it to this ADR's recorded-digest rule is not possible and not
  wanted.

## Alternatives considered

- **Follow the upstream rolling tags.** Cheapest to maintain, and it is what
  the project did until the checks landed. Rejected: it makes what Snatch ships
  a function of someone else's repository state at build time.
- **Vendor the binaries into this repository.** Immutable by construction, but
  it puts tens of megabytes of third-party executables into git history where
  they cannot be removed, and updating one rewrites the repository's size
  forever.
- **Verify signatures rather than digests.** Stronger, and the right answer if
  every upstream signed its releases. They do not, so it would cover some
  artifacts and not others, with nothing saying which — and an unmapped gap is
  worse than a uniform weaker control, because no reader can tell what is
  protected. Not an argument against partial coverage as such — this decision
  has gaps of its own — but for the gaps being enumerable, which
  § Known exceptions is.
