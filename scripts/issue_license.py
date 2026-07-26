#!/usr/bin/env python3
"""Mint a signed FileForge license key. Wire this to a Gumroad/Payhip purchase
webhook (or run it manually) to fulfill orders.

Requires the signing key: set FILEFORGE_PRIVATE_KEY in the environment, or pass
--private-key. Generate a keypair with `python scripts/keygen.py`.

    export FILEFORGE_PRIVATE_KEY="<from keygen>"
    python scripts/issue_license.py --tier pro --subject buyer@example.com
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fileforge.licensing import Tier, issue_key


def main() -> int:
    ap = argparse.ArgumentParser(description="Issue a FileForge license key")
    ap.add_argument("--tier", required=True, choices=[t.name.lower() for t in Tier])
    ap.add_argument("--subject", required=True, help="order id or buyer email")
    ap.add_argument("--private-key", default=None,
                    help="signing key (else read from FILEFORGE_PRIVATE_KEY)")
    args = ap.parse_args()
    print(issue_key(Tier.from_name(args.tier), args.subject, private_key=args.private_key))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
