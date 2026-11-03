"""The public half of the key every Snatch release is signed with (SNAT-0038).

The private half lives only on the maintainer's PC, outside the repository,
and is made once by scripts/gen-signing-key.py. An update is installed only
when its manifest verifies against this key.

Changing this value is a key rotation, and this spec does not support one:
every installed copy would refuse every later update and would have to be
updated once by hand. tests/test_update_key.py goes red when it changes.
"""

import base64

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

# The raw 32-byte Ed25519 public key, base64. gen-signing-key.py prints it.
RELEASE_PUBLIC_KEY_B64 = "eICOEpgEsLwFPVaVy0P+JSByTNKzrNPH20m/9/I7/oI="


def public_key():
    """The release key, ready to verify a signature."""
    return Ed25519PublicKey.from_public_bytes(
        base64.b64decode(RELEASE_PUBLIC_KEY_B64, validate=True))
