# Contributing

## Goal

This repository is being prepared as an open-source engineering prototype. Contributions should improve correctness, clarity, and operational safety before expanding scope.

## Before You Start

- Read [README.md](README.md) for current product scope.
- Read [docs/developer-guide.md](docs/developer-guide.md) for the Phase 1 architecture.
- Read [docs/phase-2-plan.md](docs/phase-2-plan.md) if you are working on the next hardening round.

## Local Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

## Required Checks

Run these before opening a PR:

```bash
python -m py_compile app.py fea_engine/*.py templates/*.py tests/*.py
PYTHONPATH=. pytest -q
```

Run the Docker-backed smoke path when you touch backend orchestration, artifact schemas, or CI:

```bash
docker pull dolfinx/dolfinx:v0.7.3
RUN_DOCKER_SMOKE=1 PYTHONPATH=. pytest -q tests/test_integration_docker_smoke.py --run-docker-smoke
```

## Contribution Rules

- Keep scope tight. Do not mix unrelated refactors into one change.
- Prefer explicit, typed validation over heuristic guessing.
- Preserve the current supported-scope contract unless the PR clearly expands it and adds tests.
- Add tests for behavior changes. Parser, validation, and template changes should not land without coverage.
- Do not commit local environment files, caches, or generated artifacts.

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
- Phase 2 service-layer prep that preserves current behavior
