import io
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "cloud-api"))
sys.path.insert(0, str(ROOT / "src"))

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture()
def client():
    # Both cloud-api and license-server ship a package named `app`; evict any
    # cached one and force this service's path first so we import the right one.
    for mod in [m for m in list(sys.modules) if m == "app" or m.startswith("app.")]:
        del sys.modules[mod]
    sys.path.insert(0, str(ROOT / "cloud-api"))
    from app.main import app
    # Context manager so FastAPI startup events fire (loads converters + keys).
    with TestClient(app) as c:
        yield c


def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_formats_lists_routes(client):
    r = client.get("/v1/formats")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] > 0
    assert any(rt["source"] == "json" and rt["target"] == "csv" for rt in body["routes"])


def test_convert_requires_api_key(client):
    r = client.post("/v1/convert?target=csv",
                    files={"file": ("d.json", b"[{\"a\":1}]", "application/json")})
    assert r.status_code == 401


def test_convert_json_to_csv(client):
    r = client.post(
        "/v1/convert?target=csv",
        headers={"X-API-Key": "demo-lifetime"},
        files={"file": ("d.json", b"[{\"a\":1,\"b\":2}]", "application/json")},
    )
    assert r.status_code == 200
    assert b"a,b" in r.content
    assert b"1,2" in r.content


def test_usage_reports_after_conversion(client):
    client.post("/v1/convert?target=csv",
                headers={"X-API-Key": "demo-metered"},
                files={"file": ("d.json", b"[{\"a\":1}]", "application/json")})
    r = client.get("/v1/usage", headers={"X-API-Key": "demo-metered"})
    body = r.json()
    assert body["plan"] == "metered"
    assert body["used"] >= 1
    assert body["quota"] == 500


def test_unknown_route_422(client):
    r = client.post("/v1/convert?target=xyz",
                    headers={"X-API-Key": "demo-lifetime"},
                    files={"file": ("d.json", b"[]", "application/json")})
    assert r.status_code == 422
