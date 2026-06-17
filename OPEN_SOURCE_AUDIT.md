# Open Source Audit

## Snapshot

- Repo: `suchipizza/hellostress`
- Default branch: `main`
- Launch branch: `hellostress/open-source-baseline`
- Primary package entrypoint: `feacopilot`
- Current supported solver backends: `mock`, `docker`, `auto`

## Working Commands

```bash
python3 -m pip install -e '.[dev]'
make test
make example
make examples
make validate
```

Optional Docker-backed checks:

```bash
make validate-docker
RUN_DOCKER_SMOKE=1 pytest -q tests/test_integration_docker_smoke.py --run-docker-smoke
```

## What Already Exists

- landing-page style `README.md`
- agent guidance in `AGENTS.md`
- examples for beam, plate, simply supported beam, bracket screening, plate-with-hole screening, and hand-calculation comparison
- validation directories for analytical beam, public formula checks, Roark-style plate comparison, mesh convergence, and solver-comparison intake
- CI workflow with test and Docker smoke jobs
- issue templates, PR template, changelog, citation metadata, code of conduct, and security policy
- committed demo and social-preview assets

## Remaining Human-Orchestrated Work

- obtain one qualifying approval on PR `#3`
- merge PR `#3` into `main`
- publish the `v0.1.0` GitHub release after merge

## Risk Notes

- bracket and plate-with-hole workflows are analytical `mock`-mode screening only; Docker support is intentionally not claimed
- mesh convergence is committed as evidence, not presented as a solved monotonic convergence story
- there are local working-tree edits outside the published baseline branch history that should be reviewed intentionally before any separate PR

## Phase Status

- Phase 0 audit: complete
- Phase 1 README and metadata: substantially complete
- Phase 2 examples and quickstart: complete for current scope
- Phase 3 validation and benchmark: complete for current scope, with solver comparison still scaffolded
- Phase 4 contribution and agent-friendliness: complete
- Phase 5 CI, release, and devcontainer: complete in repo, pending GitHub release publication
