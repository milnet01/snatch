#!/usr/bin/env python3
"""Make the Snatch release signing key, once (SNAT-0038).

Usage:
    python3 scripts/gen-signing-key.py

Writes an unencrypted Ed25519 key to $SNATCH_SIGNING_KEY, by default
~/.config/snatch-release/signing.key, readable by you alone. Refuses to
overwrite one that exists: a new key would strand every installed copy.

Prints the public key and two self-test constants to paste into the
repository. It never prints the private key.
"""

import base64
import os
import sys
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

DEFAULT_KEY = Path("~/.config/snatch-release/signing.key").expanduser()
SELFTEST_MANIFEST = b"snatch selftest\n"


def key_path():
    return Path(os.environ.get("SNATCH_SIGNING_KEY") or DEFAULT_KEY)


def main():
    path = key_path()
    if path.exists():
        sys.exit(f"{path} already exists. Not overwriting it: a new key would "
                 "stop every installed Snatch accepting updates.")
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)

    key = Ed25519PrivateKey.generate()
    pem = key.private_bytes(serialization.Encoding.PEM,
                            serialization.PrivateFormat.PKCS8,
                            serialization.NoEncryption())
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(pem)
    del pem

    public = base64.b64encode(key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw)).decode()
    signature = base64.b64encode(key.sign(SELFTEST_MANIFEST)).decode()

    print(f"Wrote the signing key to {path}\n")
    print("In snatch/update_key.py:")
    print(f'RELEASE_PUBLIC_KEY_B64 = "{public}"\n')
    print("In snatch/selftest.py:")
    print(f"SELFTEST_MANIFEST = {SELFTEST_MANIFEST!r}")
    print(f'SELFTEST_SIGNATURE = "{signature}"\n')
    print("NOW copy the key to a second drive. If it is lost, no further\n"
          "release can be signed, and every installed copy has to be\n"
          "updated once by hand.")


if __name__ == "__main__":
    main()
