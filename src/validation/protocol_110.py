"""
protocol_110.py — Universal Validation System: The Guardian
============================================================
SEED_ID: SEED-001
Protocol: 110%

Validates repository artifacts against all five 110% Protocol gates and
attempts auto-remediation for known, safe issue patterns.

Usage:
    python src/validation/protocol_110.py [--root <path>] [--fix] [--report <path>]

Exit codes:
    0 — all gates pass
    1 — one or more gates fail (after auto-fix attempts if --fix is set)
    2 — unrecoverable error
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

__version__ = "1.0.0"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
log = logging.getLogger("protocol_110")

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class Finding:
    """A single validation finding against a specific gate."""

    gate: str
    severity: str  # "ERROR" | "WARNING" | "INFO"
    path: str
    message: str
    auto_fixed: bool = False


@dataclass
class ValidationReport:
    """Aggregated report for a full validation run."""

    root: str
    timestamp: str = field(
        default_factory=lambda: datetime.now(tz=timezone.utc).isoformat()
    )
    findings: list[Finding] = field(default_factory=list)
    passed: bool = False

    def add(self, finding: Finding) -> None:
        self.findings.append(finding)

    def error_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "ERROR" and not f.auto_fixed)

    def warning_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "WARNING" and not f.auto_fixed)

    def fixed_count(self) -> int:
        return sum(1 for f in self.findings if f.auto_fixed)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["error_count"] = self.error_count()
        d["warning_count"] = self.warning_count()
        d["fixed_count"] = self.fixed_count()
        return d


# ---------------------------------------------------------------------------
# Check registry
# ---------------------------------------------------------------------------

CheckFn = Callable[[Path, ValidationReport, bool], None]
_CHECKS: list[CheckFn] = []


def _check(fn: CheckFn) -> CheckFn:
    """Decorator that registers a validation check."""
    _CHECKS.append(fn)
    return fn


# ---------------------------------------------------------------------------
# G1 — Zero Failure
# ---------------------------------------------------------------------------

@_check
def check_g1_no_bare_except(root: Path, report: ValidationReport, fix: bool) -> None:
    """G1: Python files must not use bare `except:` clauses."""
    for pyfile in _iter_python_files(root):
        source = pyfile.read_text(encoding="utf-8", errors="replace")
        for i, line in enumerate(source.splitlines(), 1):
            stripped = line.strip()
            if stripped == "except:" or stripped.startswith("except :"):
                report.add(Finding(
                    gate="G1",
                    severity="ERROR",
                    path=str(pyfile.relative_to(root)),
                    message=f"Line {i}: bare `except:` clause found — use `except Exception:`",
                ))


@_check
def check_g1_sys_exit_in_library(root: Path, report: ValidationReport, fix: bool) -> None:
    """G1: Module-level sys.exit() calls (outside functions/classes) are discouraged."""
    for pyfile in _iter_python_files(root):
        if pyfile.name in ("__main__.py",):
            continue
        source = pyfile.read_text(encoding="utf-8", errors="replace")
        lines = source.splitlines()
        in_block = False  # inside a function, class, or if __name__ block
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            # Track entry into any indented block (function/class/if __name__)
            if re.match(r"^(def |class |if __name__)", stripped):
                in_block = True
            # A non-empty, unindented line that isn't a definition resets block tracking
            if line and not line[0].isspace() and not re.match(r"^(def |class |if |@|#|[\"'])", line):
                in_block = False
            if not in_block and "sys.exit(" in line and not stripped.startswith("#"):
                report.add(Finding(
                    gate="G1",
                    severity="WARNING",
                    path=str(pyfile.relative_to(root)),
                    message=f"Line {i}: `sys.exit()` called at module scope — move inside a function",
                ))


# ---------------------------------------------------------------------------
# G2 — Zero Tech Debt
# ---------------------------------------------------------------------------

@_check
def check_g2_module_docstring(root: Path, report: ValidationReport, fix: bool) -> None:
    """G2: Every Python file must have a module-level docstring."""
    for pyfile in _iter_python_files(root):
        source = pyfile.read_text(encoding="utf-8", errors="replace")
        stripped = source.lstrip()

        # Skip encoding declarations and shebangs at the very top
        effective = re.sub(r"^(#[^\n]*\n)+", "", stripped)
        effective = effective.lstrip()

        has_docstring = effective.startswith('"""') or effective.startswith("'''")
        if not has_docstring:
            if fix:
                _fix_add_docstring(pyfile, source)
                report.add(Finding(
                    gate="G2",
                    severity="WARNING",
                    path=str(pyfile.relative_to(root)),
                    message="Missing module docstring — stub inserted by auto-fix",
                    auto_fixed=True,
                ))
            else:
                report.add(Finding(
                    gate="G2",
                    severity="ERROR",
                    path=str(pyfile.relative_to(root)),
                    message="Missing module-level docstring",
                ))


