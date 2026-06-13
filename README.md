# 🧠 FEA Copilot MVP

Natural-language assistant that converts prompts for simple beam/plate simulations into FEniCS scripts, runs them, and visualizes the results in Streamlit.

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

The app defaults to a fast **mock** solver that uses analytical closed-form estimates. Switch to `docker` mode in the sidebar to execute the generated script with FEniCS:

```bash
docker pull dolfinx/dolfinx:v0.7.3
```

## Environment Variables

- `OPENAI_API_KEY` – optional. Enables GPT-assisted parsing + result summarization.
- `OPENAI_MODEL` – override the default `gpt-4o-mini` model name (optional).

You can create a `.env` file in the project root so the Streamlit app picks it up automatically.

## Project Layout

```
feacopilot/
├── app.py                  # Streamlit UI
├── requirements.txt
├── README.md
├── fea_engine/
│   ├── __init__.py
│   ├── llm_client.py       # OpenAI Responses helper
│   ├── models.py           # Dataclasses for specs/results
│   ├── parser.py           # Prompt → structured spec
│   ├── generator.py        # Spec → FEniCS script (Jinja templates)
│   ├── solver.py           # Docker/local/mock execution wrapper
│   ├── postprocessor.py    # Loads solver metrics
│   ├── visualizer.py       # Plotly figures
│   ├── summarizer.py       # LLM + fallback summary text
│   └── utils.py            # Analytical beam/plate estimates
└── templates/
    ├── beam_template.py
    └── plate_template.py
```

## Usage Notes

1. Enter a natural-language description (e.g., *"1 m steel cantilever beam with 100 N downward tip load"*).
2. Pick the solver mode & mesh density from the sidebar.
3. Click **Run simulation**. The pipeline will:
   - Parse the prompt (LLM + heuristics)
   - Generate and optionally execute a FEniCS script
   - Post-process & visualize key metrics
   - Summarize the outcome in plain language

If Docker/FEniCS is unavailable, the mock mode still provides ballpark deflection/stress numbers via classical formulas.

## Testing & Linting

The MVP does not ship with a test suite yet; recommended next steps include:
- Unit tests for `PromptParser` heuristics
- Golden tests for template generation
- Integration test that exercises the mock solver path

## Disclaimer

Results are for educational and preliminary design purposes only and are **not** certified for production use.
