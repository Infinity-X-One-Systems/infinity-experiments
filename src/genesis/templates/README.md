# Genesis Templates

This directory contains versioned project skeleton templates used by `scaffolder.py`.

## Available Templates

| Template | Description |
|----------|-------------|
| `python_module/` | Standard 110%-compliant Python module scaffold |
| `governance/` | Governance document scaffold for a new policy area |

## Adding a New Template

1. Create a subdirectory: `templates/<template_name>/`
2. Add `template_manifest.json` — describes the files to generate.
3. Add template files using `${VARIABLE}` substitution syntax.
4. Register the template in `scaffolder.py`'s `_GATE_TEMPLATE_MAP`.

## Template Variables

| Variable | Description |
|----------|-------------|
| `${SEED_ID}` | Seed ID from manifest.json |
| `${SEED_DESCRIPTION}` | Human-readable description of the seed |
| `${MODULE_NAME}` | Slugified module name derived from the description |
| `${DATE}` | Generation date (YYYY-MM-DD) |
| `${VERSION}` | Initial version string |
| `${GATE}` | Primary 110% Protocol gate for this seed |
