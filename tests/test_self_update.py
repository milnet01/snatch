"""Finding, fetching and verifying a signed Snatch update (SNAT-0038).

The updater downloads code from the network and runs it as the user, so every
refusal here is the feature, not an edge case. The network is a dict of
URL -> bytes, and the release key is one made in the test, so nothing here
depends on the real key or on GitHub.
"""

import hashlib
import io
import json

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from snatch import self_update
from snatch.self_update import (UpdateCancelled, UpdateDownloadError,
                                UpdateOffer, UpdateVerificationError,
                                download_verified, find_offer, parse_manifest)

ASSET = "Snatch-x86_64.AppImage"
BUILD = b"the new AppImage" * 1000
BASE = "https://github.com/milnet01/snatch/releases/download/v1.4.0/"


def _manifest(version="1.4.0", assets=None):
    assets = assets if assets is not None else {
        ASSET: hashlib.sha256(BUILD).hexdigest(),
        "Snatch-arm64.dmg": "0" * 64,
        "snatch.exe": "1" * 64,
    }
    lines = ["snatch-update 1", f"version {version}"]
    lines += [f"{digest}  {name}" for name, digest in assets.items()]
    return ("\n".join(lines) + "\n").encode("ascii")


class _Response(io.BytesIO):
    def __init__(self, body, length=None):
        super().__init__(body)
        size = len(body) if length is None else length
        self.headers = {"Content-Length": str(size)}


class Network:
    """Serves `files` by URL and records every URL opened, in order."""

    def __init__(self, files, lengths=None):
        self.files = files
        self.lengths = lengths or {}
        self.opened = []

    def __call__(self, url, _timeout):
        self.opened.append(url)
        if url not in self.files:
            raise OSError(f"404 {url}")
        return _Response(self.files[url], self.lengths.get(url))


@pytest.fixture
def release_key(monkeypatch):
    key = Ed25519PrivateKey.generate()
    monkeypatch.setattr(self_update, "public_key", key.public_key)
    monkeypatch.setattr(self_update, "__version__", "1.3.1")
    return key


def _offer(version="1.4.0", asset_name=ASSET):
    return UpdateOffer(version=version, asset_name=asset_name,
                       asset_url=BASE + asset_name,
                       manifest_url=BASE + "SNATCH-UPDATE",
                       signature_url=BASE + "SNATCH-UPDATE.sig",
                       notes="")


def _serve(monkeypatch, signer, manifest=None, build=BUILD, lengths=None,
           asset_name=ASSET):
    manifest = _manifest() if manifest is None else manifest
    net = Network({BASE + "SNATCH-UPDATE": manifest,
                   BASE + "SNATCH-UPDATE.sig": signer.sign(manifest),
                   BASE + asset_name: build}, lengths)
    monkeypatch.setattr(self_update, "_open_https", net)
    return net


def _download(tmp_path, offer=None, cancelled=lambda: False):
    return download_verified(offer or _offer(), str(tmp_path),
                             on_progress=lambda done, total: None,
                             cancelled=cancelled)


def _leftovers(tmp_path):
    return sorted(p.name for p in tmp_path.iterdir()
                  if p.name.startswith(".snatch-update-"))


# ── INV-1: an offer needs a newer release with all three assets ──────────

def _release(tag="v1.4.0", names=(ASSET, "SNATCH-UPDATE", "SNATCH-UPDATE.sig")):
    return {"tag_name": tag, "body": "What changed.",
            "assets": [{"name": n, "browser_download_url": BASE + n}
                       for n in names]}


def test_offer_for_a_complete_newer_release():
    offer = find_offer(_release(), "1.3.1", ASSET)
    assert offer == UpdateOffer(
        version="1.4.0", asset_name=ASSET, asset_url=BASE + ASSET,
        manifest_url=BASE + "SNATCH-UPDATE",
        signature_url=BASE + "SNATCH-UPDATE.sig", notes="What changed.")


@pytest.mark.parametrize("release", [
    _release(names=(ASSET, "SNATCH-UPDATE")),
    _release(names=(ASSET, "SNATCH-UPDATE.sig")),
    _release(names=("SNATCH-UPDATE", "SNATCH-UPDATE.sig")),
    _release(names=("snatch.exe", "SNATCH-UPDATE", "SNATCH-UPDATE.sig")),
    _release(names=(ASSET, ASSET, "SNATCH-UPDATE", "SNATCH-UPDATE.sig")),
    _release(tag="v1.3.1"),
    _release(tag="v1.4.0/../evil"),
    {"tag_name": "v1.4.0"},
    {"tag_name": "v1.4.0", "assets": "nope"},
], ids=["no-signature", "no-manifest", "no-asset", "other-platform-only",
        "asset-twice", "not-newer", "bad-tag", "no-assets", "assets-not-a-list"])