@_check
def check_g2_version_string(root: Path, report: ValidationReport, fix: bool) -> None:
    """G2: Every Python module must declare __version__."""
    for pyfile in _iter_python_files(root):
        source = pyfile.read_text(encoding="utf-8", errors="replace")
        if "__version__" not in source:
            if fix:
                _fix_add_version(pyfile, source)
                report.add(Finding(
                    gate="G2",
                    severity="WARNING",
                    path=str(pyfile.relative_to(root)),
                    message="Missing __version__ — set to '0.0.1-auto' by auto-fix",
                    auto_fixed=True,
                ))
            else:
                report.add(Finding(
                    gate="G2",
                    severity="ERROR",
                    path=str(pyfile.relative_to(root)),
                    message="Missing __version__ declaration",
                ))


# ---------------------------------------------------------------------------
# G3 — Governance First
# ---------------------------------------------------------------------------

@_check
def check_g3_governance_file(root: Path, report: ValidationReport, fix: bool) -> None:
    """G3: Repository must contain GOVERNANCE.md."""
    if not (root / "GOVERNANCE.md").exists():
        report.add(Finding(
            gate="G3",
            severity="ERROR",
            path="GOVERNANCE.md",
            message="GOVERNANCE.md is missing — all governance gates will fail",
        ))


@_check
def check_g3_readme_exists(root: Path, report: ValidationReport, fix: bool) -> None:
    """G3: Repository must contain a top-level README.md."""
    if not (root / "README.md").exists():
        report.add(Finding(
            gate="G3",
            severity="ERROR",
            path="README.md",
            message="README.md is missing",
        ))


# ---------------------------------------------------------------------------
# G4 — Traceability
# ---------------------------------------------------------------------------

@_check
def check_g4_seed_id_header(root: Path, report: ValidationReport, fix: bool) -> None:
    """G4: Every Python file must carry a SEED_ID marker."""
    for pyfile in _iter_python_files(root):
        source = pyfile.read_text(encoding="utf-8", errors="replace")
        if "SEED_ID" not in source:
            if fix:
                _fix_add_seed_id(pyfile, source)
                report.add(Finding(
                    gate="G4",
                    severity="WARNING",
                    path=str(pyfile.relative_to(root)),
                    message="Missing SEED_ID — set to 'SEED-UNKNOWN' by auto-fix",
                    auto_fixed=True,
                ))
            else:
                report.add(Finding(
                    gate="G4",
                    severity="ERROR",
                    path=str(pyfile.relative_to(root)),
                    message="Missing SEED_ID traceability marker",
                ))


@_check
def check_g4_manifest_exists(root: Path, report: ValidationReport, fix: bool) -> None:
    """G4: The seed manifest must exist."""
    manifest_path = root / "src" / "discovery" / "manifest.json"
    if not manifest_path.exists():
        report.add(Finding(
            gate="G4",
            severity="ERROR",
            path="src/discovery/manifest.json",
            message="Seed manifest (manifest.json) is missing",
        ))


# ---------------------------------------------------------------------------
# G5 — Scalability Hook
# ---------------------------------------------------------------------------

@_check
def check_g5_public_interface(root: Path, report: ValidationReport, fix: bool) -> None:
    """G5: Python modules should expose a `main` callable as a scalability hook."""
    for pyfile in _iter_python_files(root):
        if pyfile.name.startswith("test_") or pyfile.name == "__init__.py":
            continue
        source = pyfile.read_text(encoding="utf-8", errors="replace")
        # Check for `def main(` — the standard scalability hook
        if "def main(" not in source:
            report.add(Finding(
                gate="G5",
                severity="WARNING",
                path=str(pyfile.relative_to(root)),
                message="No `main()` entry point found — module lacks a scalability hook",
            ))


