import pytest

from fileforge.licensing import (
    License,
    Tier,
    issue_key,
    require,
    validate_key,
)


def test_free_when_no_key():
    lic = validate_key(None)
    assert lic.tier is Tier.FREE
    assert lic.valid


def test_valid_pro_key():
    key = issue_key(Tier.PRO, "order123")
    lic = validate_key(key)
    assert lic.tier is Tier.PRO
    assert lic.valid


def test_tampered_key_downgrades_to_free():
    key = issue_key(Tier.ENTERPRISE, "order999")
    tampered = key[:-1] + ("0" if key[-1] != "0" else "1")
    lic = validate_key(tampered)
    assert lic.tier is Tier.FREE
    assert not lic.valid


def test_require_blocks_lower_tier():
    free = License(Tier.FREE, "anon", True)
    with pytest.raises(PermissionError):
        require(Tier.PRO, free)


def test_require_allows_equal_or_higher():
    ent = validate_key(issue_key(Tier.ENTERPRISE, "big-co"))
    assert require(Tier.PRO, ent).tier is Tier.ENTERPRISE
