# Developer Guide

## Current Architecture

The Phase 1 and Phase 2 work established a stricter parsing and backend contract, and Phase 3 now adds a shared runtime configuration surface:

- `fea_engine/models.py`: explicit geometry-specific data structures.
- `fea_engine/parser.py`: deterministic prompt parsing with LLM fallback.
- `fea_engine/validation.py`: supported-scope validation rules.
- `fea_engine/errors.py`: typed application errors for UI-safe handling.
- `fea_engine/settings.py`: validated runtime settings sourced from environment variables.
- `fea_engine/service.py`: end-to-end simulation orchestration outside the Streamlit UI.
- `fea_engine/cli.py`: headless CLI entry point backed by the same service layer as the UI.

## Local Setup

1. Create and activate `.venv`.
2. Install the package and test extras with `pip install '.[dev]'`.

## Test Suite

- Unit tests live in `tests/test_parser.py` and `tests/test_validation.py`.
- Golden template tests live in `tests/test_generator_golden.py`.
- Run all tests with `pytest -q`.
- The CLI coverage lives in `tests/test_cli.py`.
- GitHub Actions also runs a CLI artifact workflow smoke path covering run creation, inspection, export, and cleanup.
- The gated Docker integration smoke test lives in `tests/test_integration_docker_smoke.py` and should be run with `RUN_DOCKER_SMOKE=1 pytest -q tests/test_integration_docker_smoke.py --run-docker-smoke`.

## Runtime Configuration

Phase 3 introduces a single runtime settings source consumed by the UI, service defaults, and CLI.

- `FEA_DEFAULT_SOLVER_MODE`: `mock`, `docker`, or `auto`
- `FEA_DEFAULT_MESH_DENSITY`: integer default for UI and CLI runs, validated in the `12` to `80` range
- `FEA_DOCKER_IMAGE`: Docker image used for backend execution
- `FEA_SOLVER_TIMEOUT_SECONDS`: backend timeout in seconds
- `FEA_RUNS_DIR`: workspace for generated run directories and artifacts
- `OPENAI_MODEL`: optional model override for parser/summarizer LLM assistance

Invalid values raise `ConfigurationError` early rather than silently falling back.

## CLI Usage

The installed console script uses the same `SimulationService` path as `app.py`:

```bash
feacopilot \
  --prompt "Simulate a 1 m long, 0.1 m thick steel cantilever beam with a 150 N downward tip load." \
  --solver-mode mock \
  --output json
```

Use this path for automation, reproducible debugging, and future non-Streamlit integrations.

For persisted runs, the CLI can inspect the artifact bundle without re-running the solver:

```bash
feacopilot --inspect-run-dir /path/to/run
feacopilot --inspect-run-result /path/to/run/run_result.json --output json
```

The CLI also supports operational workflows around the run workspace:

```bash
feacopilot --export-run-dir /path/to/run --export-output run-artifacts.zip
feacopilot --cleanup-runs --retention-days 14 --keep-latest 5 --dry-run
```

## Design Notes

- The parser is intentionally narrow. Unsupported or ambiguous prompts should fail clearly.
- Validation is separate from parsing so future API entry points can reuse the same rules.
- Golden tests are used to catch unintended script-template regressions.
- `SimulationService` is now the preferred entry point for app-level orchestration tests and future API/service extraction work.
- `FenicsSolver` now exposes a stricter artifact contract and only supports `mock`, `docker`, and `auto`.
- `app.py` should stay a UI shell. Presentation helpers belong in engine modules so they can be tested without Streamlit.
- Shared defaults should flow through `RuntimeSettings` instead of new ad hoc environment lookups.

## Solver Artifact Contract

`SolverArtifacts` is the backend boundary consumed by post-processing and service orchestration.

- `backend_mode`: the resolved backend used for the run
- `backend_status`: normalized backend execution status
- `run_dir`: working directory for the run
- `script_path`: generated script path
- `results_dir`: backend output directory
- `metrics_path`: canonical metrics file path
- `backend_status_path`: path to `backend_status.json`
- `backend_metadata_path`: path to `backend_metadata.json`
- `run_metadata`: command, exit code, timeout flag, stdout log path, stderr log path, and short excerpts
- `runtime_metadata`: normalized container lifecycle metadata, inspect state, and cleanup result
- `generated_files`: files produced by the backend
- `warnings`: backend or contract warnings

`SimulationService` is also responsible for normalizing backend failures into application-level `SimulationRunError` instances so UI layers do not need to reason about subprocess exceptions directly.

For Docker runs, the backend now uses an explicit `create` / `start` / `wait` / `logs` / `inspect` / `rm` lifecycle so artifact files can capture:

- container id
- start and finish timestamps
- container state from Docker inspect
- cleanup status after removal

## Final Run Result Schema

`SimulationService` writes `run_result.json` into the run directory after post-processing succeeds.

It captures:

- `schema_version` for the artifact contract
- normalized run status such as `completed` or `completed_with_fallback`
- backend mode and backend status
- metrics source
- fallback usage
- aggregated warnings
- embedded backend status and metadata payloads
- file paths for the backend artifacts
- serialized run metadata and runtime metadata

`backend_status.json` and `backend_metadata.json` now also carry `schema_version`, and `fea_engine.artifacts` provides reusable validation helpers for artifact consumers.

## Artifact Compatibility Policy

Phase 4 defines a machine-readable compatibility boundary for persisted run artifacts.

- `ARTIFACT_SCHEMA_VERSION` is the current writer version.
- `MIN_SUPPORTED_ARTIFACT_SCHEMA_VERSION` and `MAX_SUPPORTED_ARTIFACT_SCHEMA_VERSION` define the accepted read range.
- Inspection fails fast on unsupported schema versions instead of attempting a best-effort parse.
- Inspection diagnostics also verify referenced file presence and consistency between `run_result.json` embedded payloads and the referenced backend artifact files.
- Export first validates the bundle, then writes a zip archive rooted at the run directory.
- Export archives now include `export-manifest.json` with per-file relative paths, sizes, and SHA-256 checksums for downstream verification.
- Cleanup applies retention rules to direct child run directories in the configured workspace and supports `keep_latest` plus `dry_run`.
- Cleanup JSON output now includes summary counts and run-name lists so automation can react without scraping text output.

## Repository Standards

- Use `pytest -q` for local test runs after the editable install.
- Keep local tooling artifacts out of Git via `.gitignore`.
- Treat `app.py` as the UI shell, not the orchestration layer.
- Use [artifact-lifecycle-runbook.md](artifact-lifecycle-runbook.md) as the operational reference for inspection, export, and retention workflows.

## Next Documentation Targets

- Deployment guide for containerized execution
- Failure-handling and incident-response notes for backend troubleshooting
- API/service-layer documentation for non-Streamlit entry points
