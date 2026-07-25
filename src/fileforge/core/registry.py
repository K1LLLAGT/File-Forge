"""Conversion registry — the shared engine for every FileForge tier.

A *converter* is any callable that turns a source file into a destination
file. Converters register themselves against a ``(source_ext, target_ext)``
pair. The registry is deliberately tier-agnostic: the free CLI, the Pro
desktop build, and the Cloud API all resolve conversions through the same
lookup so behaviour stays identical everywhere.
"""

from __future__ import annotations

import importlib
import pkgutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Tuple

# A converter takes (source_path, target_path, **options) and writes the
# result to target_path. It returns the target_path on success.
ConverterFn = Callable[..., Path]


class ConversionError(RuntimeError):
    """Raised when a conversion cannot be performed or fails mid-way."""


@dataclass(frozen=True)
class Converter:
    """Metadata + implementation for a single conversion route."""

    source_ext: str
    target_ext: str
    fn: ConverterFn
    tier: str = "free"  # free | pro | cloud | enterprise
    description: str = ""
    requires: Tuple[str, ...] = field(default_factory=tuple)  # optional deps

    @property
    def route(self) -> Tuple[str, str]:
        return (self.source_ext, self.target_ext)

    def available(self) -> bool:
        """True when every optional dependency this converter needs imports."""
        for module in self.requires:
            if importlib.util.find_spec(module) is None:
                return False
        return True


class Registry:
    """Holds every known converter and resolves conversion requests."""

    def __init__(self) -> None:
        self._converters: Dict[Tuple[str, str], Converter] = {}

    def register(self, converter: Converter) -> None:
        self._converters[converter.route] = converter

    def add(
        self,
        source_ext: str,
        target_ext: str,
        *,
        tier: str = "free",
        description: str = "",
        requires: Iterable[str] = (),
    ):
        """Decorator form: ``@registry.add("png", "jpg")``."""

        def _wrap(fn: ConverterFn) -> ConverterFn:
            self.register(
                Converter(
                    source_ext=_norm(source_ext),
                    target_ext=_norm(target_ext),
                    fn=fn,
                    tier=tier,
                    description=description,
                    requires=tuple(requires),
                )
            )
            return fn

        return _wrap

    def get(self, source_ext: str, target_ext: str) -> Optional[Converter]:
        return self._converters.get((_norm(source_ext), _norm(target_ext)))

    def routes(self, tier: Optional[str] = None) -> List[Converter]:
        items = sorted(self._converters.values(), key=lambda c: c.route)
        if tier is None:
            return items
        order = ["free", "pro", "cloud", "enterprise"]
        allowed = set(order[: order.index(tier) + 1])
        return [c for c in items if c.tier in allowed]

    def targets_for(self, source_ext: str) -> List[str]:
        src = _norm(source_ext)
        return sorted(t for (s, t) in self._converters if s == src)

    def find_path(
        self, source_ext: str, target_ext: str, *, max_hops: int = 3
    ) -> Optional[List["Converter"]]:
        """Return the shortest chain of *available* converters that turns
        ``source_ext`` into ``target_ext`` (e.g. ``md -> txt -> pdf``), or
        ``None`` if no route within ``max_hops`` exists.

        Only converters whose optional dependencies are importable are used, so
        a returned chain is always runnable. Callers should try :meth:`get`
        (a direct converter) first; this handles the indirect case.
        """
        from collections import deque

        src, tgt = _norm(source_ext), _norm(target_ext)
        if src == tgt:
            return []
        # Adjacency of available converters: ext -> [(next_ext, converter)].
        adj: Dict[str, List[Tuple[str, "Converter"]]] = {}
        for (s, t), conv in self._converters.items():
            if conv.available():
                adj.setdefault(s, []).append((t, conv))

        queue = deque([(src, [])])
        seen = {src}
        while queue:
            cur, path = queue.popleft()
            if len(path) >= max_hops:
                continue
            for nxt, conv in adj.get(cur, []):
                if nxt == tgt:
                    return path + [conv]
                if nxt not in seen:
                    seen.add(nxt)
                    queue.append((nxt, path + [conv]))
        return None


def _norm(ext: str) -> str:
    return ext.lower().lstrip(".")


# The one process-wide registry every tier imports.
registry = Registry()


def load_builtin_converters() -> None:
    """Import every module under ``fileforge.converters`` so its
    ``@registry.add`` decorators run and populate the registry."""
    import fileforge.converters as converters_pkg

    for mod in pkgutil.iter_modules(converters_pkg.__path__):
        importlib.import_module(f"fileforge.converters.{mod.name}")
