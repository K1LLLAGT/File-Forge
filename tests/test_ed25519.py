"""Pin the vendored Ed25519 to the RFC 8032 Section 7.1 Test 1 vector, so we
know it is genuine Ed25519 and not merely self-consistent."""

from fileforge import _ed25519 as ed

# RFC 8032, Section 7.1, TEST 1 (empty message).
SEED = bytes.fromhex("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60")
PUBKEY = bytes.fromhex("d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a")
SIG = bytes.fromhex(
    "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901"
    "555fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b"
)


def test_rfc8032_public_key():
    assert ed.publickey(SEED) == PUBKEY


def test_rfc8032_signature():
    assert ed.sign(SEED, b"") == SIG


def test_verify_accepts_valid():
    assert ed.verify(PUBKEY, b"", SIG) is True


def test_verify_rejects_tampered_message():
    assert ed.verify(PUBKEY, b"tampered", SIG) is False


def test_verify_rejects_bad_lengths():
    assert ed.verify(b"short", b"", SIG) is False
    assert ed.verify(PUBKEY, b"", b"short") is False


def test_roundtrip_random():
    seed = ed.generate_seed()
    pk = ed.publickey(seed)
    sig = ed.sign(seed, b"hello world")
    assert ed.verify(pk, b"hello world", sig)
    assert not ed.verify(pk, b"hello worlD", sig)
