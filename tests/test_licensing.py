import pytest

from fileforge.licensing import (
    License,
    Tier,
    generate_keypair,
    issue_key,
    require,
    validate_key,
)


@pytest.fixture(scope="module")
def keypair():
    return generate_keypair()  # (private_b64, public_b64)


def test_free_when_no_key(keypair):
    _, pub = keypair
    lic = validate_key(None, public_key=pub)
    assert lic.tier is Tier.FREE
    assert lic.valid


def test_valid_pro_key_roundtrip(keypair):
    priv, pub = keypair
    key = issue_key(Tier.PRO, "order123", private_key=priv)
    assert key.startswith("FF2.")
    lic = validate_key(key, public_key=pub)
    assert lic.tier is Tier.PRO
    assert lic.valid
    assert lic.subject == "order123"


def test_subject_with_hyphens_and_email(keypair):
    priv, pub = keypair
    key = issue_key(Tier.ENTERPRISE, "big-co+team@example.com", private_key=priv)
    lic = validate_key(key, public_key=pub)
    assert lic.tier is Tier.ENTERPRISE
    assert lic.subject == "big-co+team@example.com"


def test_tampered_payload_rejected(keypair):
    priv, pub = keypair
    key = issue_key(Tier.PRO, "order123", private_key=priv)
    prefix, payload, sig = key.split(".")
    # Forge a different payload but keep the old signature.
    forged_payload = __import__("fileforge.licensing", fromlist=["_b64e"])._b64e(
        b'{"s":"x","t":"ENTERPRISE","v":2}'
    )
    forged = f"{prefix}.{forged_payload}.{sig}"
    lic = validate_key(forged, public_key=pub)
    assert lic.tier is Tier.FREE
    assert not lic.valid


def test_key_from_other_keypair_rejected(keypair):
    priv_a, _ = keypair
    _, pub_b = generate_keypair()          # different keypair
    key = issue_key(Tier.PRO, "x", private_key=priv_a)
    lic = validate_key(key, public_key=pub_b)   # verify with the wrong public key
    assert lic.tier is Tier.FREE
    assert not lic.valid


def test_no_public_key_configured_is_free(keypair):
    priv, _ = keypair
    key = issue_key(Tier.PRO, "x", private_key=priv)
    lic = validate_key(key, public_key="")   # nothing to verify against
    assert lic.tier is Tier.FREE
    assert not lic.valid


def test_require_never_blocks_free_tier():
    # FileForge is free: require() is a no-op and never raises, so every
    # feature is available even on the FREE tier.
    free = License(Tier.FREE, "anon", True)
    assert require(Tier.PRO, free).tier is Tier.FREE
    assert require(Tier.ENTERPRISE, free).tier is Tier.FREE


def test_require_passes_through_license(keypair):
    priv, pub = keypair
    ent = validate_key(issue_key(Tier.ENTERPRISE, "big-co", private_key=priv), public_key=pub)
    assert require(Tier.PRO, ent).tier is Tier.ENTERPRISE


def test_issue_without_signing_key_errors(monkeypatch):
    monkeypatch.delenv("FILEFORGE_PRIVATE_KEY", raising=False)
    with pytest.raises(RuntimeError):
        issue_key(Tier.PRO, "x")
