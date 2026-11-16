<!-- ants-spec-format: 1 -->
# SNAT-0028 — Package Snatch for openSUSE Tumbleweed on OBS

**Status:** accepted (2026-11-16).
**Kind:** package.
**Source:** ROADMAP SNAT-0028 (user-request-2026-08-20; decisions by the user 2026-11-16).
**Pairs with:** SNAT-0038 (its "every other build" sentence gains a package case, §11).

*Layman:* Tumbleweed users can install Snatch with zypper or Discover, keep their settings in their home folder, and get a yt-dlp new enough for YouTube with one click.

## 1. Goal

A Tumbleweed user adds the `home:milnet:snatch` repository and installs the
`snatch` package. It starts from the menu, saves settings, history, queue and
log under `$XDG_DATA_HOME/snatch`, and on first launch asks once whether to
download the current yt-dlp. Yes gives YouTube playback; No leaves the
distro's yt-dlp in use. Revert goes back to the distro copy. The package
contains Snatch's own code only: Python, Tk, ffmpeg, yt-dlp and a JavaScript
runtime come from Tumbleweed. Zypper updates it; Snatch does not offer its
own updates. Running from source and the AppImage behave as today.

## 2. Problem

Checked 2026-11-16 by running a read-only copy (recorded on SNAT-0028):

1. **Saves fail.** `platform_utils.app_data_dir()` returns the project root
   when `is_frozen()` is false. A distro install is not frozen, so the root is
   the read-only install directory. Writes of `config.json`, `history.json`,
   `queue.json` and `snatch.log` raise `PermissionError`.
2. **The yt-dlp fetch fails.** `platform_utils.user_bin_dir()` sits inside
   `app_data_dir()`, so it cannot be created. `find_ytdlp()` falls back to
   `shutil.which("yt-dlp")`, the distro copy. SNAT-0014 found that the stable
   channel the distro ships does not play YouTube.
3. **The yt-dlp dialogs name the wrong fallback.** In `snatch/version.py`,
   `VersionMixin._prompt_update`, `_prompt_revert` and the status line after a
   revert speak of "the copy that came with Snatch", and
   `_refresh_idle_button` labels the button "Revert to bundled yt-dlp". A
   package ships no copy; the fallback is the system's.
4. **Snatch would offer its own updates.** `VersionMixin.check_app_update`
   runs at every start. With `detect_installer()` returning `None` for a
   non-frozen run, the button opens the GitHub release page. A package is
   updated by zypper. SNAT-0038 §9 already says so.
5. **QuickJS on the system is not found.** `DownloaderMixin._ensure_runtime_cache`
   looks on `PATH` for an executable named `quickjs`. Tumbleweed's `quickjs`
   package provides `/usr/bin/qjs` (`zypper se --provides --match-exact
   /usr/bin/qjs` → `quickjs`), and yt-dlp's `utils/_jsruntime.py` looks for
   `qjs`. So a package relying on QuickJS gets no runtime.
6. **The window icon is looked up in the data folder.** `SnatchApp._set_icon`
   joins `self.script_dir` (that is, `app_data_dir()`) with `icon.png`. Once
   the data folder is in `$HOME`, the icon is not there.
7. **There is no package recipe.** The repository has no RPM spec, OBS
   service file, installed launcher, installed desktop entry or AppStream
   file. `Snatch.desktop` points at absolute paths on the developer's machine.

## 3. Scope decisions (agreed with the user)

- **Tumbleweed first** — the user, 2026-11-16. Other distributions are §9.
- **The package relies on Snatch fetching its own current yt-dlp, not the
  distro's** — the user, 2026-11-16.
- **First launch asks once to download the current yt-dlp; the package
  Requires the distro's yt-dlp as the fallback; Revert returns to it** — the
  user, 2026-11-16.
- **"Ask once" means once ever.** If declined, Snatch never asks again by
  itself and the Update button still offers it. Once a downloaded copy is in
  use, newer versions are offered as in the AppImage — the user, 2026-11-16.
- **A marker file written by the package build decides "installed by a
  package"**, not a guess from the folder — the user, 2026-11-16.
- **A package install does not check for a newer Snatch** — the user,
  2026-11-16.
- **The package Requires `quickjs`** as yt-dlp's JavaScript runtime — the
  user, 2026-11-16.
