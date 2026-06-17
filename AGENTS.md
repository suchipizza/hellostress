# AGENTS.md

## Project Purpose

FEA Copilot is a narrow-scope open-source engineering tool that turns supported natural-language structural prompts into transparent, reproducible beam, plate, bracket, and plate-with-hole workflows. The repo is optimized for humans and coding agents to inspect, run, validate, and extend.

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e '.[dev]'
```

Optional Docker backend:

```bash
docker pull dolfinx/dolfinx:v0.7.3
```

## Run Tests

```bash
python3 -m py_compile app.py fea_engine/*.py templates/*.py tests/*.py tools/*.py validation/mesh_convergence/*.py validation/roark_formulas/*.py
pytest -q
python3 tools/check_markdown_links.py
```

Docker smoke path:

```bash
RUN_DOCKER_SMOKE=1 pytest -q tests/test_integration_docker_smoke.py --run-docker-smoke
```

## Run The Minimal Example

```bash
./examples/minimal/run.sh
```

Or directly:

```bash
feacopilot --prompt-file examples/minimal/prompt.txt --solver-mode mock --output json
```

## Project Structure

- `fea_engine/`: parser, validation, service orchestration, solver integration, artifact handling, and visualization.
- `templates/`: Jinja templates for generated solver scripts plus contributor scaffolds.
- `examples/`: runnable examples and extension stubs.
- `validation/`: committed comparisons, benchmark intake scaffolds, and convergence workflows.
- `docs/`: quickstart, architecture, validation, launch, and contribution docs.
- `.github/`: CI plus issue and PR templates.
- `tests/`: unit, golden, CLI, artifact, visualization, and gated Docker smoke tests.

## Rules For Modifying Examples

- Keep example commands reproducible from a fresh editable install.
- Every example directory should include `README.md`, `prompt.txt`, `run.sh`, and an expected-output artifact or note.
- If an example is analytical-only or backend-limited, state that explicitly and keep the script deterministic.
- Do not claim benchmark accuracy unless the reference result, source, tolerance, and command are committed in that example or validation case.

## Rules For Adding Validation Cases

- Include the problem definition, assumptions, reproducible command, reference result, tolerance, and source of truth.
- Prefer committed `expected_metrics.json` or a similarly machine-readable artifact.
- If the reference comes from a handbook or paper, cite the source in the case README and avoid paraphrasing it as if it were produced by the repository.
- Mesh convergence claims require either committed convergence data or a script that regenerates it.

## Rules For Solver Adapters

- Preserve the current public CLI and artifact contract unless there is a strong reason to change it.
- New adapters must write the same bundle shape: generated script, logs, metrics, `backend_status.json`, and `backend_metadata.json`.
- Unsupported environments should fail clearly with actionable messages.
- Add coverage in `tests/` for adapter behavior, error normalization, and artifact integrity.

## Definition Of Done For Agent Changes

- The change is scoped to a clear user-facing or contributor-facing outcome.
- Docs and examples stay consistent with the actual supported scope.
- Relevant tests pass locally, or the blocking reason is stated explicitly.
- New files are linked from the README or relevant docs.
- No fake badges, benchmark claims, citations, or community metrics are introduced.
