"""
scaffolder.py — Genesis Engine: Project Scaffolding Module
===========================================================
SEED_ID: SEED-001
Protocol: 110%

Consumes a Seed Idea from manifest.json and scaffolds a production-ready
project structure following the 110% Protocol standards. Templates are
loaded from the sibling `templates/` directory.

Usage:
    python src/genesis/scaffolder.py --seed <SEED-ID> [--output <path>]
    python src/genesis/scaffolder.py --seed SEED-001 --output ./output/my-project

Exit codes:
    0 — scaffolding complete
    1 — unrecoverable error
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from string import Template
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
log = logging.getLogger("scaffolder")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_HERE = Path(__file__).parent
_TEMPLATES_DIR = _HERE / "templates"
_DEFAULT_MANIFEST = _HERE.parent / "discovery" / "manifest.json"

# ---------------------------------------------------------------------------
# Template selection
# ---------------------------------------------------------------------------

_GATE_TEMPLATE_MAP: dict[str, str] = {
    "G1": "python_module",
    "G2": "python_module",
    "G3": "governance",
    "G4": "python_module",
    "G5": "python_module",
}
_DEFAULT_TEMPLATE = "python_module"


def _select_template(seed: dict) -> str:
    return _GATE_TEMPLATE_MAP.get(seed.get("gate", ""), _DEFAULT_TEMPLATE)


# ---------------------------------------------------------------------------
# Template loading & rendering
# ---------------------------------------------------------------------------

def _load_template_manifest(template_name: str) -> dict:
    """Load the template's manifest.json describing the files to generate."""
    manifest_path = _TEMPLATES_DIR / template_name / "template_manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(
            f"Template manifest not found: {manifest_path}"
        )
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def _render(template_str: str, variables: dict) -> str:
    """Safe string substitution — unknown placeholders are left intact."""
    # Use Python's string.Template with $var / ${var} syntax.
    # Escape any lone $ signs that are not valid substitution tokens.
    try:
        return Template(template_str).safe_substitute(variables)
    except Exception as exc:  # noqa: BLE001
        log.warning("Template rendering issue: %s", exc)
        return template_str


def _build_variables(seed: dict) -> dict:
    """Derive template substitution variables from a seed record."""
    name_raw = seed.get("description", seed["id"])
    # Convert to a safe Python identifier / slug
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", name_raw).strip("_").lower()
    module_name = slug[:40]  # keep it reasonable

    return {
        "SEED_ID": seed["id"],
        "SEED_DESCRIPTION": seed.get("description", ""),
        "MODULE_NAME": module_name,
        "DATE": datetime.now(tz=timezone.utc).strftime("%Y-%m-%d"),
        "VERSION": "0.1.0",
        "GATE": seed.get("gate", "G1"),
    }


# ---------------------------------------------------------------------------
# Scaffolding
# ---------------------------------------------------------------------------

def scaffold(seed: dict, output_dir: Path) -> list[Path]:
    """Scaffold a project for the given seed into output_dir.

    Returns the list of created file paths.
    """
    template_name = _select_template(seed)
    log.info(
        "Scaffolding seed=%s with template='%s' into '%s'",
        seed["id"],
        template_name,
        output_dir,
    )

    template_def = _load_template_manifest(template_name)
    variables = _build_variables(seed)

    created: list[Path] = []
    for file_entry in template_def.get("files", []):
        rel_path = _render(file_entry["path"], variables)
        src_template = _TEMPLATES_DIR / template_name / file_entry["template"]

        if not src_template.exists():
            log.warning("Template source not found, skipping: %s", src_template)
            continue

        raw_content = src_template.read_text(encoding="utf-8")
        rendered_content = _render(raw_content, variables)

        dest_path = output_dir / rel_path
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_text(rendered_content, encoding="utf-8")
        log.info("Created: %s", dest_path)
        created.append(dest_path)

    return created


# ---------------------------------------------------------------------------
# Manifest helpers
# ---------------------------------------------------------------------------

def _load_manifest(manifest_path: Path) -> dict:
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def _find_seed(manifest: dict, seed_id: str) -> dict:
    for seed in manifest.get("seeds", []):
        if seed.get("id") == seed_id:
            return seed
    raise ValueError(f"Seed '{seed_id}' not found in manifest")


def _update_seed_status(manifest_path: Path, seed_id: str, status: str) -> None:
    manifest = _load_manifest(manifest_path)
    for seed in manifest.get("seeds", []):
        if seed.get("id") == seed_id:
            seed["status"] = status
            seed["updated_at"] = datetime.now(tz=timezone.utc).isoformat()
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Infinity Invention Machine — Scaffolder v" + __version__
    )
    parser.add_argument(
        "--seed",
        required=True,
        help="Seed ID to scaffold (e.g. SEED-001)",
    )
    parser.add_argument(
        "--output",
        default="./output",
        help="Directory to scaffold into (default: ./output)",
    )
    parser.add_argument(
        "--manifest",
        default=str(_DEFAULT_MANIFEST),
        help="Path to the seed manifest file",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    manifest_path = Path(args.manifest).resolve()
    output_dir = Path(args.output).resolve()

    try:
        manifest = _load_manifest(manifest_path)
        seed = _find_seed(manifest, args.seed)
    except (FileNotFoundError, ValueError) as exc:
        log.error("%s", exc)
        return 1

    try:
        _update_seed_status(manifest_path, args.seed, "IN_PROGRESS")
        created = scaffold(seed, output_dir)
        _update_seed_status(manifest_path, args.seed, "COMPLETE")
        log.info("Scaffolding complete. Files created: %d", len(created))
    except Exception as exc:  # noqa: BLE001
        log.error("Fatal error during scaffolding: %s", exc)
        _update_seed_status(manifest_path, args.seed, "IDENTIFIED")  # revert
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
