# Phase 2 Plan

## Objective

Phase 2 is the backend hardening round. The goal is to move the project from a correctness-focused prototype to a safer execution architecture with explicit backend contracts.

## Current Progress

- `SimulationService` has been introduced in `fea_engine/service.py`.
- `app.py` now delegates the simulation pipeline to the service layer.
- Service-level tests cover orchestration and the real mock backend path.

## Workstreams

### 1. Extract orchestration from the UI

- Move parse, generate, solve, post-process, and summarize orchestration out of `app.py`.
- Introduce an application service module that the UI can call.
- Keep behavior stable while reducing Streamlit-specific coupling.

Acceptance:

- `app.py` becomes a thin UI wrapper.
- The core pipeline is callable from tests without Streamlit.

Status:

- In progress. The first extraction is complete; follow-up work should keep moving orchestration concerns out of the UI and into stable service interfaces.

### 2. Remove unsafe local execution from the supported path

- Deprecate or remove host-local execution of generated scripts.
- Keep `mock` and `docker` as the supported backends.

Acceptance:

- No production-facing path executes generated solver code directly on the host.

### 3. Define a solver artifact contract

- Standardize the expected results layout from each backend.
- Document required and optional files and the metrics schema.

Acceptance:

- Post-processing consumes a defined contract rather than backend-specific assumptions.

### 4. Harden Docker solver execution

- Add explicit error capture, timeout handling, and cleanup guarantees.
- Normalize solver failures into structured errors.

Acceptance:

- Docker failures produce predictable application errors and leave no ambiguous state.

### 5. Add integration coverage for backend execution

- Add mock backend integration coverage.
- Add a docker-backed smoke path that can run in CI when available.

Acceptance:

- Phase 2 behavior is covered beyond parser-only tests.

## Suggested Ticket Sequence

1. Create `fea_engine/service.py` or equivalent pipeline module.
2. Move `app.py` orchestration into the service layer.
3. Update tests to cover service-level execution.
4. Remove or disable `local` solver mode from the UI and backend contract.
5. Introduce a structured solver artifact/result model.
6. Harden Docker execution and failure handling.
7. Add integration tests for `mock`.
8. Add CI support for backend smoke coverage where practical.

## Out of Scope for Phase 2

- broad new geometry support
- production deployment infrastructure
- authentication or multi-user serving
- claims of certified engineering accuracy

## Dependencies for Contributors

- Keep all Phase 1 parser and golden tests passing.
- Preserve narrow supported scope unless explicitly expanding it with tests and docs.
