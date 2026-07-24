import hashlib
import os
import sys
from pathlib import Path

import pytest

# Make both the server app and the shared engine importable.
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "license-server"))
sys.path.insert(0, str(ROOT / "src"))

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture()
def client(tmp_path, monkeypatch):
    # A signing keypair for the server: private key signs, public key verifies.
    sys.path.insert(0, str(ROOT / "src"))
    from fileforge.licensing import generate_keypair
    priv, pub = generate_keypair()
    monkeypatch.setenv("FILEFORGE_PRIVATE_KEY", priv)
    monkeypatch.setenv("FILEFORGE_PUBLIC_KEY", pub)
    monkeypatch.setenv("FF_LICENSE_DB", str(tmp_path / "lic.db"))
    monkeypatch.setenv("FF_PRODUCT_MAP", "pro-desktop=pro,cloud-lifetime=cloud")
    monkeypatch.setenv("GUMROAD_SELLER_ID", "seller-123")
    monkeypatch.setenv("PAYHIP_SECRET", "shh")
    monkeypatch.setenv("FF_ADMIN_TOKEN", "admin-secret")
    # Both cloud-api and license-server ship a package named `app`; evict any
    # cached one and force this service's path first so we import the right one.
    for mod in [m for m in list(sys.modules) if m == "app" or m.startswith("app.")]:
        del sys.modules[mod]
    sys.path.insert(0, str(ROOT / "license-server"))
    from app.main import app
    return TestClient(app)


def test_health(client):
    assert client.get("/healthz").json()["status"] == "ok"


def test_gumroad_sale_issues_pro_key(client):
    r = client.post("/webhook/gumroad", data={
        "sale_id": "S1", "seller_id": "seller-123",
        "product_permalink": "pro-desktop", "email": "buyer@example.com",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["tier"] == "pro"
    assert body["key"].startswith("FF2.")

    # The issued key verifies as Pro.
    v = client.get(f"/license/{body['key']}")
    assert v.json()["valid"] is True
    assert v.json()["tier"] == "pro"


def test_gumroad_bad_seller_rejected(client):
    r = client.post("/webhook/gumroad", data={
        "sale_id": "S2", "seller_id": "attacker",
        "product_permalink": "pro-desktop", "email": "x@example.com",
    })
    assert r.status_code == 403


def test_duplicate_delivery_is_idempotent(client):
    data = {"sale_id": "S3", "seller_id": "seller-123",
            "product_permalink": "cloud-lifetime", "email": "c@example.com"}
    k1 = client.post("/webhook/gumroad", data=data).json()["key"]
    k2 = client.post("/webhook/gumroad", data=data).json()["key"]
    assert k1 == k2  # same sale -> same key, not a second license


def test_payhip_signature_verified(client):
    fields = {"id": "P1", "product_permalink": "pro-desktop", "email": "p@example.com"}
    parts = "".join(str(v) for _, v in sorted(fields.items()))
    fields["signature"] = hashlib.md5((parts + "shh").encode()).hexdigest()
    r = client.post("/webhook/payhip", data=fields)
    assert r.status_code == 200
    assert r.json()["tier"] == "pro"


def test_revoke_flow(client):
    key = client.post("/webhook/gumroad", data={
        "sale_id": "S4", "seller_id": "seller-123",
        "product_permalink": "pro-desktop", "email": "r@example.com",
    }).json()["key"]
    # revoke requires admin token
    assert client.post("/admin/revoke", data={"key": key}).status_code == 401
    ok = client.post("/admin/revoke", data={"key": key},
                     headers={"X-Admin-Token": "admin-secret"})
    assert ok.json()["revoked"] is True
    # now it verifies as revoked/free
    v = client.get(f"/license/{key}").json()
    assert v["revoked"] is True and v["valid"] is False


def test_admin_manual_issue(client):
    r = client.post("/admin/issue",
                    data={"tier": "enterprise", "email": "e@corp.com", "sale_id": "M1"},
                    headers={"X-Admin-Token": "admin-secret"})
    assert r.json()["tier"] == "enterprise"
    assert r.json()["key"].startswith("FF2.")
