#!/usr/bin/env python3
"""Sign a draft Snatch release and publish it (SNAT-0038).

Usage:
    python3 scripts/sign-release.py vX.Y.Z

CI publishes each tagged release as a draft. This runs on the maintainer's
PC, where the key is: it checks the draft's assets against its SHA256SUMS,
writes and signs SNATCH-UPDATE, verifies the signature with the public key
committed in snatch/update_key.py, uploads both files, publishes, and then
downloads them back and verifies them again.

The key is read from $SNATCH_SIGNING_KEY, by default
~/.config/snatch-release/signing.key. Needs `gh`, signed in.
"""

import hashlib
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from snatch.self_update import (MANIFEST_ASSET, MANIFEST_HEADER,
                                SIGNATURE_ASSET, parse_manifest)
from snatch.update_key import public_key
from snatch.version import SNATCH_TAG_RE

REPO = "milnet01/snatch"
DEFAULT_KEY = Path("~/.config/snatch-release/signing.key").expanduser()
SUMS = "SHA256SUMS"
# One of each, as the release job in .github/workflows/ci.yml attaches them.
PLATFORM_ASSETS = (re.compile(r"Snatch-[A-Za-z0-9_]+\.AppImage"),
                   re.compile(r"snatch\.exe"),
                   re.compile(r"Snatch-[A-Za-z0-9_]+\.dmg"))
SUMS_LINE_RE = re.compile(r"([0-9a-f]{64})  (\S+)")
# The three builds are some 150 MB each.
GH_DOWNLOAD_TIMEOUT_SEC = 1800
GH_TIMEOUT_SEC = 120
HASH_CHUNK_BYTES = 1024 * 1024


def fail(message):
    sys.exit(f"sign-release: {message}")


def gh(*args, timeout=GH_TIMEOUT_SEC):
    try:
        subprocess.run(["gh", *args, "--repo", REPO], check=True,
                       timeout=timeout)
    except subprocess.CalledProcessError as exc:
        fail(f"gh {' '.join(args[:2])} failed with status {exc.returncode}")
    except subprocess.TimeoutExpired:
        fail(f"gh {' '.join(args[:2])} did not finish in {timeout}s")


def download(tag, folder, *names):
    patterns = [arg for name in names for arg in ("--pattern", name)]
    gh("release", "download", tag, *patterns, "--dir", str(folder),
       timeout=GH_DOWNLOAD_TIMEOUT_SEC)


def read_key():
    path = Path(os.environ.get("SNATCH_SIGNING_KEY") or DEFAULT_KEY)
    if not path.is_file():
        fail(f"no signing key at {path}. Restore it from your backup. Do not "
             "make a new one: installed copies only accept the old key.")
    key = serialization.load_pem_private_key(path.read_bytes(), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        fail(f"{path} is not an Ed25519 key")
    return key


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while chunk := handle.read(HASH_CHUNK_BYTES):
            digest.update(chunk)
    return digest.hexdigest()


def checked_sums(folder):
    """SHA256SUMS's lines, once it names exactly the platform assets."""
    lines = (folder / SUMS).read_text(encoding="ascii").splitlines()
    entries = [SUMS_LINE_RE.fullmatch(line) for line in lines]
    if None in entries or len(entries) != len(PLATFORM_ASSETS):
        fail(f"{SUMS} is not exactly {len(PLATFORM_ASSETS)} checksum lines")
    names = [entry.group(2) for entry in entries]
    for pattern in PLATFORM_ASSETS:
        if sum(1 for name in names if pattern.fullmatch(name)) != 1:
            fail(f"{SUMS} does not list exactly one {pattern.pattern}")
    return [(entry.group(1), entry.group(2)) for entry in entries]


def verify(manifest, signature, version):
    try:
        public_key().verify(signature, manifest)
    except InvalidSignature:
        fail("the signature does not match the public key committed in "
             "snatch/update_key.py, so nothing was uploaded. Is "
             "SNATCH_SIGNING_KEY the release key?")
    if parse_manifest(manifest)[0] != version:
        fail(f"{MANIFEST_ASSET} does not name {version}")


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    tag = sys.argv[1]
    match = SNATCH_TAG_RE.match(tag)
    if match is None:
        fail(f"{tag!r} is not a vX.Y.Z tag")
    version = ".".join(match.groups())
    key = read_key()

    with tempfile.TemporaryDirectory(prefix="snatch-sign-") as work:
        work = Path(work)
        download(tag, work, SUMS)
        sums = checked_sums(work)
        download(tag, work, *(name for _digest, name in sums))
        for digest, name in sums:
            if sha256_file(work / name) != digest:
                fail(f"{name} does not match {SUMS}")

        lines = [MANIFEST_HEADER, f"version {version}"]
        lines += [f"{digest}  {name}" for digest, name in sums]
        manifest = ("\n".join(lines) + "\n").encode("ascii")
        signature = key.sign(manifest)
        verify(manifest, signature, version)

        (work / MANIFEST_ASSET).write_bytes(manifest)
        (work / SIGNATURE_ASSET).write_bytes(signature)
        gh("release", "upload", tag, str(work / MANIFEST_ASSET),
           str(work / SIGNATURE_ASSET), "--clobber")
        gh("release", "edit", tag, "--draft=false")

        back = work / "published"
        download(tag, back, MANIFEST_ASSET, SIGNATURE_ASSET)
        published = (back / MANIFEST_ASSET).read_bytes()
        if published != manifest:
            fail(f"the published {MANIFEST_ASSET} differs from what was signed")
        verify(published, (back / SIGNATURE_ASSET).read_bytes(), version)

    print(f"Signed and published {tag}; the published files verify.")


if __name__ == "__main__":
    main()
