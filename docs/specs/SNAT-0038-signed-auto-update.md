<!-- ants-spec-format: 1 -->
# SNAT-0038 — Update Snatch in place from a signed release

**Status:** spec draft (2026-11-03).
**Kind:** feature.
**Source:** ROADMAP SNAT-0038 (user-request-2026-08-20; key and spec approved by the user 2026-11-03).
**Supersedes:** SNAT-0021's click action, which opens the release page.

*Layman:* when a newer Snatch is out, it shows what changed since your version and, if you say yes, installs it and reopens itself — and it refuses any update not signed by the project's own key.

## 1. Goal

A user of the Linux AppImage or the Windows `snatch.exe` who clicks the
"Snatch X available" button sees the notes for every version since theirs. On
"Update now", Snatch downloads the new build, proves it was signed by the
maintainer's key for exactly that version, replaces itself and reopens. The
queue and settings come through intact. Every other build keeps today's
behaviour: the button opens the release page.

## 2. Problem

1. **Updating is manual.** `VersionMixin._on_app_update_click` in
   `snatch/version.py` asks with `messagebox.askyesno` and, on Yes, calls
   `open_path(SNATCH_RELEASE_PAGE)`. The user downloads, finds and replaces
   the file themselves.
2. **The user sees one version's notes.** `_check_app_update_thread` reads
   only `tag_name` from `SNATCH_RELEASE_API`, which is `/releases/latest`.
   Nothing shows what changed, and a user three versions behind would see only
   the newest release's notes even if it did.
3. **Nothing proves a release came from the maintainer.** The release job in
   `.github/workflows/ci.yml` attaches `SHA256SUMS` (SNAT-0036). That file is
   uploaded beside the artefacts it describes, so whoever can replace an
   artefact can replace it too. An updater that trusts it downloads code from
   the network and runs it as the user — worse than having no updater.

## 3. Scope decisions (agreed with the user)

- **Signed on the maintainer's PC, never in CI** — the user, 2026-11-03. CI
  publishes a draft; a local script signs and publishes it. A GitHub account
  compromise cannot sign an update.
- **Check at every launch, install only on request** — the user, 2026-11-03.
  The existing launch check stays on by default; nothing installs until
  "Update now".
- **Key without a passphrase, kept outside the repository, with a backup on
  another drive** — the user, 2026-11-03. A lost key strands every installed
  copy until its user updates once by hand.
- **Linux AppImage and Windows `.exe` only** — the roadmap item, 2026-08-20.
  The macOS build is unsigned and untested (SNAT-0004, SNAT-0025).
- **Replace the running file directly; no helper script** — not the user.
  Measured on the Windows test box, 2026-11-03, with the published 1.3.1
  `snatch.exe` running (two processes, the one-file loader and its child):
  `Rename-Item` on the running file succeeded, a new file took its name, the
  renamed file could not be deleted while running and was deleted after both
  processes exited. So the old process can install the new one itself. This
  removes finbreak's PowerShell helper, whose launch flag left every Windows
  update broken from finbreak 0.1.10 to 1.0.0 (FIBR-0444).
- **One signed manifest that names the version** — not the user. §4.2.

## 4. Design

### 4.1 Modules

| File | Job |
|------|-----|
| `snatch/update_key.py` (new) | `RELEASE_PUBLIC_KEY_B64`, the raw 32-byte Ed25519 public key in base64; `public_key()` |
| `snatch/self_update.py` (new) | Release discovery, notes, manifest verification, download. Creates no widgets; takes `_open_https` and the shared constants from the modules that hold them now. |
| `snatch/update_installer.py` (new) | `detect_installer()`, `AppImageInstaller`, `WindowsInstaller`, stale-file cleanup |
| `snatch/update_dialog.py` (new) | `UpdateDialog`, a non-modal `tk.Toplevel` |
| `snatch/version.py` | `_open_https` checks every redirect hop; `_on_app_update_click` opens the dialog when an installer exists |
| `snatch/app.py` | `_on_close` split into `_confirm_close()` and `_shutdown_state()`; stale cleanup at start |
| `snatch/selftest.py` | New modules in `MODULES`; a signature check (INV-12) |
| `scripts/gen-signing-key.py` (new) | Makes the key pair once |
| `scripts/sign-release.py` (new) | Signs and publishes a draft release |
| `.github/workflows/ci.yml` | The release job publishes a draft |
| `requirements.txt` | Adds `cryptography`, hash-locked by `scripts/lock-requirements.sh` |

