#!/usr/bin/env python3
"""Generate a FileForge Ed25519 license keypair.

    python scripts/keygen.py            # print a new keypair + next steps
    python scripts/keygen.py --write    # also embed the PUBLIC key in the CLI

- The **private** key is your signing secret. Put it in the license server's
  environment as FILEFORGE_PRIVATE_KEY. Never commit it or ship it to clients.
- The **public** key is safe to distribute. Embed it in the client
  (EMBEDDED_PUBLIC_KEY in src/fileforge/licensing.py) or set FILEFORGE_PUBLIC_KEY.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fileforge.licensing import generate_keypair  # noqa: E402

LICENSING = ROOT / "src" / "fileforge" / "licensing.py"


def embed_public_key(pub: str) -> None:
    text = LICENSING.read_text(encoding="utf-8")
    new, n = re.subn(
        r'^EMBEDDED_PUBLIC_KEY = ".*"$',
        f'EMBEDDED_PUBLIC_KEY = "{pub}"',
        text,
        flags=re.MULTILINE,
    )
    if n != 1:
        raise SystemExit("could not locate EMBEDDED_PUBLIC_KEY line to patch")
    LICENSING.write_text(new, encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate a FileForge license keypair")
    ap.add_argument("--write", action="store_true",
                    help="embed the public key into src/fileforge/licensing.py")
    args = ap.parse_args()

    private_key, public_key = generate_keypair()

    print("# ---- FileForge license keypair ----")
    print("# PRIVATE (server secret — set as FILEFORGE_PRIVATE_KEY, keep safe):")
    print(private_key)
    print("# PUBLIC (safe to distribute — embed in the client):")
    print(public_key)
    print()
    print("Next steps:")
    print("  1. Server:  export FILEFORGE_PRIVATE_KEY='<private above>'")
    print("  2. Client:  set EMBEDDED_PUBLIC_KEY (or FILEFORGE_PUBLIC_KEY) to the public key")
    if args.write:
        embed_public_key(public_key)
        print(f"\nEmbedded the public key into {LICENSING.relative_to(ROOT)}")
    else:
        print("     (re-run with --write to embed the public key automatically)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
