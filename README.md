# 🧠 FEA Copilot

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

## Phase 2 Preparation

Phase 2 is the backend hardening round. The current preparation artifacts are:

- a contributor guide with repository standards
- a documented Phase 2 ticket sequence
- CI automation for parser and template regressions

See [docs/phase-2-plan.md](docs/phase-2-plan.md) for the concrete work queue.

## Disclaimer

Results are for educational and preliminary design purposes only and are **not** certified for production use.
