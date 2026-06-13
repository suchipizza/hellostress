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

## Design Notes

- The parser is intentionally narrow. Unsupported or ambiguous prompts should fail clearly.
- Validation is separate from parsing so future API entry points can reuse the same rules.
- Golden tests are used to catch unintended script-template regressions.
- `SimulationService` is now the preferred entry point for app-level orchestration tests and future API/service extraction work.

## Repository Standards

- Use `PYTHONPATH=. pytest -q` for local test runs.
- Keep local tooling artifacts out of Git via `.gitignore`.
- Treat `app.py` as the UI shell, not the orchestration layer.

## Next Documentation Targets

- Deployment guide for containerized execution
- Operations/runbook documentation
- API/service-layer documentation once the UI orchestration is extracted
