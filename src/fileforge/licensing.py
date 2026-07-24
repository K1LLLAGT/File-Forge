"""Tier + license gating.

FileForge uses offline, signed license keys so Pro/Enterprise features work
without phoning home. A key is ``FF-<TIER>-<PAYLOAD>-<SIG>`` where SIG is an
HMAC-SHA256 truncation over the payload using the product's public signing
salt. This module only *validates* keys; key issuance lives in the Gumroad /
license-server tooling under ``scripts/``.

The scheme here is intentionally simple and self-contained so the repo runs
end-to-end. For production you would swap ``_PRODUCT_SALT`` for an
environment-provided secret and issue keys from the license server.
"""

from __future__ import annotations

import hashlib
import hmac
import os
from dataclasses import dataclass
from enum import IntEnum

_PRODUCT_SALT = os.environ.get("FILEFORGE_SALT", "fileforge-demo-salt").encode()


class Tier(IntEnum):
    FREE = 0
    PRO = 1
    CLOUD = 2
    ENTERPRISE = 3

    @classmethod
    def from_name(cls, name: str) -> "Tier":
        return cls[name.strip().upper()]


@dataclass(frozen=True)
class License:
    tier: Tier
    subject: str  # e.g. buyer email or order id
    valid: bool

    @property
    def name(self) -> str:
        return self.tier.name.lower()


def _sign(payload: str) -> str:
    return hmac.new(_PRODUCT_SALT, payload.encode(), hashlib.sha256).hexdigest()[:16]


def issue_key(tier: Tier, subject: str) -> str:
    """Used by the license server / test suite to mint a valid key."""
    payload = f"{tier.name}:{subject}"
    return f"FF-{tier.name}-{subject}-{_sign(payload)}"


def validate_key(key: str | None) -> License:
    if not key:
        return License(Tier.FREE, subject="anonymous", valid=True)
    # Format: FF-<TIER>-<SUBJECT>-<SIG>. SUBJECT may contain hyphens, so peel
    # the prefix + tier off the left and the signature off the right.
    if not key.startswith("FF-"):
        return License(Tier.FREE, subject="anonymous", valid=False)
    try:
        tier_name, remainder = key[3:].split("-", 1)
        subject, sig = remainder.rsplit("-", 1)
    except ValueError:
        return License(Tier.FREE, subject="anonymous", valid=False)
    try:
        tier = Tier.from_name(tier_name)
    except KeyError:
        return License(Tier.FREE, subject="anonymous", valid=False)
    expected = _sign(f"{tier.name}:{subject}")
    ok = hmac.compare_digest(expected, sig)
    return License(tier if ok else Tier.FREE, subject=subject, valid=ok)


def current_license() -> License:
    """Resolve the active license from the environment (CLI/GUI/daemon)."""
    return validate_key(os.environ.get("FILEFORGE_LICENSE"))


def require(tier: Tier, license: License | None = None) -> License:
    lic = license or current_license()
    if lic.tier < tier:
        raise PermissionError(
            f"this feature requires the {tier.name.title()} tier; "
            f"active tier is {lic.tier.name.title()}. "
            "Set FILEFORGE_LICENSE with a valid key."
        )
    return lic
