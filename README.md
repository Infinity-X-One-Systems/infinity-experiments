# Infinity Invention Machine — Experiments

> **Protocol:** 110% | **Version:** 1.0.0 | **Status:** Active
>
> Autonomous system proving the recursive, simplified pattern of the Infinity X One core architecture.

---

## Architecture Overview

```
Discover → Generate → Validate → Deploy → Discover…
```

See [`docs/SYSTEM_ARCHITECTURE.md`](docs/SYSTEM_ARCHITECTURE.md) for the full design.
Governance rules are defined in [`GOVERNANCE.md`](GOVERNANCE.md).

---

## Repository Structure

```
.
├── docs/
│   ├── SYSTEM_ARCHITECTURE.md   # System design, 110% Protocol, three pillars
│   └── INDEX.md                 # Live central index
├── src/
│   ├── discovery/
│   │   ├── gap_finder.py        # Seed Idea scanner
│   │   └── manifest.json        # Seed registry
│   ├── genesis/
│   │   ├── scaffolder.py        # Project scaffolding engine
│   │   └── templates/           # Project skeleton templates
│   └── validation/
│       └── protocol_110.py      # 110% validation engine
├── .github/
│   └── workflows/
│       ├── infinity-pipeline.yml  # Main governance pipeline
│       └── deploy-docs.yml        # GitHub Pages deployment
├── GOVERNANCE.md                # Gates, guardrails, autonomous protocols
└── README.md                    # This file
```

---

## Command List — Step-by-Step Operator Guide

### Prerequisites

```bash
python --version   # Requires Python 3.10+
```

### Step 1 — Scan for Gaps (Discovery)

Run the gap finder against the repository root to identify system gaps and register them as Seed Ideas:

```bash
python src/discovery/gap_finder.py --root . --manifest src/discovery/manifest.json
```

New gaps are appended to `src/discovery/manifest.json` with status `IDENTIFIED`.

---

### Step 2 — Scaffold a Project (Genesis)

Pick a Seed ID from the manifest (e.g., `SEED-001`) and scaffold a new project:

```bash
python src/genesis/scaffolder.py \
  --seed SEED-001 \
  --output ./output/my-project \
  --manifest src/discovery/manifest.json
```

The seed status will be updated to `COMPLETE` on success.

---

### Step 3 — Validate (The Guardian)

Run the 110% Protocol validator to check all repository artifacts:

```bash
# Check only — reports errors without changing files
python src/validation/protocol_110.py --root .

# Auto-fix mode — attempts safe remediations
python src/validation/protocol_110.py --root . --fix

# Save a JSON report
python src/validation/protocol_110.py --root . --report ./reports/validation.json
```

Exit code `0` = all gates pass. Exit code `1` = gates failed.

---

### Step 4 — Trigger the Full Pipeline (Autonomous Cycle)

Push to any branch or open a PR against `main` to trigger the full pipeline automatically:

```bash
git add .
git commit -m "feat: describe your change"
git push origin your-branch
```

The pipeline runs:

1. **Lint** — `flake8`, `black`, `isort`
2. **Security** — `pip-audit`, `bandit`
3. **110% Validation** — `protocol_110.py`
4. **Deployment Gate** — labels PR `ready-for-deployment` when all gates pass

---

### Step 5 — Manual Pipeline Trigger

Trigger the pipeline without a code push via GitHub Actions:

1. Go to **Actions → Infinity Pipeline → Run workflow**.
2. Select the branch and click **Run workflow**.

---

### Step 6 — Deploy Documentation

Documentation is automatically deployed to GitHub Pages on every push to `main` that modifies `docs/`.

To trigger manually:

1. Go to **Actions → Deploy Docs to GitHub Pages → Run workflow**.

---

## The 110% Protocol Gates

| Gate | Name | Requirement |
|------|------|-------------|
| G1 | Zero Failure | Defensive error handling, no bare `except:` |
| G2 | Zero Tech Debt | Module docstrings, `__version__`, structured logging |
| G3 | Governance First | `GOVERNANCE.md` present, `SEED_ID` headers |
| G4 | Traceability | All artifacts reference a Seed ID in `manifest.json` |
| G5 | Scalability Hook | Every module exposes a `main()` entry point |

---

## Contributing

All changes must pass the full `infinity-pipeline.yml` gate suite before merge.
See [`GOVERNANCE.md`](GOVERNANCE.md) for amendment procedures.
