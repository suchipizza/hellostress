# Developer Guide

## Phase 1 Architecture

Phase 1 establishes a stricter contract around parsing and validation, and the current Phase 2 start point adds a service layer for orchestration:

- `fea_engine/models.py`: explicit geometry-specific data structures.
- `fea_engine/parser.py`: deterministic prompt parsing with LLM fallback.
- `fea_engine/validation.py`: supported-scope validation rules.
- `fea_engine/errors.py`: typed application errors for UI-safe handling.
- `fea_engine/service.py`: end-to-end simulation orchestration outside the Streamlit UI.

## Local Setup

1. Create and activate `.venv`.
2. Install runtime dependencies with `pip install -r requirements.txt`.
3. Install test dependencies with `pip install -r requirements-dev.txt`.

## Test Suite

- Unit tests live in `tests/test_parser.py` and `tests/test_validation.py`.
- Golden template tests live in `tests/test_generator_golden.py`.
- Run all tests with `pytest -q`.
- The gated Docker integration smoke test lives in `tests/test_integration_docker_smoke.py` and should be run with `RUN_DOCKER_SMOKE=1 PYTHONPATH=. pytest -q tests/test_integration_docker_smoke.py --run-docker-smoke`.

## Design Notes

- The parser is intentionally narrow. Unsupported or ambiguous prompts should fail clearly.
- Validation is separate from parsing so future API entry points can reuse the same rules.
- Golden tests are used to catch unintended script-template regressions.
- `SimulationService` is now the preferred entry point for app-level orchestration tests and future API/service extraction work.
- `FenicsSolver` now exposes a stricter artifact contract and only supports `mock`, `docker`, and `auto`.
- `app.py` should stay a UI shell. Presentation helpers belong in engine modules so they can be tested without Streamlit.

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

- normalized run status such as `completed` or `completed_with_fallback`
- backend mode and backend status
- metrics source
- fallback usage
- aggregated warnings
- embedded backend status and metadata payloads
- file paths for the backend artifacts
- serialized run metadata and runtime metadata

## Repository Standards

- Use `PYTHONPATH=. pytest -q` for local test runs.
- Keep local tooling artifacts out of Git via `.gitignore`.
- Treat `app.py` as the UI shell, not the orchestration layer.

## Next Documentation Targets

- Deployment guide for containerized execution
- Operations/runbook documentation
- API/service-layer documentation for non-Streamlit entry points