### 4.2 The signed manifest

Each release carries two new assets: `SNATCH-UPDATE` and
`SNATCH-UPDATE.sig`. `SNATCH-UPDATE` is ASCII, LF line endings, ending in a
newline, at most 64 KiB:

```
snatch-update 1
version 1.4.0
<64 lowercase hex>  Snatch-x86_64.AppImage
<64 lowercase hex>  Snatch-arm64.dmg
<64 lowercase hex>  snatch.exe
```

- Line 1 is exactly `snatch-update 1`. A later format changes the number.
- Line 2 is `version ` plus `X.Y.Z` matching `SNATCH_TAG_RE` without its `v`.
- Every further line is `<sha256 hex><two spaces><asset name>`, the
  `sha256sum` shape, with no name repeated.
- Any other line, a missing line or a repeated name rejects the whole file.

`SNATCH-UPDATE.sig` is exactly 64 bytes: the raw Ed25519 signature over the
exact bytes of `SNATCH-UPDATE`.

The version line binds the version: a correctly signed manifest from an older
release names the older version, so it cannot be replayed under a newer tag.
`SHA256SUMS` stays as it is, for people checking a download by hand.

### 4.3 Discovery and the offer

```python
@dataclass(frozen=True)
class UpdateOffer:
    version: str          # "1.4.0"
    asset_name: str       # find_offer's argument; download_verified looks up its digest
    asset_url: str        # browser_download_url of this build's asset
    manifest_url: str
    signature_url: str
    notes: str            # every version since ours, newest first
```

`find_offer(current, asset_name)` reuses the launch check's single fetch of
`SNATCH_RELEASE_API`. GitHub excludes drafts and prereleases from it. It
returns an offer only when the tag is newer than `current` by
`newer_app_version`, and the release lists exactly one asset each named
`asset_name`, `SNATCH-UPDATE` and `SNATCH-UPDATE.sig`. Otherwise it returns
`None` and the button behaves as today.

`asset_name` comes from the installer: `Snatch-{platform.machine()}.AppImage`
on Linux, `snatch.exe` on Windows.

Notes come from one more fetch, `.../releases?per_page=30`, capped at 4 MiB.
It keeps releases that are neither draft nor prerelease and whose tag lies in
(current, offered], newest first. Each becomes `## X.Y.Z` plus its body,
joined with `---` lines. If that fetch fails, the offered release's own body
is used. Notes never block the offer.

### 4.4 Download and verification

`download_verified(offer, target_dir, on_progress, cancelled)`:

1. Fetch `SNATCH-UPDATE.sig` (refuse over 64 bytes) and `SNATCH-UPDATE`
   (refuse over 64 KiB).
2. Verify the signature with `public_key()`. Then parse the manifest (§4.2).
   Require `version` to equal `offer.version` and to be newer than
   `__version__`. Look up `offer.asset_name`'s digest.
3. Only then fetch the asset into `tempfile.mkstemp(prefix=".snatch-update-",
   dir=target_dir)`. Refuse a `Content-Length` over `UPDATE_MAX_BYTES`
   (512 MiB), stop at that many bytes, hash while writing in
   `YTDLP_CHUNK_BYTES` chunks, and report progress at most every
   `DownloaderMixin.PROGRESS_THROTTLE_SEC`. Check `cancelled` between chunks.
4. A body shorter than its `Content-Length` raises `UpdateDownloadError`; a
   digest mismatch raises `UpdateVerificationError`.
5. On any failure or cancel, unlink the temp file in `finally`. Return its
   path only on success.

Every fetch goes through `_open_https` with `UPDATE_CHECK_TIMEOUT_SEC` per
read. `_open_https` gains a redirect handler that refuses any non-HTTPS hop
before following it (FIBR-0167). It builds its own opener rather than
replacing the process-wide one.

### 4.5 Which builds can update

```python
def detect_installer() -> AppImageInstaller | WindowsInstaller | None
```

- **Windows:** `is_windows()` and `is_frozen()` → `WindowsInstaller(Path(sys.executable))`.
- **Linux:** `is_frozen()`, `$APPIMAGE` names an existing file, `$APPDIR` is
  set and `sys.executable` resolves inside `$APPDIR` →
  `AppImageInstaller(Path(os.environ["APPIMAGE"]))`. `$APPIMAGE` alone is not
  trusted: a program started from another AppImage inherits it.
