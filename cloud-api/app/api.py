"""Cloud Conversion API — core endpoints.

POST /v1/convert — convert a file
GET /v1/formats — list available formats
GET /v1/usage — show current API key usage
GET /v1/account — show account tier and limits
GET /healthz — health check
"""

from __future__ import annotations

import time
from typing import Optional

from fastapi import APIRouter, File, HTTPException, Header, UploadFile, Query
from pydantic import BaseModel

from fileforge.core.registry import ConversionError, registry, load_builtin_converters


router = APIRouter(prefix="/v1", tags=["v1"])

# Placeholder metering store (in production, use Redis/Postgres)
_metering = {}  # key -> {conversions: int, bytes_in: int, bytes_out: int, last_reset: time}


class FormatRoute(BaseModel):
    source: str
    target: str
    description: str
    tier: str
    available: bool


class UsageInfo(BaseModel):
    api_key: str
    conversions: int
    bytes_in: int
    bytes_out: int
    tier: str


class AccountInfo(BaseModel):
    api_key: str
    tier: str
    conversions_limit: Optional[int]
    bytes_limit: Optional[int]
    reset_date: Optional[str]


def _get_or_init_api_key(api_key: str) -> dict:
    """Initialize metering for a new API key."""
    if api_key not in _metering:
        _metering[api_key] = {
            "conversions": 0,
            "bytes_in": 0,
            "bytes_out": 0,
            "last_reset": time.time(),
            "tier": "metered",  # Would resolve from DB in production
        }
    return _metering[api_key]


@router.post("/convert", responses={200: {"description": "Converted file"}}, status_code=200)
async def convert(
    file: UploadFile = File(...),
    target: str = Query(..., description="Target format (e.g., 'png', 'json')"),
    api_key: str = Header(..., description="API key for authentication"),
) -> dict:
    """Convert an uploaded file to a target format."""
    load_builtin_converters()
    
    if not api_key or not api_key.startswith(("demo-", "key_")):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    
    metrics = _get_or_init_api_key(api_key)
    
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    # Parse source format from filename
    source_ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if not source_ext:
        raise HTTPException(status_code=400, detail="File must have an extension")
    
    target_ext = target.lower().lstrip(".")
    
    # Check if converter exists
    conv = registry.get(source_ext, target_ext)
    if not conv:
        raise HTTPException(
            status_code=400,
            detail=f"No converter for {source_ext} -> {target_ext}",
        )
    
    if not conv.available():
        raise HTTPException(
            status_code=400,
            detail=f"Converter needs: {', '.join(conv.requires)}",
        )
    
    # Read file
    try:
        file_content = await file.read()
        if not file_content:
            raise HTTPException(status_code=400, detail="File is empty")
        if len(file_content) > 500 * 1024 * 1024:  # 500MB limit
            raise HTTPException(status_code=413, detail="File too large (max 500MB)")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {exc}")
    
    # Convert
    import tempfile
    from pathlib import Path
    try:
        with tempfile.NamedTemporaryFile(suffix=f".{source_ext}", delete=False) as src_tmp:
            src_path = Path(src_tmp.name)
            src_tmp.write(file_content)
        
        with tempfile.NamedTemporaryFile(suffix=f".{target_ext}", delete=False) as dst_tmp:
            dst_path = Path(dst_tmp.name)
        
        # Run conversion
        conv.fn(src_path, dst_path)
        
        # Read result
        result_content = dst_path.read_bytes()
        
        # Update metrics
        metrics["conversions"] += 1
        metrics["bytes_in"] += len(file_content)
        metrics["bytes_out"] += len(result_content)
        
        # Cleanup
        src_path.unlink()
        dst_path.unlink()
        
        return {
            "status": "ok",
            "filename": file.filename.rsplit(".", 1)[0] + f".{target_ext}",
            "size_bytes": len(result_content),
            "conversions_used": metrics["conversions"],
        }
    except ConversionError as exc:
        raise HTTPException(status_code=422, detail=f"Conversion failed: {exc}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Server error: {exc}")


@router.get("/formats", response_model=list[FormatRoute])
def list_formats(api_key: str = Header(...)) -> list[FormatRoute]:
    """List all available conversion routes."""
    load_builtin_converters()
    
    if not api_key or not api_key.startswith(("demo-", "key_")):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    
    routes = registry.routes()
    return [
        FormatRoute(
            source=c.source_ext,
            target=c.target_ext,
            description=c.description,
            tier=c.tier,
            available=c.available(),
        )
        for c in routes
    ]


@router.get("/usage", response_model=UsageInfo)
def get_usage(api_key: str = Header(...)) -> UsageInfo:
    """Get API usage for this key."""
    if not api_key or not api_key.startswith(("demo-", "key_")):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    
    metrics = _get_or_init_api_key(api_key)
    return UsageInfo(
        api_key=api_key,
        conversions=metrics["conversions"],
        bytes_in=metrics["bytes_in"],
        bytes_out=metrics["bytes_out"],
        tier=metrics["tier"],
    )


@router.get("/account", response_model=AccountInfo)
def get_account(api_key: str = Header(...)) -> AccountInfo:
    """Get account tier and limits for this API key."""
    if not api_key or not api_key.startswith(("demo-", "key_")):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    
    metrics = _get_or_init_api_key(api_key)
    
    # Demo key: unlimited; metered keys: 500 conversions/month; paid: unlimited
    tier = metrics["tier"]
    if api_key.startswith("demo-"):
        conversions_limit = None
        bytes_limit = None
    elif tier == "metered":
        conversions_limit = 500
        bytes_limit = None
    else:
        conversions_limit = None
        bytes_limit = None
    
    return AccountInfo(
        api_key=api_key,
        tier=tier,
        conversions_limit=conversions_limit,
        bytes_limit=bytes_limit,
        reset_date="2026-08-24" if tier == "metered" else None,
    )


@router.get("/healthz")
def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "ok"}
