# Phase 3 Plan

## Objective

Phase 3 focuses on making FEA Copilot easier to install, operate, and contribute to as an open-source project without expanding the supported simulation geometry scope.

## Scope

The target is a more production-shaped runtime surface around the existing narrow beam and plate workflow:

- shared runtime configuration
- a non-Streamlit entry point for automation
- package/install metadata
- clearer operator and contributor documentation
- CI paths that reflect the supported package and CLI usage

## Ticket Sequence

### P3-01. Shared Runtime Settings

- Introduce a validated settings module for runtime defaults and backend configuration.
- Replace scattered solver/runtime literals with configuration-backed defaults.
- Keep `app.py` as a thin UI shell that consumes shared settings.

Acceptance:

- One settings source defines default solver mode, mesh density, Docker image, solver timeout, run workspace, and OpenAI model.
- Invalid environment configuration fails clearly.
- Service and UI layers consume the same defaults.

### P3-02. Headless CLI Runner

- Add a CLI entry point for non-UI execution of a simulation prompt.
- Return structured output that references generated artifacts rather than inventing a second result contract.

Acceptance:

- Contributors can run a prompt in `mock`, `docker`, or `auto` mode without Streamlit.
- CLI output includes run status, metrics, warnings, and artifact paths.
- Recoverable application failures exit non-zero with a readable error.

### P3-03. Packaging and Install Surface

- Add standard Python package metadata and a console script entry point.
- Align local development instructions with editable installs.

Acceptance:

- `pip install '.[dev]'` works on a clean environment.
- A `feacopilot` console script is installed.
- CI validates the package installation path.

### P3-04. Documentation and CI Alignment

- Document runtime configuration, CLI usage, and artifact locations for contributors and operators.
- Add CI coverage for the package-backed CLI mock path while preserving the gated Docker smoke test.

Acceptance:

- README and developer docs cover install, env vars, CLI usage, and backend/runtime knobs.
- CI runs the unit suite plus a CLI smoke path from the installed package.
- Existing Docker smoke coverage remains in place for the real backend path.

## Out of Scope

- new geometry families
- broad API/server deployment infrastructure
- multi-user orchestration
- certified engineering or production-accuracy claims
