# Architecture

## Runtime Shape

FEA Copilot has one core orchestration path used by both the CLI and the Streamlit app:

1. parse a prompt into `SimulationSpec`
2. validate the supported scope
3. render a generated solver script
4. run a backend in `mock`, `docker`, or `auto` mode
5. collect metrics and write artifact files
6. summarize and visualize the result

## Main Modules

- `fea_engine/models.py`: geometry, material, load, and result data structures.
- `fea_engine/parser.py`: deterministic prompt parsing with optional OpenAI-assisted extraction.
- `fea_engine/validation.py`: explicit supported-scope validation rules.
- `fea_engine/generator.py`: Jinja-backed solver script rendering.
- `fea_engine/solver.py`: backend execution and artifact creation for `mock` and Docker modes.
- `fea_engine/postprocessor.py`: metrics collection and fallback logic.
- `fea_engine/artifacts.py`: artifact inspection, export, workspace policy, and cleanup.
- `fea_engine/service.py`: end-to-end orchestration used by the CLI and UI.
- `fea_engine/cli.py`: automation-friendly entry point for execution and artifact workflows.

## Artifact Contract

Each successful run writes a bundle with:

- `run_result.json`
- `backend_status.json`
- `backend_metadata.json`
- `solver.stdout.log`
- `solver.stderr.log`
- generated `simulation.py`
- `results/metrics.json`

Docker-backed runs may also emit additional field files under `results/`.

## Design Constraints

- The parser should fail clearly on unsupported or ambiguous prompts.
- The CLI is the preferred reproducible interface for examples, tests, and automation.
- `mock` mode is intentionally fast and deterministic for smoke tests.
- Docker mode is the intended path for generated DOLFINx execution.
- Validation claims require committed evidence in `validation/`, not just README prose.

## Extension Points

- `templates/new_solver_adapter/`: adding a new backend while preserving the artifact contract.
- `templates/new_benchmark_case/`: adding a new validation or benchmark case with reproducible evidence.
- `examples/`: adding user-facing runnable workflows or explicit unsupported-case scaffolds.

See [docs/developer-guide.md](developer-guide.md) for lower-level implementation notes.
