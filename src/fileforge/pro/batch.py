"""Batch + parallel conversion — a headline Pro feature.

Convert whole directories (optionally recursive) to a target format using a
process/thread pool. Free tier converts one file at a time; Pro unlocks the
pool and the glob/recursive walk.
"""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, List, Optional

from fileforge.core.registry import ConversionError, load_builtin_converters, registry
from fileforge.licensing import License, Tier, require


@dataclass
class BatchResult:
    source: Path
    target: Optional[Path]
    ok: bool
    error: str = ""


def _iter_sources(root: Path, source_ext: str, recursive: bool) -> Iterable[Path]:
    pattern = f"**/*.{source_ext}" if recursive else f"*.{source_ext}"
    yield from sorted(root.glob(pattern))


def convert_batch(
    root: Path,
    source_ext: str,
    target_ext: str,
    *,
    out_dir: Optional[Path] = None,
    recursive: bool = False,
    workers: Optional[int] = None,
    license: License | None = None,
    on_progress: Optional[Callable[[BatchResult], None]] = None,
    **options,
) -> List[BatchResult]:
    require(Tier.PRO, license)
    if not registry.routes():
        load_builtin_converters()

    conv = registry.get(source_ext, target_ext)
    if conv is None:
        raise ConversionError(f"no converter for {source_ext} -> {target_ext}")

    root = Path(root)
    out_dir = Path(out_dir) if out_dir else root
    out_dir.mkdir(parents=True, exist_ok=True)
    workers = workers or min(32, (os.cpu_count() or 4))

    sources = list(_iter_sources(root, source_ext, recursive))
    results: List[BatchResult] = []

    def _one(src: Path) -> BatchResult:
        dst = out_dir / f"{src.stem}.{target_ext}"
        try:
            conv.fn(src, dst, **options)
            return BatchResult(src, dst, ok=True)
        except Exception as exc:  # noqa: BLE001 - report per-file, keep going
            return BatchResult(src, None, ok=False, error=str(exc))

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_one, s): s for s in sources}
        for fut in as_completed(futures):
            res = fut.result()
            results.append(res)
            if on_progress:
                on_progress(res)
    return sorted(results, key=lambda r: str(r.source))
