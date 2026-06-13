# User Guide

## Overview

FEA Copilot converts a narrow set of natural-language beam and plate prompts into quick structural simulations. In Phase 1, the supported scope is intentionally limited to:

- Beam prompts that clearly specify length, section thickness or height, and load with units.
- Plate prompts that clearly specify rectangular plan dimensions, thickness, and pressure with units.

## Quick Start

1. Create and activate a virtual environment.
2. Install the package with `pip install .`.
3. Launch the app with `streamlit run app.py`.
4. Start with one of the built-in example prompts.

You can also run a supported prompt without the UI:

```bash
feacopilot --prompt "Simulate a 1 m long, 0.1 m thick steel cantilever beam with a 150 N downward tip load."
```

To inspect a finished run:

```bash
feacopilot --inspect-run-dir /path/to/run
```

To export or clean up runs:

```bash
feacopilot --export-run-dir /path/to/run --export-output run-artifacts.zip
feacopilot --cleanup-runs --retention-days 14 --keep-latest 5 --dry-run
```

## Supported Prompt Patterns

- Beam: `1 m long steel cantilever beam 0.1 m thick with a 150 N downward tip load`
- Plate: `0.5 m by 0.3 m aluminum plate 5 mm thick under 50 kPa pressure`

## Current Constraints

- Plate simulations currently support pressure loads only.
- Beam width defaults to beam height when width is omitted.
- Mock mode provides analytical estimates, not a certified FEA sign-off.
- Supported solver backends are `mock`, `docker`, and `auto`.
- Host-local solver execution is intentionally not supported.
- Backend failures are normalized into user-facing solver errors with log context.
- Successful runs now include backend status and metadata artifacts in the run directory for debugging.
- The CLI writes the same backend artifacts as the app, including `run_result.json`.
- Run artifacts now include a `schema_version` field for contract validation.
- The CLI inspection command now reports compatibility status, referenced file presence, and artifact consistency checks.
- The CLI export command writes a validated zip archive of a completed run.
- The CLI cleanup command applies retention rules to the run workspace and can preview deletions with `--dry-run`.
- If a prompt is ambiguous or missing units, the app now fails explicitly instead of guessing.

## Runtime Defaults

Optional environment variables:

- `FEA_DEFAULT_SOLVER_MODE`
- `FEA_DEFAULT_MESH_DENSITY`
- `FEA_DOCKER_IMAGE`
- `FEA_SOLVER_TIMEOUT_SECONDS`
- `FEA_RUNS_DIR`
- `OPENAI_API_KEY`
- `OPENAI_MODEL`

## Troubleshooting

- `Prompt must mention either a beam or a plate`: add the geometry explicitly.
- `Could not determine the load magnitude and units`: include units such as `N`, `kN`, `kPa`, or `MPa`.
- `Could not determine beam thickness/height`: include a section size such as `50 mm thick`.
- `Invalid FEA_DEFAULT_SOLVER_MODE ...`: set the variable to `mock`, `docker`, or `auto`.
