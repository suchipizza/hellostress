# Contributing

## What We Want Contributions To Improve

This repository is intentionally narrow. The best contributions improve one of these areas without hiding assumptions:

- correctness of parsing, validation, and artifact handling
- reproducibility of examples and validation cases
- clarity of engineering assumptions and limitations
- contributor ergonomics for adapters, benchmarks, and documentation

## Before You Start

- Read [README.md](README.md) for current scope.
- Read [AGENTS.md](AGENTS.md) for agent-facing repo rules.
- Read [docs/quickstart.md](docs/quickstart.md) and [docs/architecture.md](docs/architecture.md).
- Check [ROADMAP.md](ROADMAP.md) and [docs/contributing_examples.md](docs/contributing_examples.md) for scoped issue ideas.

## Local Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e '.[dev]'
```

## Required Checks

Run these before opening a PR:

```bash
make test
make examples
make validate
```

Run the Docker smoke path when you touch backend orchestration, script templates, or validation workflows that depend on DOLFINx:

```bash
docker pull dolfinx/dolfinx:v0.7.3
RUN_DOCKER_SMOKE=1 pytest -q tests/test_integration_docker_smoke.py --run-docker-smoke
```

## Pull Request Rules

- Keep scope tight. Do not mix unrelated refactors into one PR.
- Preserve current public APIs unless the change clearly needs an API update and adds tests/docs.
- Add or update tests for behavior changes.
- Add or update example or validation docs when the supported workflow changes.
- Do not commit local caches, `.venv`, generated run bundles, or machine-specific output paths.
- Be explicit about unsupported cases instead of adding vague fallback behavior.

## Example And Benchmark Contributions

- Follow the structure in `examples/` and `validation/`.
- Prefer the starter scaffolds under `templates/new_example_case/`, `templates/new_validation_case/`, `templates/new_solver_adapter/`, and `templates/new_exporter/`.
- Every new case needs a reproducible command and a written assumptions section.
- Benchmark cases need a reference result, tolerance, and source citation if applicable.
- If a case is only scaffolded, mark it `TODO` and describe what evidence is missing.

## Review Priorities

- parsing correctness
- regression risk in service and artifact flows
- unsupported-case behavior
- evidence for validation claims
- clarity of docs and examples for external contributors

## Good First Contributions

- add one sourced validation case
- improve one example README or expected-output artifact
- add a mesh convergence data script and plot
- expand CLI error messages for unsupported prompts
- add teaching-oriented docs around assumptions and boundary conditions
