"""Headless controller for the FileForge Windows desktop app.

All application logic that does *not* touch Tkinter lives here so it can be
unit-tested and reused (the GUI in ``fileforge_app.py`` is a thin view over
this). It builds directly on the FileForge 2.0 discovery/suggestion layer:

- :mod:`fileforge.suggestions` — directory scan, ranked suggestions, plans.
- :mod:`fileforge.core.registry` — the real conversion routes.

Nothing here imports ``tkinter``; keep it that way.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence

from fileforge.core.registry import (
    ConversionError,
    load_builtin_converters,
    registry,
)
from fileforge.suggestions import (
    DirectoryScan,
    Suggestion,
    build_plan,
    scan_directory,
    suggest,
)

#: Where the desktop app keeps its rolling conversion log.
def default_log_path() -> Path:
    r"""Return the per-user history log path.

    On Windows this resolves under ``%LOCALAPPDATA%\FileForge``; elsewhere it
    falls back to ``~/.fileforge`` so the module is testable on Linux/CI.
    """
    base = os.environ.get("LOCALAPPDATA")
    root = Path(base) / "FileForge" if base else Path.home() / ".fileforge"
    return root / "history.jsonl"


@dataclass
class FileTypeSummary:
    """One row of the "file types in this folder" panel."""

    ext: str
    count: int
    samples: List[str] = field(default_factory=list)


@dataclass
class ConversionResult:
    source: str
    target: str
    ok: bool
    error: str = ""
    elapsed_ms: int = 0


class Controller:
    """Backs the desktop GUI. Stateful around a "current directory"."""

    def __init__(self, log_path: Optional[Path] = None) -> None:
        load_builtin_converters()
        self.directory: Optional[Path] = None
        self.scan: Optional[DirectoryScan] = None
        self.log_path = log_path or default_log_path()

    # -- directory + summary ------------------------------------------------ #

    def set_directory(self, directory: os.PathLike | str, *, recursive: bool = False) -> None:
        """Point the controller at *directory* and (re)scan it."""
        self.directory = Path(directory).expanduser()
        self.scan = scan_directory(self.directory, recursive=recursive)

    def file_type_summary(self) -> List[FileTypeSummary]:
        """Extension → count/sample rows for the current directory."""
        if not self.scan:
            return []
        return [
            FileTypeSummary(ext=ext, count=count, samples=self.scan.samples.get(ext, []))
            for ext, count in self.scan.frequency.items()
        ]

    # -- suggestions -------------------------------------------------------- #

    def suggestions(self, *, include_generic: bool = True) -> List[Suggestion]:
        """Ranked conversion suggestions for the current directory."""
        if not self.scan:
            return []
        return suggest(self.scan, include_generic=include_generic)

    def targets_for(self, ext: str) -> List[str]:
        """Engine-supported target extensions for a source extension."""
        return registry.targets_for(ext)

    # -- planning + execution ---------------------------------------------- #

    def plan(self, source_ext: str, target_ext: str, *, recursive: bool = False):
        """Concrete source→target file pairs for one route."""
        if not self.scan:
            return []
        return build_plan(self.scan, source_ext, target_ext, recursive=recursive)

    def run_plan(
        self,
        source_ext: str,
        target_ext: str,
        *,
        recursive: bool = False,
        on_progress: Optional[Callable[[int, int, ConversionResult], None]] = None,
    ) -> List[ConversionResult]:
        """Execute every file in a route's plan, reporting progress.

        *on_progress* is called as ``(done, total, result)`` after each file so
        the GUI can drive a progress bar without knowing the engine internals.
        """
        plan = self.plan(source_ext, target_ext, recursive=recursive)
        total = len(plan)
        results: List[ConversionResult] = []
        conv = registry.get(source_ext.lower().lstrip("."), target_ext.lower().lstrip("."))

        for i, item in enumerate(plan, start=1):
            started = time.monotonic()
            if conv is None:
                res = ConversionResult(
                    source=item.source,
                    target=item.target,
                    ok=False,
                    error=f"no engine route for {item.source_ext} -> {item.target_ext}",
                )
            else:
                try:
                    conv.fn(Path(item.source), Path(item.target))
                    res = ConversionResult(source=item.source, target=item.target, ok=True)
                except (ConversionError, Exception) as exc:  # noqa: BLE001
                    res = ConversionResult(
                        source=item.source, target=item.target, ok=False, error=str(exc)
                    )
            res.elapsed_ms = int((time.monotonic() - started) * 1000)
            results.append(res)
            self._log(res)
            if on_progress:
                on_progress(i, total, res)
        return results

    # -- history / logging -------------------------------------------------- #

    def _log(self, result: ConversionResult) -> None:
        """Append one conversion to the rolling JSONL history log."""
        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            entry = {
                "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "source": result.source,
                "target": result.target,
                "ok": result.ok,
                "error": result.error,
                "elapsed_ms": result.elapsed_ms,
            }
            with self.log_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry) + "\n")
        except OSError:
            pass  # logging must never break a conversion

    def history(self, limit: int = 50) -> List[dict]:
        """Return the most recent *limit* history entries (newest last)."""
        if not self.log_path.exists():
            return []
        lines = self.log_path.read_text(encoding="utf-8").splitlines()
        out: List[dict] = []
        for line in lines[-limit:]:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return out

    def clear_history(self) -> None:
        try:
            if self.log_path.exists():
                self.log_path.unlink()
        except OSError:
            pass


__all__ = [
    "Controller",
    "ConversionResult",
    "FileTypeSummary",
    "default_log_path",
]