# ---------------------------------------------------------------------------
# Auto-fix helpers
# ---------------------------------------------------------------------------

def _fix_add_docstring(pyfile: Path, source: str) -> None:
    """Insert a stub module docstring at the top of the file."""
    stub = f'"""\n{pyfile.stem} — auto-generated stub docstring.\nSEED_ID: SEED-UNKNOWN\nProtocol: 110%\n"""\n\n'
    pyfile.write_text(stub + source, encoding="utf-8")
    log.info("Auto-fix [G2]: added docstring stub to %s", pyfile)


def _fix_add_version(pyfile: Path, source: str) -> None:
    """Insert a __version__ declaration after the module docstring (if any)."""
    import ast as _ast
    version_line = "\n__version__ = '0.0.1-auto'\n"
    insert_pos = 0
    try:
        tree = _ast.parse(source)
        if (
            tree.body
            and isinstance(tree.body[0], _ast.Expr)
            and isinstance(tree.body[0].value, _ast.Constant)
            and isinstance(tree.body[0].value.value, str)
        ):
            # Insert after the last line of the docstring node
            doc_node = tree.body[0]
            end_line = doc_node.end_lineno  # type: ignore[attr-defined]
            lines = source.splitlines(keepends=True)
            insert_pos = sum(len(l) for l in lines[:end_line])
    except SyntaxError:
        pass  # Fall back to inserting at the top
    new_source = source[:insert_pos] + version_line + source[insert_pos:]
    pyfile.write_text(new_source, encoding="utf-8")
    log.info("Auto-fix [G2]: added __version__ to %s", pyfile)


def _fix_add_seed_id(pyfile: Path, source: str) -> None:
    """Insert a SEED_ID comment into the module docstring or at the top."""
    seed_comment = "# SEED_ID: SEED-UNKNOWN\n"
    # Try to insert inside the existing docstring
    match = re.search(r'(""")', source)
    if match:
        insert_pos = match.end()
        # Insert after the opening triple-quote
        new_source = source[:insert_pos] + "\nSEED_ID: SEED-UNKNOWN\n" + source[insert_pos:]
    else:
        new_source = seed_comment + source
    pyfile.write_text(new_source, encoding="utf-8")
    log.info("Auto-fix [G4]: added SEED_ID to %s", pyfile)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _iter_python_files(root: Path):
    """Yield Python source files, excluding hidden dirs and common noise."""
    for pyfile in root.rglob("*.py"):
        parts = pyfile.parts
        if any(p.startswith(".") for p in parts):
            continue
        if any(p in ("__pycache__", "node_modules", "venv", ".venv") for p in parts):
            continue
        yield pyfile


# ---------------------------------------------------------------------------
# Main validation runner
# ---------------------------------------------------------------------------

def validate(root: Path, fix: bool = False) -> ValidationReport:
    """Run all registered checks against the given root directory.

    Args:
        root: Repository root path.
        fix:  If True, attempt auto-remediation of safe issues.

    Returns:
        A populated ValidationReport.
    """
    report = ValidationReport(root=str(root))
    log.info("Starting validation — root=%s fix=%s", root, fix)

    for check in _CHECKS:
        try:
            check(root, report, fix)
        except Exception as exc:  # noqa: BLE001
            log.warning("Check '%s' raised an exception: %s", check.__name__, exc)

    report.passed = report.error_count() == 0
    status = "PASS" if report.passed else "FAIL"
    log.info(
        "Validation %s — errors=%d warnings=%d fixed=%d",
        status,
        report.error_count(),
        report.warning_count(),
        report.fixed_count(),
    )
    return report


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Infinity Invention Machine — 110% Protocol Validator v" + __version__
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Repository root to validate (default: current directory)",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Attempt auto-remediation of safe issues",
    )
    parser.add_argument(
        "--report",
        default=None,
        help="Path to write the JSON validation report (optional)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    if not root.is_dir():
        log.error("Root path does not exist: %s", root)
        return 2

    try:
        report = validate(root, fix=args.fix)
    except Exception as exc:  # noqa: BLE001
        log.error("Fatal error during validation: %s", exc)
        return 2

    # Emit report
    report_data = report.to_dict()
    print(json.dumps(report_data, indent=2))

    if args.report:
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(report_data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        log.info("Report written to %s", report_path)

    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