- **Anything else** → `None`: a source run, macOS, a future distro package
  (SNAT-0028).

`detect_installer()` also returns `None` unless a file can be created and
removed in the target's folder, for example a copy in `C:\Program Files`. Do
not use `os.access` for this: on Windows it returned True for a folder whose
access list denied writing (measured 2026-11-03, Windows 10).
`None` means today's behaviour, unchanged.

### 4.6 Installing

Both installers take the verified temp file, which sits in the folder of
`<target>`, the file the installer was built with (§4.5), so every move is a
same-volume rename.

**Before installing**, on the main thread: `_confirm_close()` asks about
running downloads, exactly as closing the window does. If the user says no,
the update stops and the temp file is deleted. Then `_shutdown_state()`
cancels downloads, stops mpv, and saves config and `queue.json`. Nothing
writes user data after this point.

**AppImage:** `chmod 0o755` the temp file, fsync it, then
`os.replace(temp, appimage)`, then fsync the folder. The running copy keeps
its mounted image, so the swap is safe.

**Windows:** rename the running `<target>` to `<target>.old`, removing
an earlier `.old` first and using `<target>.old-<n>` if that one is still
locked. Then `os.replace(temp, target)`, tried five times 500 ms apart in case
antivirus holds the new file. If it still fails, rename the `.old`
file back, delete the temp file and report the error.

**Relaunch**, on both: `subprocess.Popen([str(target)], env=env,
stdin=DEVNULL, stdout=DEVNULL, stderr=DEVNULL, close_fds=True)`. On Linux
add `start_new_session=True`. On Windows add
`creationflags=CREATE_NEW_PROCESS_GROUP`, never `DETACHED_PROCESS`. `env` is
`os.environ` minus `APPIMAGE`, `APPDIR` and `ARGV0`, plus
`PYINSTALLER_RESET_ENVIRONMENT=1`. That flag makes the new bootloader reset
its own `_PYI_*` variables; PyInstaller's advanced-topics page says code
outside the bootloader must not modify them. `restore_child_library_path()` has
already cleaned `LD_LIBRARY_PATH`. There is no shell anywhere. Then
`os._exit(0)`, also when the spawn fails, because the swap is already
committed. A failed spawn is logged; the user starts the new version
themselves.

**Cleanup at start:** `cleanup_stale(installer)` deletes, in the target's own
folder only, `.snatch-update-*` files older than an hour and
`<target>.old*` files. A file still locked stays for next time.

### 4.7 The dialog

The "Snatch X available" button keeps its place and its launch check.
Clicking it with an installer and an offer opens `UpdateDialog`:

- The notes, in a read-only `tk.Text` with a scrollbar, colours from `theme.*`.
- **Later** closes the dialog; the button stays.
- **Skip this version** stores the version in `dismissed_app_version` (the
  existing key) and hides the button, as No does today.
- **Update now** disables Later and Skip, shows a determinate
  `ttk.Progressbar` and a **Cancel** button, and downloads in a daemon
  thread. Results come back via `root.after(0, ...)`.
- Closing the dialog during a download cancels it.
- A failed download says "Couldn't download the update. Try again later." A
  failed verification says "The update could not be verified, so it was not
  installed." Both delete the temp file and leave the button in place.

### 4.8 Releasing

**Key, once:** `scripts/gen-signing-key.py` writes an unencrypted PKCS#8 PEM to
`$SNATCH_SIGNING_KEY`, default `~/.config/snatch-release/signing.key`. It uses
`O_CREAT | O_EXCL` and mode 0600, refuses to overwrite an existing file, and
prints the base64 public key for `snatch/update_key.py`. It also tells the
user to copy the key to a second drive.

**CI:** the `release` job passes `draft: true` to `softprops/action-gh-release`.
A draft is invisible to users and to `/releases/latest`.

**Each release:** `scripts/sign-release.py vX.Y.Z`:

1. Read the key. If it is missing, stop and say to restore it from the
   backup; never suggest making a new one.
2. Download the draft's assets with `gh release download` into a fresh
   `mkdtemp`.
3. Check every asset against `SHA256SUMS` and check that `SHA256SUMS` lists
   exactly the three platform assets.
