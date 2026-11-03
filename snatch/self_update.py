"""Find, fetch and verify a signed Snatch update (SNAT-0038).

The spec is docs/specs/SNAT-0038-signed-auto-update.md. This module decides
whether a release can be installed and produces a verified file; it creates
no widgets and installs nothing (update_installer.py does that).

The order in download_verified is the security: nothing is written for the
build until the manifest's signature has verified against the release key,
and the build is returned only once its bytes hash to the manifest's line for
this platform's asset.
"""

import hashlib
import http.client
import json
import os
import re
import tempfile
import time
from dataclasses import dataclass, replace

from cryptography.exceptions import InvalidSignature

from . import __version__
from .downloader import DownloaderMixin
from .logging_setup import get_logger
from .update_key import public_key
from .version import (SNATCH_TAG_RE, UPDATE_CHECK_TIMEOUT_SEC,
                      YTDLP_CHUNK_BYTES, _open_https, newer_app_version)

log = get_logger(__name__)

MANIFEST_ASSET = "SNATCH-UPDATE"
SIGNATURE_ASSET = "SNATCH-UPDATE.sig"
MANIFEST_MAX_BYTES = 64 * 1024
SIGNATURE_BYTES = 64
# The builds run to about 150 MB. The cap stops a substituted response from
# filling the disk; it is not an estimate of their size.
UPDATE_MAX_BYTES = 512 * 1024 * 1024

# Every release since ours, for the notes. 30 is one page and far more
# versions than anyone falls behind by.
RELEASES_LIST_API = (
    "https://api.github.com/repos/milnet01/snatch/releases?per_page=30")
RELEASES_LIST_MAX_BYTES = 4 * 1024 * 1024
NOTES_SEPARATOR = "\n\n---\n\n"

MANIFEST_HEADER = "snatch-update 1"
_VERSION_LINE_RE = re.compile(r"version ([0-9]+\.[0-9]+\.[0-9]+)")
_ASSET_LINE_RE = re.compile(r"([0-9a-f]{64})  ([A-Za-z0-9._-]+)")

# What a failed fetch raises. ValueError is _open_https refusing a non-HTTPS
# hop; HTTPException is a body cut short (IncompleteRead), which is not an
# OSError.
_NETWORK_ERRORS = (OSError, ValueError, http.client.HTTPException)


class UpdateError(Exception):
    """Any reason an update was not produced."""


class UpdateDownloadError(UpdateError):
    """The network failed or served something incomplete."""


class UpdateVerificationError(UpdateError):
    """What arrived is not what the release key signed."""


class UpdateCancelled(UpdateError):
    """The user stopped the download."""


@dataclass(frozen=True)
class UpdateOffer:
    version: str          # "1.4.0"
    asset_name: str       # find_offer's argument; download_verified looks up its digest
    asset_url: str        # browser_download_url of this build's asset
    manifest_url: str
    signature_url: str
    notes: str            # every version since ours, newest first


def _version_tuple(version):
    return tuple(int(part) for part in version.split("."))


def find_offer(release, current, asset_name):
    """An UpdateOffer for `release` (parsed /releases/latest JSON), else None.

    Fetches nothing. None means the button keeps opening the release page:
    the release is not newer, or it lacks exactly one each of this build's
    asset, the manifest and its signature.
    """
    if not isinstance(release, dict):
        return None
    version = newer_app_version(release.get("tag_name"), current)
    assets = release.get("assets")
    if not version or not isinstance(assets, list):
        return None
    urls = {}
    for asset in assets:
        if isinstance(asset, dict):
            urls.setdefault(asset.get("name"), []).append(
                asset.get("browser_download_url"))
    wanted = {}
    for name in (asset_name, MANIFEST_ASSET, SIGNATURE_ASSET):
        found = urls.get(name, [])
        if len(found) != 1 or not isinstance(found[0], str) \
                or not found[0].startswith("https://"):
            return None
        wanted[name] = found[0]
    body = release.get("body")
    return UpdateOffer(version=version, asset_name=asset_name,
                       asset_url=wanted[asset_name],
                       manifest_url=wanted[MANIFEST_ASSET],
                       signature_url=wanted[SIGNATURE_ASSET],
                       notes=body if isinstance(body, str) else "")


def _section(version, body):
    return f"## {version}\n\n{(body or '').strip()}"


def with_notes(offer, current):
    """`offer` with the notes of every release in (current, offered].

    One more fetch. When it fails, the offered release's own notes are used,
    so the notes never block the offer.
    """
    fallback = replace(offer, notes=_section(offer.version, offer.notes))
    try:
        with _open_https(RELEASES_LIST_API, UPDATE_CHECK_TIMEOUT_SEC) as resp:
            raw = resp.read(RELEASES_LIST_MAX_BYTES + 1)
        if len(raw) > RELEASES_LIST_MAX_BYTES:
            raise ValueError("release list larger than expected")
        releases = json.loads(raw)
        del raw
    except _NETWORK_ERRORS:
        log.debug("Could not fetch the notes since %s", current, exc_info=True)
        return fallback
    if not isinstance(releases, list):
        return fallback
    low, high = _version_tuple(current), _version_tuple(offer.version)
    found = []
    for release in releases:
        if not isinstance(release, dict) or release.get("draft") \
                or release.get("prerelease"):
            continue
        tag = release.get("tag_name")
        match = SNATCH_TAG_RE.match(tag) if isinstance(tag, str) else None
        if match is None:
            continue
        version = tuple(int(part) for part in match.groups())
        if low < version <= high:
            body = release.get("body")
            found.append((version, body if isinstance(body, str) else ""))
    del releases
    if not found:
        return fallback
    found.sort(reverse=True)
    notes = NOTES_SEPARATOR.join(
        _section(".".join(map(str, v)), body) for v, body in found)
    return replace(offer, notes=notes)