- **Settings live in the AppImage's `$XDG_DATA_HOME/snatch`**, so the package
  and the AppImage share them — recorded on SNAT-0028 by an earlier session;
  no new location.

## 4. Design

### 4.1 Detecting a package install

The package build writes an empty file `snatch/INSTALLED_BY_PACKAGE` beside
the package's modules. Nothing else creates it. It is in `.gitignore`.

```python
# snatch/platform_utils.py
_PACKAGE_MARKER = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "INSTALLED_BY_PACKAGE")
_PACKAGE_INSTALL = None   # cached; tests reset it like _USER_BIN_DIR

def is_package_install() -> bool:
    """True when a distro package installed this copy (SNAT-0028)."""
```

A frozen build never has the marker, so `is_frozen()` and
`is_package_install()` are never both true.

### 4.2 Paths

`app_data_dir()` gains a branch after the frozen ones and before the source
one. The Linux frozen branch and the new one share one helper, so the
location is stated once:

```python
def _xdg_data_dir():
    base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    return _ensure_dir(os.path.join(base, "snatch"))

def app_data_dir():
    if is_frozen():
        ...                       # Windows, macOS unchanged
        return _xdg_data_dir()    # Linux AppImage, unchanged in effect
    if is_package_install():
        return _xdg_data_dir()
    return <project root>         # source run, unchanged
```

- `user_bin_dir()` uses `["bin"]` when `is_frozen() or is_package_install()`,
  so the package and the AppImage share one fetched yt-dlp.
- `_find_bundled_binary()` returns `None` on a package install. The package
  ships no `bin/`, and this keeps a stray `/usr/share/snatch/bin/` from ever
  becoming the floor. `find_ytdlp()` is then: fetched copy, else `PATH`.
- `SnatchApp._set_icon` loads `resource_path("icon.png")`. From source and in
  the package that is the install root; in a frozen build it is `_MEIPASS`.

### 4.3 The yt-dlp offer and Revert

One helper names the fallback, so the three dialogs and the button agree:

```python
# snatch/version.py
def _fallback_words() -> tuple[str, str]:
    """(button word, sentence phrase) for the copy Revert returns to."""
    # package install → ("system", "your system's yt-dlp")
    # otherwise       → ("bundled", "the copy that came with Snatch")
```

`_refresh_idle_button`, `_prompt_update`, `_prompt_revert` and the status line
after a revert take their wording from it. Off a package install the text is
today's, word for word.

**Ask once.** A new config key, `ytdlp_offer_shown` (bool, default `false`),
is loaded in `SnatchApp.__init__` and written by `_save_config`.
`_show_update_available` becomes:

```python
self.update_btn.config(text=f"Update to {self.latest_version}", state=tk.NORMAL)
self.status_var.set(...)                       # unchanged
if is_package_install() and not updated_ytdlp_path():
    if self.ytdlp_offer_shown:
        return                                  # button only, no dialog
    self.ytdlp_offer_shown = True
    self._save_config()
self._prompt_update()
```

The flag is set only when the dialog is about to show. A first launch that is
offline, or rate-limited by GitHub, does not use it up. With a downloaded copy
in use, the package behaves as the AppImage does.

### 4.4 No self-update check

`VersionMixin.check_app_update` returns at once when `is_package_install()`.
No thread starts, no request is made, and the "Snatch X available" button is
never shown. `detect_installer()` is unchanged: it already returns `None` for
any non-frozen run.

### 4.5 JavaScript runtime on PATH

`DownloaderMixin._ensure_runtime_cache` keeps its bundled entry and its
`deno`, `node`, `bun` names. For QuickJS it looks for `qjs`, the name both
upstream and Tumbleweed install, and enables it as `quickjs`:

```python
if shutil.which("qjs"):
    runtimes.append("quickjs")   # yt-dlp resolves "quickjs" to qjs on PATH
```

The `shutil.which("quickjs")` probe goes; nothing installs that name.

### 4.6 The package

New files, all under `packaging/obs/`:

| File | Installed as |
|------|--------------|
| `snatch.spec` | the RPM recipe |
| `_service` | OBS source services |
| `snatch.sh` | `/usr/bin/snatch` |
| `io.github.milnet01.snatch.desktop` | `/usr/share/applications/` |
| `io.github.milnet01.snatch.metainfo.xml` | `/usr/share/metainfo/` |

