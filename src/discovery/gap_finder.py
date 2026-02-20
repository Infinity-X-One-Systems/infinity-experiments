"""
gap_finder.py — Discovery Pipeline: Seed Idea Scanner
======================================================
SEED_ID: SEED-001
Protocol: 110%

Scans the repository for system gaps and registers them as Seed Ideas
in manifest.json. A "gap" is any area where automation, documentation,
or tooling is absent or degraded according to the 110% Protocol gates.

Usage:
    python src/discovery/gap_finder.py [--root <path>] [--manifest <path>]

Exit codes:
    0 — scan complete (gaps may or may not have been found)
    1 — unrecoverable error
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

__version__ = "1.0.0"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
log = logging.getLogger("gap_finder")

# ---------------------------------------------------------------------------
# Gap detection rules
# ---------------------------------------------------------------------------

# Each rule is a callable (root: Path) -> list[dict].
# It returns zero or more gap descriptors.
_RULES: list[Any] = []


def _rule(fn: Any) -> Any:
    """Decorator that registers a detection rule."""
    _RULES.append(fn)
    return fn


@_rule
def rule_missing_readme(root: Path) -> list[dict]:
    """G2/G4: Every top-level directory should have a README or __init__."""
    gaps = []
    for dirpath in root.rglob("*"):
        if not dirpath.is_dir():
            continue
        # Exclude any path that has a hidden component or is inside common noise dirs
        rel = dirpath.relative_to(root)
        parts = rel.parts
        if any(p.startswith(".") for p in parts):
            continue
        if any(p in ("node_modules", "__pycache__", "venv", ".venv") for p in parts):
            continue
        has_readme = any(
            (dirpath / name).exists()
            for name in ("README.md", "README.rst", "__init__.py", "template_manifest.json")
        ) or any(dirpath.glob("*.md"))
        if not has_readme and any(dirpath.iterdir()):
            gaps.append(
                {
                    "gate": "G2",
                    "description": f"Directory '{dirpath.relative_to(root)}' has no README or __init__",
                    "path": str(dirpath.relative_to(root)),
                }
            )
    return gaps


@_rule
def rule_missing_docstrings(root: Path) -> list[dict]:
    """G2: Python files should have a module-level docstring."""
    gaps = []
    for pyfile in root.rglob("*.py"):
        if ".git" in pyfile.parts:
            continue
        source = pyfile.read_text(encoding="utf-8", errors="replace")
        stripped = source.lstrip()
        if stripped and not (stripped.startswith('"""') or stripped.startswith("'''")):
            gaps.append(
                {
                    "gate": "G2",
                    "description": f"Python file '{pyfile.relative_to(root)}' lacks a module docstring",
                    "path": str(pyfile.relative_to(root)),
                }
            )
    return gaps


@_rule
def rule_missing_seed_id(root: Path) -> list[dict]:
    """G4: Python files should carry a SEED_ID header comment."""
    gaps = []
    for pyfile in root.rglob("*.py"):
        if ".git" in pyfile.parts:
            continue
        source = pyfile.read_text(encoding="utf-8", errors="replace")
        if "SEED_ID" not in source:
            gaps.append(
                {
                    "gate": "G4",
                    "description": f"Python file '{pyfile.relative_to(root)}' is missing a SEED_ID marker",
                    "path": str(pyfile.relative_to(root)),
                }
            )
    return gaps


@_rule
def rule_missing_governance(root: Path) -> list[dict]:
    """G3: Repository must contain a GOVERNANCE.md file."""
    gaps = []
    if not (root / "GOVERNANCE.md").exists():
        gaps.append(
            {
                "gate": "G3",
                "description": "Repository is missing GOVERNANCE.md",
                "path": "GOVERNANCE.md",
            }
        )
    return gaps


# ---------------------------------------------------------------------------
# Manifest helpers
# ---------------------------------------------------------------------------

def _load_manifest(manifest_path: Path) -> dict:
    if manifest_path.exists():
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    return {"version": "1.0.0", "seeds": []}


def _save_manifest(manifest_path: Path, manifest: dict) -> None:
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _seed_exists(seeds: list[dict], path: str, gate: str) -> bool:
    return any(
        s.get("path") == path and s.get("gate") == gate
        for s in seeds
    )


# ---------------------------------------------------------------------------
# Main scan logic
# ---------------------------------------------------------------------------

def scan(root: Path, manifest_path: Path) -> int:
    """Run all gap-detection rules and update the manifest.

    Returns the number of new gaps registered.
    """
    log.info("Starting gap scan — root=%s", root)
    manifest = _load_manifest(manifest_path)
    seeds: list[dict] = manifest.setdefault("seeds", [])

    new_count = 0
    for rule in _RULES:
        try:
            gaps = rule(root)
        except Exception as exc:  # noqa: BLE001
            log.warning("Rule '%s' raised an exception: %s", rule.__name__, exc)
            continue

        for gap in gaps:
            if _seed_exists(seeds, gap["path"], gap["gate"]):
                continue  # already tracked
            seed = {
                "id": "SEED-" + hashlib.sha1(
                    f"{gap['gate']}:{gap['path']}".encode()
                ).hexdigest()[:8].upper(),
                "gate": gap["gate"],
                "status": "IDENTIFIED",
                "description": gap["description"],
                "path": gap["path"],
                "discovered_at": datetime.now(tz=timezone.utc).isoformat(),
            }
            seeds.append(seed)
            new_count += 1
            log.info("New gap registered: %s — %s", seed["id"], seed["description"])

    manifest["last_scan"] = datetime.now(tz=timezone.utc).isoformat()
    _save_manifest(manifest_path, manifest)
    log.info("Scan complete. New gaps: %d | Total seeds: %d", new_count, len(seeds))
    return new_count


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Infinity Invention Machine — Gap Finder v" + __version__
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Repository root to scan (default: current directory)",
    )
    parser.add_argument(
        "--manifest",
        default="src/discovery/manifest.json",
        help="Path to the seed manifest file",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    manifest_path = Path(args.manifest)
    if not manifest_path.is_absolute():
        manifest_path = root / manifest_path

    if not root.is_dir():
        log.error("Root path does not exist: %s", root)
        return 1

    try:
        scan(root, manifest_path)
    except Exception as exc:  # noqa: BLE001
        log.error("Fatal error during scan: %s", exc)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
