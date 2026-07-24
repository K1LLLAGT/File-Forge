"""FileForge Cloud Conversion API (monetization strategy #3 + #7).

REST surface:
    POST /v1/convert     upload a file, convert server-side, return the result
    GET  /v1/formats     list supported (source -> target) routes
    GET  /v1/usage       remaining quota for the caller's API key
    GET  /healthz        liveness

Auth is by ``X-API-Key`` header. Metering is pluggable; the default in-memory
meter is fine for local dev and demos, and swaps for Redis/Postgres in prod
(Cloudflare Workers KV, Fly.io + Upstash, Railway + Postgres).

Run locally:
    pip install -e '.[cloud]'
    uvicorn app.main:app --reload   # from the cloud-api/ directory
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

# Make the shared conversion engine importable from the sibling src/ tree.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from fileforge.core.registry import ConversionError, load_builtin_converters, registry

from .metering import Meter, Plan

app = FastAPI(title="FileForge Cloud API", version="1.0.0")
meter = Meter()


@app.on_event("startup")
def _startup() -> None:
    load_builtin_converters()
    # Demo keys mirroring the pricing tiers. Replace with a real key store.
    meter.register_key("demo-metered", Plan.METERED)     # $5 / 500 conv
    meter.register_key("demo-lifetime", Plan.LIFETIME)   # $49 unlimited
    meter.register_key("demo-enterprise", Plan.ENTERPRISE)  # $199/yr


def require_key(x_api_key: str | None = Header(default=None)) -> str:
    if not x_api_key or not meter.known(x_api_key):
        raise HTTPException(status_code=401, detail="missing or invalid X-API-Key")
    return x_api_key


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok", "routes": len(registry.routes())}


@app.get("/v1/formats")
def formats() -> JSONResponse:
    data = [
        {"source": c.source_ext, "target": c.target_ext, "tier": c.tier,
         "available": c.available()}
        for c in registry.routes()
    ]
    return JSONResponse({"count": len(data), "routes": data})


@app.get("/v1/usage")
def usage(api_key: str = Depends(require_key)) -> dict:
    return meter.snapshot(api_key)


@app.post("/v1/convert")
def convert(
    target: str,
    file: UploadFile = File(...),
    api_key: str = Depends(require_key),
) -> FileResponse:
    if not meter.allow(api_key):
        raise HTTPException(status_code=429, detail="conversion quota exhausted")

    src_ext = Path(file.filename or "").suffix.lstrip(".").lower()
    tgt_ext = target.lstrip(".").lower()
    conv = registry.get(src_ext, tgt_ext)
    if conv is None:
        raise HTTPException(status_code=422, detail=f"no route {src_ext}->{tgt_ext}")
    if not conv.available():
        raise HTTPException(status_code=501, detail=f"route needs deps: {conv.requires}")

    workdir = Path(tempfile.mkdtemp(prefix="ff-"))
    src_path = workdir / f"in.{src_ext}"
    dst_path = workdir / f"out.{tgt_ext}"
    src_path.write_bytes(file.file.read())
    try:
        conv.fn(src_path, dst_path)
    except ConversionError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    meter.record(api_key)
    return FileResponse(
        dst_path,
        filename=f"{Path(file.filename or 'file').stem}.{tgt_ext}",
        media_type="application/octet-stream",
    )