The app itself goes to `/usr/share/snatch/`: `snatch.py`, the `snatch/`
package and `icon.png`. `%install` byte-compiles it there, so no user run
tries to write `__pycache__`. Icons go to
`/usr/share/icons/hicolor/{48x48,64x64,256x256}/apps/io.github.milnet01.snatch.png`
from `icon_48.png`, `icon_64.png` and `icon.png`. The marker is written by
`%install`:

```sh
touch %{buildroot}%{_datadir}/snatch/snatch/INSTALLED_BY_PACKAGE
```

The launcher:

```sh
#!/bin/sh
exec /usr/bin/python3 /usr/share/snatch/snatch.py "$@"
```

The desktop entry has `Exec=snatch`, `Icon=io.github.milnet01.snatch` and
`StartupWMClass=Snatch` (the class `snatch/__main__.py` gives Tk). The
metainfo carries no `<releases>` block, so it adds no version surface.

`snatch.spec` follows `finbreak/packaging/obs/finbreak.spec` where they
overlap — the `Version: 0` placeholder, the `_service` that sets it, and no
`%post` scriptlets, since Tumbleweed's file triggers refresh the icon and
desktop caches. It differs in what it ships: source, not a frozen bundle.

```
BuildArch:  noarch
Requires:   python3 >= 3.10
Requires:   python3-tk
Requires:   python3-Pillow
Requires:   python3-Pillow-tk
Requires:   python3-cryptography
Requires:   yt-dlp
Requires:   quickjs
Requires:   ffmpeg
Requires:   hicolor-icon-theme
Recommends: mpv
```

`BuildRequires` carries `python3-tk`, `python3-Pillow-tk` and
`python3-cryptography` too, for `%check` (§4.6, INV-14).

Each name was checked against Tumbleweed with `zypper se --provides
--match-exact <name>` on 2026-11-16; all resolve. `python3-cryptography` is
required because `--selftest` imports every module (`selftest.MODULES`), and
`snatch.self_update` imports `cryptography`. `tkinterdnd2` is not packaged
for Tumbleweed (`zypper se tkinterdnd2` finds nothing), so drag-and-drop is
off in the package (`HAS_DND` false) — §9.

`%check` runs `python3 %{buildroot}%{_datadir}/snatch/snatch.py --selftest`
against the staged tree, as finbreak's does, with `XDG_DATA_HOME` set to a
folder inside the build directory so the result does not depend on the build
machine's `$HOME`. The self-test gains one check,
active only on a package install: `app_data_dir()` is not the install
directory, and a file can be created in it.

### 4.7 Source and releases

`_service` mirrors finbreak's: `obs_scm` on
`https://github.com/milnet01/snatch.git` at the release tag (`v<version>`),
`tar`, `recompress` to gz, `set_version`. All `mode="manual"`.

`.claude/bump.json` gains the `_service` `revision` line, and
`scripts/check-version-drift.sh` checks it, so a release cannot leave the
package on the old tag. `docs/building.md` § Releasing gains the OBS step:
`osc service manualrun`, then `osc commit`, in a checkout of
`home:milnet:snatch/snatch`.

**The first submit publishes under the user's OBS account**, so it waits for
the user's go-ahead.

## 5. Invariants

- **INV-1** — `is_package_install()` is true exactly when
  `snatch/INSTALLED_BY_PACKAGE` exists beside the package's modules.
  *Test:* `tests/test_package_install.py::test_marker_decides_package_install`.
  *Breaks when:* detection reads anything else, such as whether the folder is
  writable — the fixture is a writable temp folder with and without the
  marker.

- **INV-2** — On a package install, `app_data_dir()` is
  `$XDG_DATA_HOME/snatch`, or `~/.local/share/snatch` when that is unset, and
  never the install directory.
  *Test:* `tests/test_package_install.py::test_package_data_goes_to_xdg`.
  *Breaks when:* the package branch is missing or sits after the source
  branch, so the install root is returned.

- **INV-3** — Without the marker and not frozen, `app_data_dir()` is the
  project root and `user_bin_dir()` is `<root>/bin/updated`, as today.
  *Test:* `tests/test_package_install.py::test_source_run_is_unchanged`, with
  the existing `tests/test_binary_resolution.py`.
  *Breaks when:* the marker check is inverted, or the package branch is taken
  for a source run.

