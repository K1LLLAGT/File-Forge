"""
ff_queue.py — Redis-backed job queue for FileForge.

Named ff_queue (not queue) deliberately: a local file named queue.py
sitting next to server.py would shadow Python's own stdlib `queue`
module for every other file in this package, which is a landmine for
anything that ever needs threading.Queue. ff_queue avoids that entirely.
"""

from __future__ import annotations

import json
import os

import redis

from engine import convert_generic

REDIS_URL = os.environ.get("FILEFORGE_REDIS_URL", "redis://127.0.0.1:6379/0")
QUEUE_NAME = "fileforge:jobs"
RESULTS_HASH = "fileforge:results"

r = redis.from_url(REDIS_URL)


def enqueue_job(job: dict) -> None:
    r.lpush(QUEUE_NAME, json.dumps(job))
    # Record it as pending immediately so /queue-status doesn't 404
    # for a job that's still sitting in the list.
    pending = {**job, "status": "pending"}
    r.hset(RESULTS_HASH, job["jobId"], json.dumps(pending))


def dequeue_job() -> dict | None:
    item = r.brpop(QUEUE_NAME, timeout=5)
    if not item:
        return None
    _, payload = item
    return json.loads(payload)


def get_result(job_id: str) -> dict | None:
    data = r.hget(RESULTS_HASH, job_id)
    if not data:
        return None
    return json.loads(data)


def queue_depth() -> int:
    return r.llen(QUEUE_NAME)


def worker_loop() -> None:
    print(f"[ff_queue] Worker started. Listening on '{QUEUE_NAME}' at {REDIS_URL}")
    while True:
        job = dequeue_job()
        if not job:
            continue
        job_id = job.get("jobId", "unknown")
        print(f"[ff_queue] Processing {job_id}: {job.get('input')} -> {job.get('output')}")
        try:
            convert_generic(job["input"], job["output"])
            job["status"] = "completed"
        except Exception as exc:  # noqa: BLE001 - a bad job must not kill the worker
            job["status"] = "error"
            job["error"] = str(exc)
            print(f"[ff_queue] {job_id} failed: {exc}")
        r.hset(RESULTS_HASH, job_id, json.dumps(job))


if __name__ == "__main__":
    worker_loop()