def test_offer_is_refused_for_an_incomplete_release(release):
    assert find_offer(release, "1.3.1", ASSET) is None


def test_offer_refuses_an_asset_url_off_https():
    release = _release()
    release["assets"][0]["browser_download_url"] = "http://example.com/x"
    assert find_offer(release, "1.3.1", ASSET) is None


# ── INV-2: nothing is fetched for the asset until the signature verifies ──

def test_bad_signature_downloads_nothing(monkeypatch, tmp_path, release_key):
    impostor = Ed25519PrivateKey.generate()
    net = _serve(monkeypatch, impostor)
    with pytest.raises(UpdateVerificationError):
        _download(tmp_path)
    assert BASE + ASSET not in net.opened
    assert _leftovers(tmp_path) == []


# ── INV-3: the manifest names the offered version, and it is newer ───────

def test_replayed_manifest_is_refused(monkeypatch, tmp_path, release_key):
    net = _serve(monkeypatch, release_key, manifest=_manifest(version="1.0.0"))
    with pytest.raises(UpdateVerificationError):
        _download(tmp_path, _offer(version="9.0.0"))
    assert BASE + ASSET not in net.opened


def test_a_manifest_not_newer_than_this_build_is_refused(
        monkeypatch, tmp_path, release_key):
    monkeypatch.setattr(self_update, "__version__", "1.4.0")
    _serve(monkeypatch, release_key)
    with pytest.raises(UpdateVerificationError):
        _download(tmp_path)


# ── INV-4: the installed bytes hash to this build's line ─────────────────

def test_a_verified_download_is_returned(monkeypatch, tmp_path, release_key):
    _serve(monkeypatch, release_key)
    path = _download(tmp_path)
    assert path.startswith(str(tmp_path))
    with open(path, "rb") as handle:
        assert handle.read() == BUILD


def test_digest_mismatch_is_refused(monkeypatch, tmp_path, release_key):
    _serve(monkeypatch, release_key, build=BUILD + b"tampered")
    with pytest.raises(UpdateVerificationError):
        _download(tmp_path)


def test_other_platforms_digest_is_refused(monkeypatch, tmp_path, release_key):
    # The AppImage's bytes, served as snatch.exe: they match the AppImage
    # line, and must be checked against the snatch.exe line.
    _serve(monkeypatch, release_key, asset_name="snatch.exe")
    with pytest.raises(UpdateVerificationError):
        _download(tmp_path, _offer(asset_name="snatch.exe"))


# ── INV-5: a manifest is the exact shape or nothing ──────────────────────

def test_manifest_parse_accepts_the_spec_shape():
    version, digests = parse_manifest(_manifest())
    assert version == "1.4.0"
    assert digests[ASSET] == hashlib.sha256(BUILD).hexdigest()
    assert set(digests) == {ASSET, "Snatch-arm64.dmg", "snatch.exe"}


HEX = "a" * 64


@pytest.mark.parametrize("data", [
    b"snatch-update 1\nversion 1.4.0\n" + f"{HEX}  x\nextra line\n".encode(),
    b"version 1.4.0\n" + f"{HEX}  x\n".encode(),
    b"snatch-update 1\n" + f"{HEX}  x\n".encode(),
    b"snatch-update 1\nversion 1.4.0\n",
    b"snatch-update 2\nversion 1.4.0\n" + f"{HEX}  x\n".encode(),
    b"snatch-update 1\nversion 1.4.0\n" + f"{HEX}  x\n{HEX}  x\n".encode(),
    b"snatch-update 1\r\nversion 1.4.0\r\n" + f"{HEX}  x\r\n".encode(),
    b"snatch-update 1\nversion 1.4.0\n" + f"{HEX}  x".encode(),
    b"snatch-update 1\nversion 1.4.0\n" + f"{'A' * 64}  x\n".encode(),
    b"snatch-update 1\nversion 1.4.0\n" + f"{HEX} x\n".encode(),
    b"snatch-update 1\nversion 1.4\n" + f"{HEX}  x\n".encode(),
    b"snatch-update 1\nversion 1.4.0\n\n" + f"{HEX}  x\n".encode(),
    b"snatch-update 1\nversion 1.4.0\n" + f"{HEX}  \xe9\n".encode("latin-1"),
    _manifest() + b"#" * (64 * 1024),
], ids=["unknown-line", "no-header", "no-version", "no-assets",
        "other-format", "repeated-name", "crlf", "no-final-newline",
        "uppercase-hex", "one-space", "short-version", "blank-line",
        "not-ascii", "over-64-kib"])
