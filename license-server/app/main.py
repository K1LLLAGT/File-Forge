"""FileForge License Server (monetization strategies #1, #6, #7, #8, #10).

Receives purchase webhooks from Gumroad / Payhip, verifies them, mints a
signed FileForge license key for the mapped tier, stores it, and (optionally)
emails it to the buyer. Buyers and your support tooling can re-fetch or verify
keys through the read endpoints.

Endpoints
    POST /webhook/gumroad   Gumroad Ping/webhook (form-encoded)
    POST /webhook/payhip    Payhip webhook (form-encoded)
    GET  /license/{key}     verify a key (valid / tier / revoked)
    POST /admin/revoke      revoke a key (X-Admin-Token)
    POST /admin/issue       manually mint a key (X-Admin-Token)
    GET  /healthz

Run:
    pip install -e '.[cloud]'
    export FF_PRODUCT_MAP="pro-desktop=pro,cloud-lifetime=cloud"
    export GUMROAD_ACCESS_TOKEN=...        # or GUMROAD_SELLER_ID for fallback
    uvicorn app.main:app --port 8080       # from license-server/
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Reuse the engine's signing logic so server-issued keys validate in the CLI.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from fastapi import Depends, FastAPI, Form, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from fileforge.licensing import Tier, issue_key, validate_key

from .emailer import send_license_email
from .providers import tier_for_product, verify_gumroad, verify_payhip
from .store import LicenseRecord, LicenseStore, now

app = FastAPI(title="FileForge License Server", version="1.0.0")
store = LicenseStore(os.environ.get("FF_LICENSE_DB", "licenses.db"))


def _admin(x_admin_token: str | None = Header(default=None)) -> None:
    expected = os.environ.get("FF_ADMIN_TOKEN")
    if not expected or x_admin_token != expected:
        raise HTTPException(status_code=401, detail="bad admin token")


def _fulfill(
    provider: str,
    sale_id: str,
    product: str,
    email: str,
    tier_override: str | None = None,
) -> LicenseRecord:
    """Idempotently mint + persist a key for a verified sale."""
    existing = store.get_by_sale(sale_id)
    if existing:
        return existing  # duplicate webhook delivery -> return the same key

    tier_name = tier_override or tier_for_product(product)
    if tier_name is None:
        raise HTTPException(status_code=422, detail=f"no tier mapped for product '{product}'")
    try:
        tier = Tier.from_name(tier_name)
    except KeyError:
        raise HTTPException(status_code=500, detail=f"invalid tier mapping '{tier_name}'")

    subject = email or sale_id
    key = issue_key(tier, subject)
    rec = LicenseRecord(sale_id, provider, tier.name.lower(), email, key, now())
    store.upsert(rec)
    if email:
        send_license_email(email, key, tier.name.lower())
    return rec


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


@app.post("/webhook/gumroad")
async def gumroad_webhook(request: Request) -> JSONResponse:
    form = {k: str(v) for k, v in (await request.form()).items()}
    if not verify_gumroad(form):
        raise HTTPException(status_code=403, detail="gumroad verification failed")
    rec = _fulfill(
        "gumroad",
        sale_id=form.get("sale_id", ""),
        product=form.get("product_permalink") or form.get("product_id", ""),
        email=form.get("email", ""),
    )
    return JSONResponse({"ok": True, "tier": rec.tier, "key": rec.key})


@app.post("/webhook/payhip")
async def payhip_webhook(request: Request) -> JSONResponse:
    form = {k: str(v) for k, v in (await request.form()).items()}
    if not verify_payhip(form):
        raise HTTPException(status_code=403, detail="payhip verification failed")
    rec = _fulfill(
        "payhip",
        sale_id=form.get("id") or form.get("transaction_id", ""),
        product=form.get("product_permalink") or form.get("product_id", ""),
        email=form.get("email", ""),
    )
    return JSONResponse({"ok": True, "tier": rec.tier, "key": rec.key})


@app.get("/license/{key}")
def verify(key: str) -> dict:
    lic = validate_key(key)
    rec = store.get_by_key(key)
    revoked = bool(rec and rec.revoked)
    return {
        "key": key,
        "valid": lic.valid and not revoked,
        "tier": "free" if revoked else lic.name,
        "revoked": revoked,
        "known": rec is not None,
    }


@app.post("/admin/revoke")
def revoke(key: str = Form(...), _: None = Depends(_admin)) -> dict:
    return {"revoked": store.revoke(key)}


@app.post("/admin/issue")
def admin_issue(
    tier: str = Form(...),
    email: str = Form(...),
    sale_id: str = Form(...),
    _: None = Depends(_admin),
) -> dict:
    rec = _fulfill("manual", sale_id=sale_id, product="__manual__",
                   email=email, tier_override=tier.lower())
    return {"key": rec.key, "tier": rec.tier}