4. Write `SNATCH-UPDATE` from those lines plus the version from the tag.
5. Sign it, then verify the signature with the committed
   `RELEASE_PUBLIC_KEY_B64`. Stop if that fails.
6. Upload both files, then publish with `gh release edit --draft=false`.
7. Download both files from the published release and verify them again.

`docs/building.md` § Releasing documents the two steps.

## 5. Invariants

- **INV-1** — An offer exists only for a release that is newer, is not a
  draft or prerelease, and carries this build's asset, `SNATCH-UPDATE` and
  `SNATCH-UPDATE.sig`; otherwise the button opens the release page as today.
  *Test:* `tests/test_self_update.py::test_offer_*`, one fixture per missing
  piece.
  *Breaks when:* a release without `SNATCH-UPDATE.sig`, or without an asset
  named `asset_name`, yields an offer.

- **INV-2** — Nothing is written to disk for the asset until the manifest's
  signature verifies against `RELEASE_PUBLIC_KEY_B64`.
  *Test:* `tests/test_self_update.py::test_bad_signature_downloads_nothing`
  signs the manifest with a freshly made key and asserts the asset URL was
  never opened.
  *Breaks when:* the asset is fetched before, or in parallel with, the
  signature check.

- **INV-3** — The manifest's `version` must equal the offered version and be
  newer than `__version__`.
  *Test:* `tests/test_self_update.py::test_replayed_manifest_is_refused`
  offers tag `v9.0.0` with a manifest validly signed for `1.0.0`, under the
  test key.
  *Breaks when:* the version line is parsed but not compared.

- **INV-4** — The installed bytes hash to the manifest's digest for this
  build's asset name.
  *Test:* `tests/test_self_update.py::test_digest_mismatch_is_refused` and
  `::test_other_platforms_digest_is_refused`.
  *Breaks when:* the downloaded `snatch.exe` is checked against the AppImage
  line, or the download is not hashed at all.

- **INV-5** — A manifest with an unknown line, a missing line, a repeated
  asset name, CRLF endings or more than 64 KiB is rejected whole.
  *Test:* `tests/test_self_update.py::test_manifest_parse_*`, one case per
  shape.
  *Breaks when:* the parser skips lines it does not recognise.

- **INV-6** — Every network read for the update refuses a non-HTTPS URL and a
  non-HTTPS redirect hop, even one that ends on HTTPS.
  *Test:* `tests/test_https_only.py::test_a_redirect_hop_off_https_is_refused`
  serves https → http → https and expects `ValueError`.
  *Breaks when:* only the final URL is checked, which is today's behaviour.

- **INV-7** — Any failed or cancelled download leaves no `.snatch-update-*`
  file behind and leaves the running file untouched.
  *Test:* `tests/test_self_update.py::test_failure_leaves_no_temp_*`
  (truncated body, digest mismatch, cancel, over-size `Content-Length`).
  *Breaks when:* the temp file is unlinked only on the success path.

- **INV-8** — `detect_installer()` returns `None` for a source run, macOS, an
  unwritable target, and a frozen Linux process whose `sys.executable` is not
  inside `$APPDIR` even though `$APPIMAGE` is set.
  *Test:* `tests/test_update_installer.py::test_detect_*`.
  *Breaks when:* `$APPIMAGE` alone arms the updater.

- **INV-9** — A Windows install whose final replace fails renames
  `<target>.old` back to `<target>`, so the user keeps a working copy.
  *Test:* `tests/test_update_installer.py::test_windows_failed_replace_restores_the_original`,
  with `os.replace` patched to raise.
  *Breaks when:* the rename-back step is missing or runs only on success.

- **INV-10** — Config and `queue.json` are written before the new process is
  spawned, and nothing writes them after.
  *Test:* `tests/test_update_installer.py::test_state_saved_before_spawn`
  records the order of `_save_config`, `_save_queue` and `Popen`.
  *Breaks when:* the spawn happens first, or `_on_close`'s teardown runs again
  after it.

- **INV-11** — The relaunch uses an argument list and no shell, never passes
  `DETACHED_PROCESS`, strips `APPIMAGE`, `APPDIR` and `ARGV0` from the
  child's environment, and sets `PYINSTALLER_RESET_ENVIRONMENT=1`.
  *Test:* `tests/test_update_installer.py::test_relaunch_*` captures the
  `Popen` call.
  *Breaks when:* a shell string, `shell=True` or `DETACHED_PROCESS` appears,
  the child inherits `APPDIR`, or the reset flag is missing.

