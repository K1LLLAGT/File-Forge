"""
server.py — FileForge unified FastAPI backend.

Run with:
    uvicorn server:app --host 127.0.0.1 --port 8091

This single `app` is the one true FastAPI instance. Every conversion
capability (single convert, batch, queue, thumbnails, compression) is
registered on it via APIRouter, so all routes below actually exist on
the running server. Previously, batch/queue/thumbnail/compression each
lived in their own standalone FastAPI() instance in a *_patch.py file
that server.py never imported — those routes never actually ran.

Imports below are absolute (not relative) on purpose: this module is
invoked as a top-level module via `uvicorn server:app`, not as part of
a package, so `from .engine import ...` would fail with "attempted
relative import with no known parent package". Absolute imports work
because uvicorn's working directory (backend/) is on sys.path.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from typing import Dict

from fastapi import APIRouter, FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from batch import batch_convert
from compression import compress_video
from engine import ConversionError, convert_generic
from ff_queue import enqueue_job, get_result, list_history, queue_depth, record_history
from thumbnails import image_thumbnail, video_thumbnail

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("fileforge")

app = FastAPI(title="FileForge Backend", version="2.0.0")

# The Next.js dev server (port 8090) calls this API directly from route
# handlers running server-side, but CORS is opened up for direct/local
# testing (e.g. curl, the CLI, or hitting the API from a browser tab).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8090", "http://localhost:8090"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(__file__)
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
COMPRESSED_DIR = os.path.join(BASE_DIR, "compressed")
THUMB_DIR = os.path.join(BASE_DIR, "thumbs")
for d in (OUTPUT_DIR, COMPRESSED_DIR, THUMB_DIR):
    os.makedirs(d, exist_ok=True)

# In-memory job store for synchronous (/convert, /batch-convert) jobs.
# Queued jobs (/queue-convert) live in Redis via ff_queue instead, since
# they need to survive across the worker process.
JOBS: Dict[str, Dict] = {}


def _save_upload(upload: UploadFile, dest_dir: str, prefix: str) -> str:
    path = os.path.join(dest_dir, f"{prefix}-{upload.filename}")
    with open(path, "wb") as f:
        f.write(upload.file.read())
    return path


# ============================================================
# Single conversion
# ============================================================
convert_router = APIRouter(tags=["convert"])


@convert_router.post("/convert")
async def convert_file(file: UploadFile = File(...), target_ext: str = Form(...)):
    job_id = f"ff-{uuid.uuid4().hex[:8]}"
    input_path = os.path.join(OUTPUT_DIR, f"{job_id}-input-{file.filename}")
    output_path = os.path.join(OUTPUT_DIR, f"{job_id}-output.{target_ext.lstrip('.')}")

    with open(input_path, "wb") as f:
        f.write(await file.read())

    try:
        convert_generic(input_path, output_path)
    except ConversionError as exc:
        JOBS[job_id] = {"status": "error", "error": str(exc)}
        log.warning("convert %s failed: %s", job_id, exc)
        return JSONResponse({"jobId": job_id, "status": "error", "error": str(exc)}, status_code=500)

    JOBS[job_id] = {
        "status": "completed",
        "input": input_path,
        "output": output_path,
        "target_ext": target_ext,
        "filename": file.filename,
    }
    record_history({"jobId": job_id, **JOBS[job_id]})

    return {"jobId": job_id, "status": "completed", "downloadUrl": f"/download/{job_id}"}


@convert_router.get("/status/{job_id}")
async def status(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        return JSONResponse({"error": "Job not found"}, status_code=404)
    return job


@convert_router.get("/download/{job_id}")
async def download(job_id: str):
    job = JOBS.get(job_id)
    if not job or job.get("status") != "completed":
        return JSONResponse({"error": "Job not completed"}, status_code=404)
    return FileResponse(job["output"], filename=os.path.basename(job["output"]))


# ============================================================
# Batch conversion
# ============================================================
batch_router = APIRouter(tags=["batch"])


@batch_router.post("/batch-convert")
async def batch_convert_endpoint(files: list[UploadFile] = File(...), target_ext: str = Form(...)):
    jobs = []
    for f in files:
        job_id = f"ff-batch-{uuid.uuid4().hex[:8]}"
        input_path = os.path.join(OUTPUT_DIR, f"{job_id}-input-{f.filename}")
        output_path = os.path.join(OUTPUT_DIR, f"{job_id}-output.{target_ext.lstrip('.')}")
        with open(input_path, "wb") as fp:
            fp.write(await f.read())
        jobs.append({"jobId": job_id, "input": input_path, "output": output_path})

    results = batch_convert(jobs)
    for r in results:
        JOBS[r["jobId"]] = r
        record_history(r)
    return {"jobs": results}


# ============================================================
# Queued conversion (Redis-backed)
# ============================================================
queue_router = APIRouter(tags=["queue"])


@queue_router.post("/queue-convert")
async def queue_convert(file: UploadFile = File(...), target_ext: str = Form(...)):
    job_id = f"ff-q-{uuid.uuid4().hex[:8]}"
    input_path = os.path.join(OUTPUT_DIR, f"{job_id}-input-{file.filename}")
    output_path = os.path.join(OUTPUT_DIR, f"{job_id}-output.{target_ext.lstrip('.')}")

    with open(input_path, "wb") as f:
        f.write(await file.read())

    job = {
        "jobId": job_id,
        "input": input_path,
        "output": output_path,
        "target_ext": target_ext,
        "filename": file.filename,
    }
    enqueue_job(job)
    return {"jobId": job_id, "status": "queued"}


@queue_router.get("/queue-status/{job_id}")
async def queue_status(job_id: str):
    job = get_result(job_id)
    if not job:
        return JSONResponse({"jobId": job_id, "status": "pending"}, status_code=200)
    return job


@queue_router.get("/queue/stats")
async def queue_stats():
    try:
        depth = queue_depth()
    except Exception as exc:  # noqa: BLE001 - Redis may be unreachable
        return JSONResponse({"error": f"Redis unavailable: {exc}"}, status_code=503)
    return {"depth": depth}


# ============================================================
# Thumbnails
# ============================================================
thumbnail_router = APIRouter(tags=["thumbnails"])


@thumbnail_router.post("/thumbnail/image")
async def thumbnail_image(file: UploadFile = File(...)):
    input_path = os.path.join(THUMB_DIR, f"img-{file.filename}")
    thumb_path = os.path.join(THUMB_DIR, f"thumb-{file.filename}.png")
    with open(input_path, "wb") as f:
        f.write(await file.read())
    try:
        image_thumbnail(input_path, thumb_path)
        return FileResponse(thumb_path, filename=os.path.basename(thumb_path))
    except ConversionError as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


@thumbnail_router.post("/thumbnail/video")
async def thumbnail_video(file: UploadFile = File(...)):
    input_path = os.path.join(THUMB_DIR, f"vid-{file.filename}")
    thumb_path = os.path.join(THUMB_DIR, f"thumb-{file.filename}.png")
    with open(input_path, "wb") as f:
        f.write(await file.read())
    try:
        video_thumbnail(input_path, thumb_path)
        return FileResponse(thumb_path, filename=os.path.basename(thumb_path))
    except ConversionError as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


# ============================================================
# Compression
# ============================================================
compression_router = APIRouter(tags=["compression"])


@compression_router.post("/compress/video")
async def compress_video_endpoint(
    file: UploadFile = File(...),
    preset: str = Form("medium"),
    crf: int = Form(23),
):
    job_id = f"ff-comp-{uuid.uuid4().hex[:8]}"
    input_path = os.path.join(COMPRESSED_DIR, f"{job_id}-input-{file.filename}")
    output_path = os.path.join(COMPRESSED_DIR, f"{job_id}-output.mp4")

    with open(input_path, "wb") as f:
        f.write(await file.read())

    try:
        compress_video(input_path, output_path, preset=preset, crf=crf)
        return {"jobId": job_id, "status": "completed", "downloadUrl": f"/compress/download/{job_id}"}
    except ConversionError as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


@compression_router.get("/compress/download/{job_id}")
async def compress_download(job_id: str):
    for fname in os.listdir(COMPRESSED_DIR):
        if fname.startswith(f"{job_id}-output"):
            return FileResponse(os.path.join(COMPRESSED_DIR, fname), filename=fname)
    return JSONResponse({"error": "Not found"}, status_code=404)


# ============================================================
# Dashboard telemetry (real, not stubbed)
# ============================================================
dashboard_router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@dashboard_router.get("/jobs")
async def dashboard_jobs():
    # Persistent history survives backend restarts (Redis-backed); the
    # in-memory JOBS dict does not, so history is the primary source and
    # JOBS only fills in anything from the current process not yet flushed.
    history = list_history(limit=25)
    seen_ids = {j.get("jobId") for j in history}
    recent_in_memory = [
        {"jobId": jid, **data} for jid, data in list(JOBS.items())[-25:]
        if jid not in seen_ids
    ]
    return {
        "endpoints": [
            "/convert", "/batch-convert", "/queue-convert", "/queue-status/{jobId}",
            "/thumbnail/image", "/thumbnail/video", "/compress/video",
        ],
        "recentJobs": (history + recent_in_memory)[:25],
    }


@dashboard_router.get("/queue")
async def dashboard_queue():
    try:
        return {"depth": queue_depth()}
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"error": f"Redis unavailable: {exc}"}, status_code=503)


@dashboard_router.get("/thumbs")
async def dashboard_thumbs():
    files = sorted(os.listdir(THUMB_DIR))[-25:]
    return {"thumbnails": files}


@app.get("/health")
async def health():
    return {"status": "ok"}


for router in (convert_router, batch_router, queue_router, thumbnail_router, compression_router, dashboard_router):
    app.include_router(router)
