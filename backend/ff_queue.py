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
import time

import redis

from engine import convert_generic

REDIS_URL = os.environ.get("FILEFORGE_REDIS_URL", "redis://127.0.0.1:6379/0")
QUEUE_NAME = "fileforge:jobs"
RESULTS_HASH = "fileforge:results"
HISTORY_LIST = "fileforge:history"
HISTORY_MAX = 100

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


def record_history(job: dict) -> None:
    """Append a completed/errored job to a small persistent history list.

    Used by both server.py (for synchronous /convert, /batch-convert jobs)
    and the worker below (for queued jobs), so /dashboard/jobs shows real
    recent activity even across a backend restart — unlike the in-memory
    JOBS dict in server.py, which is wiped whenever uvicorn restarts.
    """
    try:
        r.lpush(HISTORY_LIST, json.dumps(job))
        r.ltrim(HISTORY_LIST, 0, HISTORY_MAX - 1)
    except redis.exceptions.RedisError as exc:
        print(f"[ff_queue] Could not record history: {exc}")


def list_history(limit: int = 25) -> list[dict]:
    try:
        items = r.lrange(HISTORY_LIST, 0, limit - 1)
    except redis.exceptions.RedisError:
        return []
    return [json.loads(i) for i in items]


def worker_loop() -> None:
    print(f"[ff_queue] Worker started. Listening on '{QUEUE_NAME}' at {REDIS_URL}")
    while True:
        try:
            job = dequeue_job()
        except redis.exceptions.RedisError as exc:
            # A blocking BRPOP over a long-idle socket can hit a transient
            # read timeout (e.g. Android throttling a background Termux
            # session's networking when the screen locks). That's not a
            # reason to kill the whole worker — log it and keep listening.
            print(f"[ff_queue] Redis connection hiccup, retrying: {exc}")
            time.sleep(1)
            continue

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

        try:
            r.hset(RESULTS_HASH, job_id, json.dumps(job))
            record_history(job)
        except redis.exceptions.RedisError as exc:
            print(f"[ff_queue] Could not write result for {job_id}: {exc}")


if __name__ == "__main__":
    worker_loop()
