"""Tier + license gating with **asymmetric (Ed25519) license keys**.

The security model:

* The **license server** holds a secret Ed25519 *private* key
  (``FILEFORGE_PRIVATE_KEY``) and signs each purchase into a license key.
* Clients (CLI, GUI, Android, Magisk) only carry the *public* key and verify
  keys **offline** — no shared secret ships with the client, so nobody can
  forge keys by inspecting the distributed binary.

Key format (self-contained, offline-verifiable, JWT-like):

    FF2.<base64url(payload_json)>.<base64url(signature)>

where ``payload_json = {"t": TIER, "s": SUBJECT, "v": 2}`` and the signature
covers the payload segment. Verification needs no network and no lookup.

Generate a keypair with ``python scripts/keygen.py``. Put the private key in the
server's environment; embed the public key here (``EMBEDDED_PUBLIC_KEY``) or
ship it via ``FILEFORGE_PUBLIC_KEY``.
"""

from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from enum import IntEnum
from typing import Optional

from fileforge import _ed25519 as ed

# Public key embedded in the client. Replace with your own via
# `python scripts/keygen.py --write`. Empty means "not configured" — no key
# can be verified until you set one (or provide FILEFORGE_PUBLIC_KEY).
EMBEDDED_PUBLIC_KEY = "NqHY-gjx1rlhxIuKAwdt9nC92L8-39Rj6l7p-TFhaiM"


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
    subject: str
    valid: bool

    @property
    def name(self) -> str:
        return self.tier.name.lower()


# --------------------------------------------------------------------------- #
# base64url helpers (no padding, URL-safe — keeps keys hyphen/dot free inside
# each segment so the FF2.<payload>.<sig> split is unambiguous)
# --------------------------------------------------------------------------- #
def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64d(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


# --------------------------------------------------------------------------- #
# Keys
# --------------------------------------------------------------------------- #
def generate_keypair() -> tuple[str, str]:
    """Return (private_key_b64, public_key_b64). Keep the private key secret."""
    seed = ed.generate_seed()
    return _b64e(seed), _b64e(ed.publickey(seed))


def _public_key(explicit: Optional[str] = None) -> str:
    return explicit or os.environ.get("FILEFORGE_PUBLIC_KEY") or EMBEDDED_PUBLIC_KEY


def _private_key(explicit: Optional[str] = None) -> str:
    key = explicit or os.environ.get("FILEFORGE_PRIVATE_KEY")
    if not key:
        raise RuntimeError(
            "no signing key: set FILEFORGE_PRIVATE_KEY (or pass private_key). "
            "Generate one with `python scripts/keygen.py`."
        )
    return key


# --------------------------------------------------------------------------- #
# Issue / validate
# --------------------------------------------------------------------------- #
def issue_key(tier: Tier, subject: str, private_key: Optional[str] = None) -> str:
    """Sign a license key for ``tier``/``subject`` (server side)."""
    payload = _b64e(
        json.dumps({"t": tier.name, "s": subject, "v": 2},
                   separators=(",", ":"), sort_keys=True).encode()
    )
    seed = _b64d(_private_key(private_key))
    sig = ed.sign(seed, payload.encode("ascii"))
    return f"FF2.{payload}.{_b64e(sig)}"


def validate_key(key: Optional[str], public_key: Optional[str] = None) -> License:
    """Verify a license key offline. Returns a FREE license for anything that
    is absent, malformed, or fails signature verification."""
    if not key:
        return License(Tier.FREE, subject="anonymous", valid=True)
    pub = _public_key(public_key)
    if not pub:
        # No public key configured -> cannot trust any key -> FREE.
        return License(Tier.FREE, subject="anonymous", valid=False)
    try:
        prefix, payload_b64, sig_b64 = key.split(".")
        if prefix != "FF2":
            raise ValueError("bad prefix")
        if not ed.verify(_b64d(pub), payload_b64.encode("ascii"), _b64d(sig_b64)):
            raise ValueError("bad signature")
        data = json.loads(_b64d(payload_b64))
        tier = Tier.from_name(data["t"])
        return License(tier, subject=str(data.get("s", "")), valid=True)
    except (ValueError, KeyError, json.JSONDecodeError):
        return License(Tier.FREE, subject="anonymous", valid=False)


def current_license() -> License:
    """Resolve the active license from the environment (CLI/GUI/daemon)."""
    return validate_key(os.environ.get("FILEFORGE_LICENSE"))


def require(tier: Tier, license: License | None = None) -> License:
    # FileForge is free: every feature is unlocked for everyone. This stays a
    # no-op (never raises) so the dormant licensing code and all call sites keep
    # working unchanged. To gate features again, restore the tier check:
    #     lic = license or current_license()
    #     if lic.tier < tier: raise PermissionError(...)
    #     return lic
    return license or current_license()
