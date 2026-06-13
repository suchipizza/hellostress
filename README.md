# HelloStress FEA Copilot

FEA Copilot is a narrow-scope structural simulation prototype that turns supported natural-language beam and plate prompts into structured specs, generated FEniCS scripts, quick estimates, and result summaries.

Phase 2 closed out the backend hardening round. Phase 3 is complete, and Phase 4 has started on artifact-contract versioning and inspection for automation and operations.

## Current Scope

This project is intentionally narrow right now.

- Supported beam prompts must clearly include geometry, section size, and a load with units.
- Supported plate prompts must clearly include rectangular plan dimensions, thickness, and pressure with units.
- Mock mode provides analytical estimates.
- Docker mode is the intended path for generated FEniCS execution.
- Host-local execution is not a supported backend.

Unsupported or ambiguous prompts should fail clearly rather than return plausible nonsense.

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install '.[dev]'
streamlit run app.py
```

The default runtime uses the fast `mock` solver. To prepare Docker-backed execution:

```bash
docker pull dolfinx/dolfinx:v0.7.3
```

You can also run the service headlessly:

```bash
feacopilot \
  --prompt "Simulate a 1 m long, 0.1 m thick steel cantilever beam with a 150 N downward tip load." \
  --solver-mode mock \
  --output json
```

## Example Prompts

- `Simulate a 1 m long, 0.1 m thick steel cantilever beam with a 150 N downward tip load.`
- `Analyze a 0.5 m by 0.3 m aluminum plate 5 mm thick under a uniform pressure of 50 kPa.`

## Environment Variables

- `OPENAI_API_KEY`: optional. Enables GPT-assisted parsing and summarization.
- `OPENAI_MODEL`: optional model override for the OpenAI client.
- `FEA_DEFAULT_SOLVER_MODE`: optional default solver mode for the UI and CLI. Supported values: `mock`, `docker`, `auto`.
- `FEA_DEFAULT_MESH_DENSITY`: optional default mesh density for the UI and CLI. Supported range: `12` to `80`.
- `FEA_DOCKER_IMAGE`: optional Docker image override for solver execution.
- `FEA_SOLVER_TIMEOUT_SECONDS`: optional backend timeout override in seconds.
- `FEA_RUNS_DIR`: optional workspace directory for generated runs and artifacts.

You can place these in a local `.env` file.

## Headless CLI

The `feacopilot` console script runs the same service layer used by the app and writes the normal backend artifacts into the configured run workspace.

Common examples:

```bash
feacopilot --prompt "Analyze a 0.5 m by 0.3 m aluminum plate 5 mm thick under a uniform pressure of 50 kPa."
feacopilot --prompt-file prompt.txt --output json
```

CLI JSON output includes status, metrics, warnings, parsed spec details, and the paths to `run_result.json`, `backend_status.json`, `backend_metadata.json`, and `metrics.json`.

You can also inspect a completed run without re-executing it:

```bash
feacopilot --inspect-run-dir /path/to/run
feacopilot --inspect-run-result /path/to/run/run_result.json --output json
```

## Local Development

Run the checks used in this repository:

```bash
python -m py_compile app.py fea_engine/*.py templates/*.py tests/*.py
pytest -q
```

The Docker-backed smoke test is gated and should be run when backend orchestration or artifact contracts change:

```bash
docker pull dolfinx/dolfinx:v0.7.3
RUN_DOCKER_SMOKE=1 pytest -q tests/test_integration_docker_smoke.py --run-docker-smoke
```

## Solver Backend Contract

The current service and backend path produces a structured solver artifact contract:

- `backend_mode`: resolved backend used for execution
- `backend_status`: normalized backend status such as `succeeded`, `failed`, or `timed_out`
- `run_dir`: working directory for the run
- `script_path`: generated simulation script written for the run
- `results_dir`: directory for solver outputs
- `metrics_path`: expected `metrics.json` path
- `backend_status_path`: JSON file describing backend execution status
- `backend_metadata_path`: JSON file describing backend metadata such as Docker image/version
- `run_metadata`: structured command, exit code, timeout, and stdout/stderr diagnostics
- `runtime_metadata`: container lifecycle metadata including container id, timing, state, and cleanup status
- `generated_files`: files actually produced by the backend
- `warnings`: contract or backend warnings surfaced to the application layer

The service layer also writes `run_result.json`, which normalizes:

- final application status
- backend execution status
- backend status and metadata payloads
- metrics source
- whether analytical fallback was used
- warning aggregation across backend and post-processing

As of Phase 4, `backend_status.json`, `backend_metadata.json`, and `run_result.json` also carry an explicit `schema_version` field so automation can validate the contract before consuming a run.

The current compatibility policy is strict and explicit:

- supported artifact bundles must declare a `schema_version` within the currently supported range
- the CLI inspection path validates referenced files and checks that embedded payloads match the referenced backend artifact files
- unsupported schema versions fail fast instead of being interpreted optimistically

## Contributing

Start with [CONTRIBUTING.md](CONTRIBUTING.md).

Relevant docs:

- [docs/user-guide.md](docs/user-guide.md)
- [docs/developer-guide.md](docs/developer-guide.md)
- [docs/phase-2-plan.md](docs/phase-2-plan.md)
- [docs/phase-3-plan.md](docs/phase-3-plan.md)
- [docs/phase-4-plan.md](docs/phase-4-plan.md)

## Repository Layout

```
feacopilot/
├── app.py
├── fea_engine/
├── templates/
├── tests/
├── docs/
├── requirements.txt
├── requirements-dev.txt
├── CONTRIBUTING.md
└── README.md
```

## Phase Status

- Phase 2 is complete on `main`.
- Phase 3 is complete on `main`.
- Phase 4 is in progress with artifact-contract versioning and inspection work.

## Disclaimer

Results are for educational and preliminary design purposes only and are **not** certified for production use.