def test_manifest_parse_rejects_the_whole_file(data):
    with pytest.raises(UpdateVerificationError):
        parse_manifest(data)


# ── INV-7: a failed or cancelled download leaves nothing behind ──────────

def _running_file(tmp_path):
    running = tmp_path / ASSET
    running.write_bytes(b"the build that is running")
    return running


def test_failure_leaves_no_temp_on_a_truncated_body(
        monkeypatch, tmp_path, release_key):
    running = _running_file(tmp_path)
    _serve(monkeypatch, release_key, lengths={BASE + ASSET: len(BUILD) + 10})
    with pytest.raises(UpdateDownloadError):
        _download(tmp_path)
    assert _leftovers(tmp_path) == []
    assert running.read_bytes() == b"the build that is running"


def test_failure_leaves_no_temp_on_a_digest_mismatch(
        monkeypatch, tmp_path, release_key):
    running = _running_file(tmp_path)
    _serve(monkeypatch, release_key, build=b"something else")
    with pytest.raises(UpdateVerificationError):
        _download(tmp_path)
    assert _leftovers(tmp_path) == []
    assert running.read_bytes() == b"the build that is running"


def test_failure_leaves_no_temp_on_cancel(monkeypatch, tmp_path, release_key):
    running = _running_file(tmp_path)
    _serve(monkeypatch, release_key)
    with pytest.raises(UpdateCancelled):
        _download(tmp_path, cancelled=lambda: True)
    assert _leftovers(tmp_path) == []
    assert running.read_bytes() == b"the build that is running"


def test_failure_leaves_no_temp_on_an_oversize_length(
        monkeypatch, tmp_path, release_key):
    running = _running_file(tmp_path)
    _serve(monkeypatch, release_key,
           lengths={BASE + ASSET: self_update.UPDATE_MAX_BYTES + 1})
    with pytest.raises(UpdateDownloadError):
        _download(tmp_path)
    assert _leftovers(tmp_path) == []
    assert running.read_bytes() == b"the build that is running"


# ── Notes: every version since ours, newest first ────────────────────────

def _releases(*tags):
    return json.dumps([{"tag_name": t, "body": f"notes {t}", "draft": False,
                        "prerelease": False} for t in tags]).encode()


def test_notes_cover_every_version_since_ours(monkeypatch):
    listing = _releases("v1.4.0", "v1.3.3", "v1.3.2", "v1.3.1", "v1.2.0")
    net = Network({self_update.RELEASES_LIST_API: listing})
    monkeypatch.setattr(self_update, "_open_https", net)
    offer = self_update.with_notes(_offer(), "1.3.1")
    assert offer.notes == ("## 1.4.0\n\nnotes v1.4.0\n\n---\n\n"
                           "## 1.3.3\n\nnotes v1.3.3\n\n---\n\n"
                           "## 1.3.2\n\nnotes v1.3.2")


def test_notes_skip_drafts_prereleases_and_later_tags(monkeypatch):
    listing = json.loads(_releases("v1.5.0", "v1.4.0", "v1.3.9", "v1.3.8"))
    listing[2]["draft"] = True
    listing[3]["prerelease"] = True
    net = Network({self_update.RELEASES_LIST_API: json.dumps(listing).encode()})
    monkeypatch.setattr(self_update, "_open_https", net)
    offer = self_update.with_notes(_offer(), "1.3.1")
    assert offer.notes == "## 1.4.0\n\nnotes v1.4.0"


def test_notes_fall_back_to_the_offered_release(monkeypatch):
    monkeypatch.setattr(self_update, "_open_https", Network({}))
    offer = self_update.with_notes(
        UpdateOffer("1.4.0", ASSET, "", "", "", notes="Just this one."),
        "1.3.1")
    assert offer.notes == "## 1.4.0\n\nJust this one."
