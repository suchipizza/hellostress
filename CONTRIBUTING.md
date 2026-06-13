# Contributing

## Goal

This repository is being prepared as an open-source engineering prototype. Contributions should improve correctness, clarity, and operational safety before expanding scope.

## Before You Start

- Read [README.md](README.md) for current product scope.
- Read [docs/developer-guide.md](docs/developer-guide.md) for the current architecture.
- Read [docs/phase-2-plan.md](docs/phase-2-plan.md) for the backend hardening closeout.
- Read [docs/phase-3-plan.md](docs/phase-3-plan.md) for the OSS-readiness closeout.
- Read [docs/phase-4-plan.md](docs/phase-4-plan.md) for the current artifact-contract workstream.

## Local Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install '.[dev]'
```

## Required Checks

Run these before opening a PR:

```bash
python -m py_compile app.py fea_engine/*.py templates/*.py tests/*.py
pytest -q
```

Run the Docker-backed smoke path when you touch backend orchestration, artifact schemas, or CI:

```bash
docker pull dolfinx/dolfinx:v0.7.3
RUN_DOCKER_SMOKE=1 pytest -q tests/test_integration_docker_smoke.py --run-docker-smoke
```

## Contribution Rules

- Keep scope tight. Do not mix unrelated refactors into one change.
- Prefer explicit, typed validation over heuristic guessing.
- Preserve the current supported-scope contract unless the PR clearly expands it and adds tests.
- Add tests for behavior changes. Parser, validation, and template changes should not land without coverage.
- Do not commit local environment files, caches, or generated artifacts.
- Route new shared runtime defaults through `fea_engine/settings.py` rather than new ad hoc environment lookups.

## Pull Request Expectations

Each PR should explain:

- what changed
- why it changed
- user or developer impact
- validation used

## Code Review Priorities

Review should focus on:

- parsing correctness
- simulation contract integrity
- behavioral regressions
- unsupported-case handling
- test completeness

## Good First Contributions

- parser edge-case tests
- clearer validation errors
- documentation improvements
- CI and developer-experience improvements
- Phase 3 packaging, CLI, and configuration improvements that preserve current behavior
