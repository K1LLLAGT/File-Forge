"""Purchase-provider verification + product→tier mapping.

Two providers are supported out of the box:

* **Gumroad** — the "Ping"/webhook posts form-encoded sale data with no
  signature, so the trustworthy check is to re-verify the sale against the
  Gumroad API using your access token. If no token is configured we fall back
  to a shared-secret compare on the `seller_id` (set GUMROAD_SELLER_ID).

* **Payhip** — posts a `signature` that is the MD5 of the item/buyer fields
  concatenated with your secret key; we recompute and compare.

Product → tier mapping is driven by env so you never touch code to add a SKU:

    FF_PRODUCT_MAP="pro-desktop=pro,cloud-lifetime=cloud,enterprise=enterprise"
"""

from __future__ import annotations

import hashlib
import os
import urllib.parse
import urllib.request
from typing import Dict, Optional


def product_map() -> Dict[str, str]:
    raw = os.environ.get("FF_PRODUCT_MAP", "")
    mapping: Dict[str, str] = {}
    for pair in raw.split(","):
        pair = pair.strip()
        if "=" in pair:
            product, tier = pair.split("=", 1)
            mapping[product.strip()] = tier.strip().lower()
    return mapping


def tier_for_product(product: str) -> Optional[str]:
    return product_map().get(product)


# --------------------------------------------------------------------------- #
# Gumroad
# --------------------------------------------------------------------------- #
def verify_gumroad(form: Dict[str, str]) -> bool:
    """Confirm the sale is real. Prefer an API re-check; fall back to seller_id."""
    token = os.environ.get("GUMROAD_ACCESS_TOKEN")
    sale_id = form.get("sale_id", "")
    if token and sale_id:
        try:
            return _gumroad_api_confirms(sale_id, token)
        except Exception:
            return False
    expected_seller = os.environ.get("GUMROAD_SELLER_ID")
    if expected_seller:
        return form.get("seller_id") == expected_seller
    # No verification configured -> refuse rather than trust blindly.
    return False


def _gumroad_api_confirms(sale_id: str, token: str) -> bool:  # pragma: no cover - network
    url = f"https://api.gumroad.com/v2/sales/{urllib.parse.quote(sale_id)}"
    req = urllib.request.Request(url + f"?access_token={urllib.parse.quote(token)}")
    with urllib.request.urlopen(req, timeout=10) as resp:
        import json
        data = json.loads(resp.read().decode())
    return bool(data.get("success")) and data.get("sale", {}).get("id") == sale_id


# --------------------------------------------------------------------------- #
# Payhip
# --------------------------------------------------------------------------- #
def verify_payhip(form: Dict[str, str]) -> bool:
    secret = os.environ.get("PAYHIP_SECRET")
    signature = form.get("signature")
    if not secret or not signature:
        return False
    # Payhip signs the concatenation of the sorted non-signature values + secret.
    parts = [str(v) for k, v in sorted(form.items()) if k != "signature"]
    expected = hashlib.md5(("".join(parts) + secret).encode()).hexdigest()
    return _consteq(expected, signature)


def _consteq(a: str, b: str) -> bool:
    import hmac
    return hmac.compare_digest(a, b)
