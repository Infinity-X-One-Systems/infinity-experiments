# Governance — Infinity Invention Machine

> **Protocol:** TAP (Policy → Authority → Truth)
> **Version:** 1.0.0

---

## 1. The TAP Protocol

All decisions within this system are resolved in strict priority order:

1. **Policy** — The rules defined in this file and `docs/SYSTEM_ARCHITECTURE.md`.
2. **Authority** — The GitHub Actions pipeline (`.github/workflows/`).
3. **Truth** — The runtime output of `src/validation/protocol_110.py`.

No human override may bypass Gate G3 (Governance First) without an explicit, documented exception logged in `docs/INDEX.md`.

---

## 2. Deployment Gates

A commit may only be merged to `main` when **all** of the following gates pass in CI:

| Gate ID | Name | Enforced By |
|---------|------|-------------|
| G1 | Zero Failure | `protocol_110.py` + linter exit codes |
| G2 | Zero Tech Debt | `protocol_110.py` docstring/comment check |
| G3 | Governance First | Presence of `GOVERNANCE.md` and `SEED_ID` header |
| G4 | Traceability | `manifest.json` contains matching seed record |
| G5 | Scalability Hook | Module exposes required public interface |

---

## 3. Autonomous Decision-Making Protocols

### 3.1 Auto-Fix Scope

The validation engine (`protocol_110.py`) is authorised to automatically remediate:

- Missing `__version__` strings (set to `0.0.1-auto`)
- Missing `SEED_ID` header comments (set to `SEED-UNKNOWN`)
- Missing module-level docstrings (stub inserted)
- Trailing whitespace and inconsistent line endings

The engine must **not** auto-fix:

- Logic errors or failed tests
- Security vulnerabilities flagged by the scanner
- Missing business logic (only the operator may fill these gaps)

### 3.2 Escalation Protocol

If any gate fails after auto-fix attempts, the pipeline must:

1. Emit a structured failure report to the Actions log.
2. Label the PR with `governance-blocked`.
3. Halt all subsequent pipeline steps.

### 3.3 Autonomous Cycle Triggers

The pipeline may be triggered autonomously by:

- Push to any branch (lint + validation only)
- Pull Request targeting `main` (full gate suite)
- Manual `workflow_dispatch` (operator-initiated)
- Scheduled run every 24 hours (drift detection)

---

## 4. Security Guardrails

- **Secret scanning** is mandatory on every push. Any detected secret blocks the pipeline immediately.
- **Dependency audit** (`pip audit` / `safety`) runs on every PR.
- No external network calls are permitted from `src/` modules during CI without explicit approval documented here.

---

## 5. Versioning Policy

- Semantic versioning (`MAJOR.MINOR.PATCH`) is enforced.
- Every module `__version__` must match the repository tag on release.
- Breaking changes to public interfaces require a `MAJOR` bump and a `GOVERNANCE.md` amendment.

---

## 6. Amendments

This file is the root policy document. Amendments require:

1. A PR with the label `governance-amendment`.
2. Approval from at least one human operator.
3. An entry added to the `docs/INDEX.md` changelog.
