"""The committed release key verifies the self-test fixture (SNAT-0038 INV-13).

The fixture was signed by the private key when it was made, so this goes red
the moment RELEASE_PUBLIC_KEY_B64 changes. A changed key strands every
installed copy (the spec's section 6), so that should never be quiet.
"""

import base64

from snatch import selftest, update_key


def test_committed_key_verifies_the_fixture():
    update_key.public_key().verify(
        base64.b64decode(selftest.SELFTEST_SIGNATURE, validate=True),
        selftest.SELFTEST_MANIFEST)


def test_the_key_is_a_raw_ed25519_key():
    assert len(base64.b64decode(update_key.RELEASE_PUBLIC_KEY_B64,
                                validate=True)) == 32
