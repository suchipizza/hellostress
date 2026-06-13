from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict

import streamlit as st
from dotenv import load_dotenv

from fea_engine import (
    FEACopilotError,
    FenicsScriptGenerator,
    FenicsSolver,
    PromptParser,
    ResultPostProcessor,
    ResultSummarizer,
    SimulationVisualizer,
)
from fea_engine.models import SimulationSpec

load_dotenv()

st.set_page_config(page_title="FEA Copilot", layout="wide")
st.title("HelloStress - FEA Copilot")
st.write(
    "Describe a simple beam or plate scenario in plain English. We'll parse it, "
    "generate a FEniCS script, and provide quick insights."
)

EXAMPLE_PROMPTS = {
    "Cantilever beam": "Simulate a 1 m long, 0.1 m thick steel cantilever beam with a 150 N downward tip load.",
    "Simply supported plate": "Analyze a 0.5 m by 0.3 m aluminum plate 5 mm thick under a uniform pressure of 50 kPa.",
}

with st.sidebar:
    st.header("Settings")
    solver_mode = st.selectbox("Solver mode", ["mock", "docker", "local", "auto"], index=0)
    mesh_density = st.slider("Mesh density", min_value=12, max_value=80, value=32, step=4)
    selected_example = st.selectbox("Example prompt", list(EXAMPLE_PROMPTS.keys()), index=0)
    if st.button("Use example"):
        st.session_state["prompt_text"] = EXAMPLE_PROMPTS[selected_example]
    st.markdown("---")
    st.caption("OpenAI API key is optional but enables better parsing + summaries.")

prompt_default = st.session_state.get("prompt_text", EXAMPLE_PROMPTS["Cantilever beam"])
prompt = st.text_area("Simulation prompt", value=prompt_default, height=140)
run_clicked = st.button("Run simulation", type="primary")
status_placeholder = st.empty()

parser = PromptParser()
generator = FenicsScriptGenerator()
postprocessor = ResultPostProcessor()
visualizer = SimulationVisualizer()
summarizer = ResultSummarizer()


def spec_to_dict(spec: SimulationSpec) -> Dict[str, Any]:
    data = asdict(spec)
    data["geometry"] = spec.geometry.value
    for load in data["loads"]:
        load["load_type"] = load["load_type"].value
    if spec.material:
        data["material"]["name"] = spec.material.name
    return data


if run_clicked:
    if not prompt.strip():
        st.error("Please provide a simulation prompt.")
    else:
        try:
            status_placeholder.info("Parsing prompt with heuristic + LLM assist…")
            spec = parser.parse(prompt)
            spec.mesh_density = mesh_density

            status_placeholder.info("Generating FEniCS script…")
            script = generator.render(spec)

            status_placeholder.info(f"Running solver in {solver_mode} mode…")
            solver = FenicsSolver(mode=solver_mode)
            artifacts = solver.run(spec, script)

            status_placeholder.info("Post-processing results…")
            metrics = postprocessor.collect_metrics(spec, artifacts)
            figure = visualizer.build_figure(spec, metrics)
            summary = summarizer.summarize(spec, metrics)

            status_placeholder.success("Simulation completed ✅")

            st.subheader("Results summary")
            st.write(summary)

            col1, col2 = st.columns(2)
            with col1:
                st.metric("Max deflection (mm)", f"{metrics.get('max_deflection', 0.0) * 1e3:.3f}")
            with col2:
                st.metric("Max stress (MPa)", f"{metrics.get('max_stress', 0.0) / 1e6:.2f}")

            st.plotly_chart(figure, use_container_width=True)

            st.subheader("Generated FEniCS script")
            st.code(script, language="python")
            st.download_button(
                label="Download script",
                file_name="simulation.py",
                mime="text/x-python",
                data=script,
            )

            st.subheader("Parsed specification")
            st.json(spec_to_dict(spec))
        except FEACopilotError as exc:
            status_placeholder.error(str(exc))
        except Exception as exc:  # pragma: no cover
            status_placeholder.error(f"Failed to complete simulation: {exc}")