- **INV-12** — A packaged build can verify an Ed25519 signature.
  *Test:* `snatch --selftest` verifies `SELFTEST_MANIFEST` against
  `SELFTEST_SIGNATURE`, two constants in `snatch/selftest.py` signed once by
  the maintainer's real key, with the bundled `cryptography`. Every
  `scripts/build-*.sh` already runs `--selftest` on its artefact. The
  constants live in the package because a packaged build does not contain
  `tests/`.
  *Breaks when:* PyInstaller leaves out `cryptography`'s native module.

- **INV-13** — The committed public key verifies the self-test constants,
  so a changed key fails the tests.
  *Test:* `tests/test_update_key.py::test_committed_key_verifies_the_fixture`
  verifies `SELFTEST_MANIFEST` and `SELFTEST_SIGNATURE` from source.
  *Breaks when:* `RELEASE_PUBLIC_KEY_B64` changes without a deliberate
  rotation (§6).

- **INV-14** — No private key is tracked, and `sign-release.py` never
  publishes a manifest its own committed public key cannot verify.
  *Test:* `tests/test_release_signing.py::test_no_private_key_is_tracked`
  scans every file `git ls-files` lists for a PEM private-key header
  (`-----BEGIN`, any words, `PRIVATE KEY-----`), building the pattern at run
  time so the test's own source does not match;
  `::test_sign_refuses_a_key_that_does_not_match` runs `sign-release.py` with
  a foreign key and `gh` replaced by a recorder, and expects no
  `gh release upload` or `gh release edit` call.
  *Breaks when:* the verify-before-publish step is removed.

## 6. Failure modes

- **Offline or rate-limited** — the launch check is silent, as now
  (`_check_app_update_thread`). The notes fetch fails into the single-body
  fallback.
- **A release published without signing** (a draft published by hand) —
  `find_offer` returns `None`; the button opens the release page.
- **The key is lost** — no further release can be signed. Installed copies
  still offer the release page, because an unsigned release makes no offer.
  The user restores the backup. A new key is a rotation: every installed copy
  must be updated once by hand.
- **Key rotation** — deliberately unsupported by this spec. INV-13 turns red
  when the key changes.
- **Disk fills during download** — the write raises; INV-7 cleans up.
- **The new process fails to start** — the old one still exits (§4.6); the
  new file is in place, and the next manual launch runs it.
- **Power cut mid-install** — AppImage: `os.replace` is atomic, so either file
  is whole. Windows: between the rename and the replace there is no
  `<target>`; `<target>.old` is the old build and the user can rename it
  back.
- **A broken installer ships** — it is the old version that installs the new
  one, so a bug in this code can only be fixed by a manual download
  (FIBR-0444). §7's live recipe runs before a release relies on it.
- **Antivirus holds the new file briefly** — §4.6's retries, then INV-9's
  rename-back.

## 7. Tests

- `tests/test_self_update.py` (new) — INV-1, INV-2, INV-3, INV-4, INV-5, INV-7.
- `tests/test_https_only.py` (new case) — INV-6.
- `tests/test_update_installer.py` (new) — INV-8, INV-9, INV-10, INV-11.
- `snatch --selftest`, run by every `scripts/build-*.sh` — INV-12.
- `tests/test_update_key.py` (new) — INV-13.
- `tests/test_release_signing.py` (new) — INV-14.

The new files follow `tests/test_app_update_notice.py`'s
pattern: a host class over the mixin, a `MagicMock` root whose `after` calls
straight through, and `_open_https` patched. Network fixtures are signed with
a key generated in the test. Each test is first seen failing against the code
before its fix.

Both existing tests in `tests/test_https_only.py` find or patch `urlopen`,
which `_open_https`'s own opener does not call. Rewrite both around the
opener, keeping what each proves.

**Live recipe, before the first release that relies on updating:**

1. Release the version carrying this feature, signed, as usual.
2. Release a patch version straight after.
3. On this machine, run the earlier AppImage and update it through the
   dialog. Confirm the window title shows the new version and the queue
   survived.
