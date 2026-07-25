"""FileForge discovery & normalization layer.

Real-world FileForge checkouts accumulate a zoo of names: ``File Forge``,
``FileForge``, ``File-Forge``, ``fileforge``, ``~/file-forge`` and so on. This
module resolves every one of those aliases to a single canonical identity and
walks the filesystem to enumerate the concrete *instances* of the project it
can find, tagging each with the role it plays (web, backend, desktop, Android,
cloud, packaging, …).

It is intentionally dependency-free so it can run inside the same environments
as the rest of the engine (CI, Android/Chaquopy, PyInstaller bundles).

Public API
----------
- :func:`normalize_alias`      — map any spelling to the canonical id.
- :func:`is_alias`             — does a string look like a FileForge alias?
- :func:`discover`             — walk roots, return a :class:`DiscoveryResult`.
- :func:`main`                 — ``fileforge-discover`` console entry point.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

# --------------------------------------------------------------------------- #
# Canonical identity & alias resolution
# --------------------------------------------------------------------------- #

#: The single identity every alias collapses to.
CANONICAL_NAME = "FileForge 2.0"
#: A slug-safe form used for package names, directories and comparisons.
CANONICAL_ID = "fileforge"

#: Known human-facing spellings. Order does not matter — matching is normalized.
KNOWN_ALIASES: Sequence[str] = (
    "File Forge",
    "FileForge",
    "File-Forge",
    "file-forge",
    "fileforge",
    "file_forge",
    "FileForge 2.0",
    "FileForge2",
    "~/file-forge",
)

# Any run of these characters between "file" and "forge" is treated as a
# separator, so "file  forge", "file.forge", "file/forge" all normalize.
_ALIAS_RE = re.compile(r"file[\s\-_.]*forge(?:\s*2(?:\.0)?)?", re.IGNORECASE)


def normalize_alias(text: str) -> Optional[str]:
    """Return :data:`CANONICAL_ID` if *text* is (or contains) a FileForge
    alias, else ``None``.

    The comparison is whitespace/separator/case insensitive so ``"File Forge"``,
    ``"file-forge"`` and ``"~/fileforge/"`` all resolve identically.
    """
    if not text:
        return None
    candidate = os.path.expanduser(text).strip().strip("/\\")
    # Compare only the last path component so "~/dev/file-forge" still matches.
    tail = Path(candidate).name or candidate
    if _ALIAS_RE.fullmatch(tail) or _ALIAS_RE.fullmatch(candidate):
        return CANONICAL_ID
    return None


def is_alias(text: str) -> bool:
    """True when *text* resolves to the canonical FileForge identity."""
    return normalize_alias(text) is not None


# --------------------------------------------------------------------------- #
# Role identification
# --------------------------------------------------------------------------- #

#: Ordered list of ``(role, matcher)`` rules. The first matching rule that a
#: directory satisfies contributes its role. A single instance may carry many
#: roles (a monorepo checkout carries all of them).
_ROLE_MARKERS: Sequence[tuple] = (
    ("android", ("build.gradle.kts", "AndroidManifest.xml", "settings.gradle.kts")),
    ("desktop", ("fileforge_gui.py", "build_windows.ps1", "FileForge.exe")),
    ("cloud", ("cloud-api", "app/api.py", "app/metering.py")),
    ("backend", ("src/fileforge/core/registry.py", "src/fileforge")),
    ("licensing", ("license-server", "licensing.py")),
    ("packaging", ("magisk-module", "module.prop", "build_magisk_zip.sh")),
    ("web", ("index.html", "package.json", "vite.config.ts")),
    ("cli", ("pyproject.toml", "cli.py")),
    ("docs", ("README.md", "ARCHITECTURE.md")),
)


def identify_roles(path: Path) -> List[str]:
    """Return the sorted list of roles a directory appears to fulfil."""
    roles: List[str] = []
    for role, markers in _ROLE_MARKERS:
        for marker in markers:
            if (path / marker).exists():
                roles.append(role)
                break
    return sorted(set(roles))


# --------------------------------------------------------------------------- #
# Data model
# --------------------------------------------------------------------------- #


@dataclass
class Instance:
    """A concrete FileForge checkout discovered on disk."""

    path: Path
    canonical: str = CANONICAL_ID
    matched_via: str = "name"          # "name" | "marker"
    roles: List[str] = field(default_factory=list)
    markers: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "path": str(self.path),
            "canonical": self.canonical,
            "matched_via": self.matched_via,
            "roles": self.roles,
            "markers": self.markers,
        }


@dataclass
class DiscoveryResult:
    """Everything :func:`discover` found in one pass."""

    canonical_name: str = CANONICAL_NAME
    canonical_id: str = CANONICAL_ID
    roots: List[str] = field(default_factory=list)
    instances: List[Instance] = field(default_factory=list)

    @property
    def roles(self) -> List[str]:
        """Union of every role across every instance."""
        seen: set = set()
        for inst in self.instances:
            seen.update(inst.roles)
        return sorted(seen)

    def to_dict(self) -> dict:
        return {
            "canonical_name": self.canonical_name,
            "canonical_id": self.canonical_id,
            "aliases": list(KNOWN_ALIASES),
            "roots": self.roots,
            "roles": self.roles,
            "instances": [i.to_dict() for i in self.instances],
        }


# --------------------------------------------------------------------------- #
# Discovery
# --------------------------------------------------------------------------- #

# Directories we never descend into — noise and huge, irrelevant trees.
_SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "build", "dist",
    ".gradle", ".idea", ".mypy_cache", ".pytest_cache", "site-packages",
}

# Files whose presence alone identifies a directory as a FileForge instance
# even when the directory itself is not aliased (e.g. a monorepo root).
_INSTANCE_MARKERS = (
    "pyproject.toml",
    "src/fileforge",
    "android/app/src/main/python/ffbridge.py",
    "desktop/fileforge_gui.py",
)


def _default_roots() -> List[Path]:
    """Sensible default search roots across Linux/Android/WSL/Windows."""
    roots: List[Path] = [Path.cwd(), Path.home()]
    # Common project parents.
    for name in ("file-forge", "fileforge", "File-Forge", "FileForge"):
        roots.append(Path.home() / name)
    # De-dupe while preserving order and keeping only existing dirs.
    out: List[Path] = []
    seen: set = set()
    for r in roots:
        rp = r.expanduser()
        if rp.exists() and rp.is_dir() and rp not in seen:
            seen.add(rp)
            out.append(rp)
    return out


def _looks_like_instance(path: Path) -> List[str]:
    """Return the marker paths that make *path* look like a FileForge root."""
    hits = [m for m in _INSTANCE_MARKERS if (path / m).exists()]
    return hits


def discover(
    roots: Optional[Iterable[os.PathLike]] = None,
    *,
    max_depth: int = 4,
) -> DiscoveryResult:
    """Walk *roots* (default: cwd + home + common project dirs) and return a
    :class:`DiscoveryResult` describing every FileForge instance found.

    A directory counts as an instance when either its name is a FileForge
    alias *or* it contains one of the :data:`_INSTANCE_MARKERS`.
    """
    search_roots = [Path(r).expanduser() for r in roots] if roots else _default_roots()
    result = DiscoveryResult(roots=[str(r) for r in search_roots])
    seen_paths: set = set()

    for root in search_roots:
        if not root.exists():
            continue
        root_depth = len(root.parts)
        for dirpath, dirnames, _filenames in os.walk(root):
            here = Path(dirpath)
            # Prune noise and enforce depth.
            dirnames[:] = [
                d for d in dirnames
                if d not in _SKIP_DIRS and not d.startswith(".")
            ]
            if len(here.parts) - root_depth > max_depth:
                dirnames[:] = []
                continue

            resolved = here.resolve()
            if resolved in seen_paths:
                continue

            matched_via: Optional[str] = None
            markers: List[str] = []
            if is_alias(here.name):
                matched_via = "name"
            else:
                markers = _looks_like_instance(here)
                if markers:
                    matched_via = "marker"

            if matched_via:
                seen_paths.add(resolved)
                result.instances.append(
                    Instance(
                        path=resolved,
                        matched_via=matched_via,
                        roles=identify_roles(here),
                        markers=markers,
                    )
                )

    result.instances.sort(key=lambda i: str(i.path))
    return result


# --------------------------------------------------------------------------- #
# CLI — ``fileforge-discover``
# --------------------------------------------------------------------------- #


def _render_text(result: DiscoveryResult) -> str:
    lines = [
        f"FileForge discovery — canonical identity: {result.canonical_name} "
        f"(id: {result.canonical_id})",
        f"known aliases: {', '.join(KNOWN_ALIASES)}",
        f"search roots: {', '.join(result.roots) or '(none)'}",
        "",
    ]
    if not result.instances:
        lines.append("no FileForge instances found.")
        return "\n".join(lines)

    lines.append(f"found {len(result.instances)} instance(s):")
    for inst in result.instances:
        roles = ", ".join(inst.roles) or "unknown"
        lines.append(f"  • {inst.path}")
        lines.append(f"      via={inst.matched_via}  roles=[{roles}]")
        if inst.markers:
            lines.append(f"      markers={', '.join(inst.markers)}")
    lines.append("")
    lines.append(f"aggregate roles: {', '.join(result.roles) or 'none'}")
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Entry point for the ``fileforge-discover`` console script."""
    parser = argparse.ArgumentParser(
        prog="fileforge-discover",
        description="Discover and normalize FileForge instances on disk.",
    )
    parser.add_argument(
        "roots",
        nargs="*",
        help="directories to search (default: cwd, home, common project dirs)",
    )
    parser.add_argument(
        "--json", action="store_true", help="emit machine-readable JSON"
    )
    parser.add_argument(
        "--max-depth", type=int, default=4, help="max recursion depth (default: 4)"
    )
    parser.add_argument(
        "--normalize",
        metavar="NAME",
        help="resolve a single alias to the canonical id and exit",
    )
    args = parser.parse_args(argv)

    if args.normalize is not None:
        canonical = normalize_alias(args.normalize)
        if args.json:
            print(json.dumps({"input": args.normalize, "canonical": canonical}))
        else:
            print(canonical or f"'{args.normalize}' is not a FileForge alias")
        return 0 if canonical else 1

    result = discover(args.roots or None, max_depth=args.max_depth)
    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(_render_text(result))
    return 0 if result.instances else 1


if __name__ == "__main__":
    sys.exit(main())
