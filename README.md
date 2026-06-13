# HelloStress 🧠 FEA Copilot

FEA Copilot is a Streamlit-based prototype that converts a narrow class of natural-language structural prompts into structured simulation specs, generated FEniCS scripts, quick estimates, and result summaries.

The repository is now on a clean open-source `main` branch with Phase 1 correctness work in place:

- explicit beam and plate data models
- parser validation and typed user-facing errors
- parser regression tests and golden script tests
- user and developer documentation

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
pip install -r requirements-dev.txt
streamlit run app.py
```

The app defaults to the fast `mock` solver. To prepare Docker-backed execution:

```bash
docker pull dolfinx/dolfinx:v0.7.3
```

## Example Prompts

- `Simulate a 1 m long, 0.1 m thick steel cantilever beam with a 150 N downward tip load.`
- `Analyze a 0.5 m by 0.3 m aluminum plate 5 mm thick under a uniform pressure of 50 kPa.`

## Environment Variables

- `OPENAI_API_KEY`: optional. Enables GPT-assisted parsing and summarization.
- `OPENAI_MODEL`: optional model override for the OpenAI client.

You can place these in a local `.env` file.

## Local Development

Run the checks used in this repository:

```bash
python -m py_compile app.py fea_engine/*.py templates/*.py tests/*.py
PYTHONPATH=. pytest -q
```

The Docker-backed smoke test is gated and only runs when explicitly enabled:

```bash
docker pull dolfinx/dolfinx:v0.7.3
RUN_DOCKER_SMOKE=1 PYTHONPATH=. pytest -q tests/test_integration_docker_smoke.py --run-docker-smoke
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

## Contributing

Start with [CONTRIBUTING.md](CONTRIBUTING.md).

Relevant docs:

- [docs/user-guide.md](docs/user-guide.md)
- [docs/developer-guide.md](docs/developer-guide.md)
- [docs/phase-2-plan.md](docs/phase-2-plan.md)

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

## Phase 2 Status

Phase 2 is complete on `main`.

The closeout work delivered:

- a thin UI shell in `app.py`, with orchestration and presentation helpers extracted into the engine layer
- explicit backend artifact files and a normalized `run_result.json` schema
- Docker lifecycle hardening with container state inspection and cleanup status capture
- gated CI smoke coverage for the real container-backed execution path

See [docs/phase-2-plan.md](docs/phase-2-plan.md) for the closeout record.

## Disclaimer

Results are for educational and preliminary design purposes only and are **not** certified for production use.