- **INV-4** — The marker is never in the repository.
  *Test:* `tests/test_package_install.py::test_marker_is_ignored_and_untracked`,
  which runs `git ls-files snatch/INSTALLED_BY_PACKAGE` (expects no output)
  and `git check-ignore -q snatch/INSTALLED_BY_PACKAGE` (expects exit 0;
  today it exits 1).
  *Breaks when:* the file is committed, which turns every source checkout
  into a package install; or the `.gitignore` line is missing.

- **INV-5** — On a package install, `user_bin_dir()` is `app_data_dir()/bin`.
  *Test:* `tests/test_package_install.py::test_package_shares_the_appimage_bin_dir`.
  *Breaks when:* the package takes the source run's `bin/updated`.

- **INV-6** — On a package install, `find_ytdlp()` returns the fetched copy
  when one is present and executable, and otherwise the `PATH` copy — never a
  file under the install directory.
  *Test:* `tests/test_package_install.py::test_package_ytdlp_order`, with a
  `yt-dlp` planted in the fake install's `bin/`.
  *Breaks when:* `_find_bundled_binary()` still searches the install root on a
  package install.

- **INV-7** — On a package install, `check_app_update()` starts no thread and
  makes no request.
  *Test:* `tests/test_package_install.py::test_package_does_not_check_for_snatch_updates`.
  *Breaks when:* the early return is missing, which the test sees as a call to
  the HTTPS opener.

- **INV-8** — On a package install with no downloaded yt-dlp, a newer
  version shows the update dialog at most once over the life of `config.json`.
  Showing it sets `ytdlp_offer_shown` and saves the config. Later launches set
  the button to "Update to <version>" and show no dialog.
  *Test:* `tests/test_package_install.py::test_offer_is_shown_once`.
  *Breaks when:* the flag is not saved, or not read on the next start.

- **INV-9** — `ytdlp_offer_shown` is set only when the dialog is shown. A run
  whose version check fails, or finds nothing newer, leaves it false.
  *Test:* `tests/test_package_install.py::test_failed_check_keeps_the_offer`.
  *Breaks when:* the flag is set at startup or when the check begins.

- **INV-10** — On a package install the Revert button reads "Revert to
  system yt-dlp", and the update dialog, the revert dialog and the status
  line after a revert name "your system's yt-dlp". Off a package install all
  four are today's text.
  *Test:* `tests/test_package_install.py::test_fallback_wording`.
  *Breaks when:* any of the four call sites keeps its own string.

- **INV-11** — On a package install, Revert deletes the downloaded copy, and
  `find_ytdlp()` then returns the `PATH` copy.
  *Test:* `tests/test_package_install.py::test_revert_returns_to_system_ytdlp`.
  *Breaks when:* Revert deletes a file in another folder, or the lookup still
  finds a non-`PATH` copy.

- **INV-12** — A `qjs` on `PATH` enables yt-dlp's `quickjs` runtime.
  *Test:* `tests/test_package_install.py::test_qjs_on_path_enables_quickjs`,
  with a fake `PATH` holding only `qjs`.
  *Breaks when:* the probe looks for `quickjs`, as today's code does — the test
  fails against today's code.

- **INV-13** — The window icon comes from `resource_path("icon.png")`.
  *Test:* `tests/test_package_install.py::test_window_icon_comes_from_the_install`.
  *Breaks when:* `_set_icon` joins `app_data_dir()`.

- **INV-14** — The package's `%check` runs `--selftest` on the staged tree,
  and it passes, including the package data-folder check.
  *Test:* the OBS build log for `openSUSE_Tumbleweed` ends with `OK: 0 check(s) failed` from `%check`.
  *Breaks when:* the marker is not written, so the data-folder check skips;
  or a Requires is missing from the build root, so an import fails.

- **INV-15** — The installed package pulls in everything §4.6 lists, and
  `snatch` from a terminal opens the window with the system's yt-dlp in use.
  *Test:* manual recipe, §7.
  *Breaks when:* a Requires is missing or misspelled for Tumbleweed.

- **INV-16** — The spec's version comes only from the release tag.
  *Test:* `tests/test_package_install.py::test_spec_version_is_a_placeholder`,
  which reads `packaging/obs/snatch.spec` and expects its `Version:` field to
  be `0`.
  *Breaks when:* someone types a real version into the spec.

