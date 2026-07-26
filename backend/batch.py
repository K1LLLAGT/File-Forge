"""batch.py — concurrent multi-file conversion."""

from __future__ import annotations

import concurrent.futures

from engine import convert_generic

MAX_WORKERS = 4


def batch_convert(jobs: list[dict]) -> list[dict]:
    """Convert a list of {jobId, input, output} jobs concurrently."""
    results: list[dict] = []

    def worker(job: dict) -> dict:
        try:
            convert_generic(job["input"], job["output"])
            return {**job, "status": "completed"}
        except Exception as exc:  # noqa: BLE001 - one bad file must not sink the batch
            return {**job, "status": "error", "error": str(exc)}

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        for res in executor.map(worker, jobs):
            results.append(res)

    return results