def parse_manifest(data):
    """(version, {asset name: sha256 hex}) from SNATCH-UPDATE's bytes.

    The shape is exact (the spec's section 4.2). Anything else rejects the
    whole file: a parser that skipped what it did not recognise would let a
    signed file mean something its signer did not write.
    """
    if len(data) > MANIFEST_MAX_BYTES:
        raise UpdateVerificationError("the update manifest is too large")
    try:
        text = data.decode("ascii")
    except UnicodeDecodeError:
        raise UpdateVerificationError("the update manifest is not ASCII") from None
    if "\r" in text or not text.endswith("\n"):
        raise UpdateVerificationError("the update manifest has bad line endings")
    lines = text[:-1].split("\n")
    if len(lines) < 3 or lines[0] != MANIFEST_HEADER:
        raise UpdateVerificationError("the update manifest has no header")
    version = _VERSION_LINE_RE.fullmatch(lines[1])
    if version is None:
        raise UpdateVerificationError("the update manifest has no version")
    digests = {}
    for line in lines[2:]:
        asset = _ASSET_LINE_RE.fullmatch(line)
        if asset is None or asset.group(2) in digests:
            raise UpdateVerificationError(
                f"the update manifest has a bad line: {line[:80]!r}")
        digests[asset.group(2)] = asset.group(1)
    return version.group(1), digests


def _fetch_small(url, limit):
    with _open_https(url, UPDATE_CHECK_TIMEOUT_SEC) as resp:
        data = resp.read(limit + 1)
    if len(data) > limit:
        raise UpdateVerificationError(f"{url} is larger than {limit} bytes")
    return data


def _expected_digest(offer):
    """Fetch and verify the manifest; return this build's digest."""
    signature = _fetch_small(offer.signature_url, SIGNATURE_BYTES)
    manifest = _fetch_small(offer.manifest_url, MANIFEST_MAX_BYTES)
    try:
        public_key().verify(signature, manifest)
    except InvalidSignature:
        raise UpdateVerificationError(
            "the update manifest is not signed by the release key") from None
    version, digests = parse_manifest(manifest)
    # The version line is what stops an older release's correctly signed
    # manifest being replayed under a newer tag (INV-3).
    if version != offer.version or \
            _version_tuple(version) <= _version_tuple(__version__):
        raise UpdateVerificationError(
            f"the manifest is for {version}, not {offer.version}")
    if offer.asset_name not in digests:
        raise UpdateVerificationError(
            f"the manifest does not list {offer.asset_name}")
    return digests[offer.asset_name]


def _content_length(resp):
    value = resp.headers.get("Content-Length")
    return int(value) if value and value.isdigit() else None


def _fetch_build(offer, out, on_progress, cancelled):
    """Stream the build into `out`; return its SHA-256 hex digest."""
    digest = hashlib.sha256()
    written, last_report = 0, 0.0
    with _open_https(offer.asset_url, UPDATE_CHECK_TIMEOUT_SEC) as resp:
        total = _content_length(resp)
        if total is not None and total > UPDATE_MAX_BYTES:
            raise UpdateDownloadError("the update is far larger than expected")
        while True:
            if cancelled():
                raise UpdateCancelled()
            chunk = resp.read(YTDLP_CHUNK_BYTES)
            if not chunk:
                break
            written += len(chunk)
            if written > UPDATE_MAX_BYTES:
                raise UpdateDownloadError("the update is far larger than expected")
            digest.update(chunk)
            out.write(chunk)
            now = time.monotonic()
            if now - last_report >= DownloaderMixin.PROGRESS_THROTTLE_SEC:
                last_report = now
                on_progress(written, total)
    if total is not None and written < total:
        raise UpdateDownloadError(
            f"the download stopped at {written} of {total} bytes")
    on_progress(written, total)
    return digest.hexdigest()


def download_verified(offer, target_dir, on_progress, cancelled):
    """Download `offer`'s build into `target_dir`; return the verified file.

    `on_progress(done, total)` is called from this thread, at most every
    PROGRESS_THROTTLE_SEC; `total` is None when the server sent no length.
    `cancelled()` is checked between chunks. Raises an UpdateError subclass
    on any failure, having deleted its temp file.
    """
    try:
        expected = _expected_digest(offer)
    except _NETWORK_ERRORS as exc:
        raise UpdateDownloadError(str(exc)) from exc

    fd, temp_path = tempfile.mkstemp(prefix=".snatch-update-", dir=target_dir)
    verified = False
    try:
        with os.fdopen(fd, "wb") as out:
            actual = _fetch_build(offer, out, on_progress, cancelled)
        if actual != expected:
            raise UpdateVerificationError(
                f"the download does not match the signed manifest "
                f"(expected {expected[:16]}..., got {actual[:16]}...)")
        verified = True
        return temp_path
    except _NETWORK_ERRORS as exc:
        raise UpdateDownloadError(str(exc)) from exc
    finally:
        if not verified:
            try:
                os.unlink(temp_path)
            except OSError:
                log.warning("Could not remove %s", temp_path, exc_info=True)