- **INV-17** — The `_service` revision matches `__version__`.
  *Test:* `bash scripts/check-version-drift.sh` on a tree whose `_service`
  revision is `v0.0.0` → a non-zero exit naming `packaging/obs/_service`.
  (It exits 0 today on any `_service`, because it does not read one.)
  *Breaks when:* a release bumps `__version__` and not the `_service` tag.

- **INV-18** — The package adds no download path. A yt-dlp fetched on a
  package install goes through `_update_ytdlp_thread`, with its HTTPS-only
  opener, tag-shape check, published SHA-256 match and temp-then-rename, into
  a folder inside `$HOME` owned by the user. Nothing writes outside `$HOME`
  and nothing asks for a password.
  *Test:* `tests/test_update_promotion.py` and `tests/test_https_only.py`
  (existing), plus a search of the diff for new `urlopen` or `_open_https`
  callers.
  *Breaks when:* the package path gets its own fetch, or a system-wide target.

## 6. Failure modes

- **Offline or rate-limited first launch.** No dialog; the flag stays false
  (INV-9); the next online launch asks. The distro yt-dlp works for sites
  other than YouTube meanwhile.
- **User says No.** The distro yt-dlp stays. YouTube may fail. The Update
  button still offers the download; Snatch never asks again by itself.
- **The download fails verification.** As today: the previous state stays and
  the error is shown. On a package install the previous state is the distro
  copy.
- **The user removes the distro yt-dlp** with `rpm -e --nodeps`. `find_ytdlp()`
  returns its literal `"yt-dlp"`; the version line reads "yt-dlp not found",
  as today.
- **AppImage and package used by one person.** They share config, history and
  the fetched yt-dlp. Revert in either deletes the shared copy; each falls
  back to its own floor. An AppImage older than this change drops the
  `ytdlp_offer_shown` key when it saves, so the package asks once more.
- **`$XDG_DATA_HOME` unwritable.** As for the AppImage today: saves log a
  warning and fail; the app still runs.
- **Someone creates the marker in a source checkout.** The checkout behaves as
  a package. `.gitignore` keeps it out of commits (INV-4).
- **A Requires name is wrong for Tumbleweed.** The OBS build fails as
  unresolvable; nothing is published.

## 7. Tests

`tests/test_package_install.py` (new) holds INV-1 to INV-13 and INV-16. Each test points `platform_utils._PACKAGE_MARKER` at a temp file and
resets `_PACKAGE_INSTALL` and `_USER_BIN_DIR`, as
`tests/test_binary_resolution.py` resets its cache. GUI behaviour is tested on
the mixins with stubbed widgets and `messagebox`, as
`tests/test_app_update_notice.py` does; no Tk window opens.

Each test must be seen to fail on today's code before the change goes in.
INV-12's fails today as written. INV-3's passes today by design: it guards
the source path against the change.

INV-4 runs `git` with a timeout, per `CLAUDE.md`. INV-17 is a command (§5). INV-14 is read from the OBS build
log. INV-18 rests on the existing tests named in its clause.

### 7.1 Manual recipe (INV-15)

On Tumbleweed, as a normal user, with a fresh `XDG_DATA_HOME`:

1. `zypper ar` the `home:milnet:snatch` repository, then `zypper in snatch`.
   Confirm `yt-dlp`, `quickjs`, `ffmpeg` and `python313-tk` were pulled in.
2. Start Snatch from the menu. It shows its icon in the window and taskbar.
3. It asks once to download yt-dlp. Answer No. Close and reopen: no dialog;
   the button reads "Update to <version>".
4. Click it, answer Yes. The version line shows the nightly. Download a
   YouTube video.
5. Click "Revert to system yt-dlp". The version line shows the distro version.
6. Confirm `~/.local/share/snatch/` (or the fresh `XDG_DATA_HOME`) holds
   `config.json`, `history.json` and `bin/`, and nothing was written under
   `/usr/share/snatch/`.
7. Confirm no "Snatch X available" button appears.

## 8. Alternatives considered (and rejected)

- **Guess a package install from an unwritable install folder.** A source
  checkout on a read-only drive would be taken for a package, and a package
  run as root would not. The user chose the marker.