4. On the Windows test box (`scripts/wplay.ps1`'s folder pattern), run the
   earlier `snatch.exe` from Explorer via the signed-in desktop, update it,
   and confirm the same. Confirm `snatch.exe.old` is gone after the next
   start.

## 8. Alternatives considered (and rejected)

- **Sign in CI with a secret** — the user rejected it (§3): anyone with
  GitHub access could sign.
- **Sign `SHA256SUMS` itself** — it carries no version. A version line makes
  the README's `sha256sum -c --ignore-missing SHA256SUMS` print "WARNING: 1
  line is improperly formatted" (measured 2026-11-03), which reads as a failed
  check to the person running it.
- **finbreak's per-file `.sig` plus signed sums** — two signatures prove
  nothing one signed manifest does not.
- **PowerShell helper on Windows** — renaming the running file was measured
  to work (§3), and the helper is the part that failed finbreak (FIBR-0444).
- **Verify from an in-memory copy (FIBR-0170)** — would hold a 150 MB build in
  memory. A process able to change a file in the user's own Snatch folder
  can replace `snatch.exe` directly, so re-reading the verified file defends
  nothing.
- **A pure-Python Ed25519 verifier** — hand-written cryptography. The
  `cryptography` package is maintained and audited.
- **GitHub build attestations** — need the `gh` tool or network checks on
  the user's machine, and trust GitHub's identity rather than the
  maintainer's key.
- **Opt-in updates, as finbreak does** — the user chose the existing launch
  check (§3).

## 9. Out of scope

- macOS self-update — deferred; not yet queued. Needs SNAT-0025 first.
- Key rotation with two trusted keys — deferred; not yet queued.
- Automatic background install without asking — not wanted (§3).
- Distro packages — SNAT-0028; there the package manager updates Snatch.

## 10. What checks this

| Rule | What catches a breach |
|------|----------------------|
| INV-1 | `tests/test_self_update.py::test_offer_*` |
| INV-2 | `tests/test_self_update.py::test_bad_signature_downloads_nothing` |
| INV-3 | `tests/test_self_update.py::test_replayed_manifest_is_refused` |
| INV-4 | `tests/test_self_update.py::test_digest_mismatch_is_refused` |
| INV-5 | `tests/test_self_update.py::test_manifest_parse_*` |
| INV-6 | `tests/test_https_only.py::test_a_redirect_hop_off_https_is_refused` |
| INV-7 | `tests/test_self_update.py::test_failure_leaves_no_temp_*` |
| INV-8 | `tests/test_update_installer.py::test_detect_*` |
| INV-9 | `tests/test_update_installer.py::test_windows_failed_replace_restores_the_original` — Partial: runs on Linux with `os.replace` patched; real Windows locking only by §7's live recipe |
| INV-10 | `tests/test_update_installer.py::test_state_saved_before_spawn` |
| INV-11 | `tests/test_update_installer.py::test_relaunch_*` — Partial: checks the call, not that Windows starts the process; §7's live recipe does |
| INV-12 | `snatch --selftest`, run by every `scripts/build-*.sh` |
| INV-13 | `tests/test_update_key.py::test_committed_key_verifies_the_fixture` |
| INV-14 | `tests/test_release_signing.py` |
| §4.8 key backup | **nothing** — the user's own step |
| §7 live recipe | **nothing** automatic — a person runs it once |

## 11. Cross-doc impact

- `docs/building.md` § Releasing — the draft-then-sign steps and the key's location.
- `STANDARDS.md` — the update modules in the architecture map; the new
  constants; `dismissed_app_version`'s row now covers Skip this version.
- `CLAUDE.md` Quick Reference — the signing key's location and `sign-release.py`.
- `README.md` — Snatch updates itself on Linux and Windows.
- `CHANGELOG.md` — the feature entry.
- `ROADMAP.md` — SNAT-0038's body names this spec.

## 12. Cold-eyes loop log

Rows live in `../reviews/SNAT-0038-signed-auto-update-loop-log.md`.

## 13. Resource cost

- **New dependency:** `cryptography`, bundled into all three builds. Its size
  in each build is measured when it is added. It needs no system library:
  its wheels carry their own OpenSSL.
- **Disk:** one temp file the size of the asset, in the target's folder,
  during the download. On Windows, a `.old` copy until the next start.
- **Memory:** one chunk at a time; notes text up to 4 MiB.
- **Network:** one extra GitHub API call when an offer is found, and none
  otherwise.