- **Detect by path prefix (`/usr/`).** Breaks for other prefixes and other
  layouts; still a guess.
- **Freeze the app with PyInstaller as finbreak does.** `is_frozen()` would
  then route data to XDG with no new branch. Rejected: it bundles Python and
  the libraries, losing the size and the distro updates the roadmap names as
  the reason for a package.
- **Install as a Python module in site-packages.** openSUSE builds Python
  modules once per Python version, which suits a library rather than an app.
  A private `/usr/share/snatch` is one copy.
- **Keep Snatch's own update notice on the package.** It would point a zypper
  user at an AppImage download. The user chose to skip it.
- **Require `deno`.** yt-dlp's default runtime, but a much larger install than
  `quickjs`, which the AppImage already bundles. The user chose `quickjs`.
- **Ask every launch, as the AppImage does.** The user chose once.

## 9. Out of scope

- Fedora, Debian, Ubuntu, Arch and Leap — deferred; not yet queued. SNAT-0028's
  headline covers them; this spec is the Tumbleweed step.
- Packaging `tkinterdnd2` for Tumbleweed, to restore drag-and-drop in the
  package — deferred; not yet queued.
- Rebuilding on OBS automatically when a tag is pushed — deferred; not yet
  queued. §4.7's manual step stands until then.
- Any change to the AppImage, Windows or macOS builds beyond the shared code
  in §4.2 to §4.5.

## 10. What checks this

| Rule | What catches a breach |
|------|----------------------|
| INV-1 | `tests/test_package_install.py::test_marker_decides_package_install` |
| INV-2 | `tests/test_package_install.py::test_package_data_goes_to_xdg` |
| INV-3 | `tests/test_package_install.py::test_source_run_is_unchanged`; `tests/test_binary_resolution.py` |
| INV-4 | `tests/test_package_install.py::test_marker_is_ignored_and_untracked` |
| INV-5 | `tests/test_package_install.py::test_package_shares_the_appimage_bin_dir` |
| INV-6 | `tests/test_package_install.py::test_package_ytdlp_order` |
| INV-7 | `tests/test_package_install.py::test_package_does_not_check_for_snatch_updates` |
| INV-8 | `tests/test_package_install.py::test_offer_is_shown_once` |
| INV-9 | `tests/test_package_install.py::test_failed_check_keeps_the_offer` |
| INV-10 | `tests/test_package_install.py::test_fallback_wording` |
| INV-11 | `tests/test_package_install.py::test_revert_returns_to_system_ytdlp` |
| INV-12 | `tests/test_package_install.py::test_qjs_on_path_enables_quickjs` |
| INV-13 | `tests/test_package_install.py::test_window_icon_comes_from_the_install` |
| INV-14 | the OBS build for `openSUSE_Tumbleweed`, which fails on a failed `%check` |
| INV-15 | **nothing** — the §7.1 manual recipe; no Tumbleweed install runs in CI |
| INV-16 | `tests/test_package_install.py::test_spec_version_is_a_placeholder` |
| INV-17 | `scripts/check-version-drift.sh`, run by `cut-release`'s post-check |
| INV-18 | Partial: `tests/test_update_promotion.py` and `tests/test_https_only.py` lock the fetch; nothing catches a new fetch path added elsewhere |

## 11. Cross-doc impact

- `docs/building.md` § Where user data goes — a package row; § Releasing —
  the OBS step (§4.7).
- `STANDARDS.md` § 14 — a package row in the location table.
- `CLAUDE.md` § Quick Reference — the `app_data_dir()` line names the package
  case.
- `README.md` — a Tumbleweed install section.
- `CHANGELOG.md` — `[Unreleased]` entry.
- `docs/specs/SNAT-0038-signed-auto-update.md` § 1 — "Every other build keeps
  today's behaviour" gains "except a distro package, which shows no button
  (SNAT-0028)".
- `.claude/bump.json` and `scripts/check-version-drift.sh` — the `_service`
  revision (§4.7).
- `.gitignore` — the marker.

## 12. Cold-eyes loop log

Rows live in `../reviews/SNAT-0028-obs-package-loop-log.md`.

## 13. Resource cost

One boolean in `config.json`. The package adds no bundled binaries; its new
dependencies are Tumbleweed packages listed in §4.6.
