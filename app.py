from __future__ import annotations

import importlib
import sys

import streamlit as st
from dotenv import load_dotenv

from fea_engine import (
    ConfigurationError,
    FEACopilotError,
    RuntimeSettings,
    SimulationService,
)
from fea_engine.presentation import spec_to_display_dict

load_dotenv()


def _extract_pyvista_warning(warnings: list[str]) -> str | None:
    for warning in warnings:
        if warning.startswith("PyVista preview unavailable:"):
            return warning
    return None


def _build_runtime_diagnostics() -> dict[str, str]:
    diagnostics = {"python": sys.executable}
    for module_name in ("h5py", "pyvista"):
        try:
            module = importlib.import_module(module_name)
            diagnostics[module_name] = f"ok ({getattr(module, '__version__', 'unknown version')})"
        except Exception as exc:
            diagnostics[module_name] = f"error ({exc})"
    return diagnostics


def _build_dependency_help(result) -> str | None:
    warning_text = " | ".join(result.warnings)
    if "No module named 'h5py'" in warning_text:
        return (
            "This Streamlit process cannot import `h5py`, so it cannot read the solver's "
            "`displacement.xdmf` / `stress.xdmf` HDF5 payloads. Install dependencies into the "
            "same Python used to launch the app, then restart it: "
            "`python3 -m pip install h5py pyvista` and run `python3 -m streamlit run app.py`."
        )
    if "No module named 'pyvista'" in warning_text:
        return (
            "This Streamlit process cannot import `pyvista`. Install it into the same Python "
            "used to launch the app, then restart it: `python3 -m pip install pyvista` and run "
            "`python3 -m streamlit run app.py`."
        )
    return None


def _format_deflection_mm(value_m: float) -> str:
    value_mm = value_m * 1e3
    magnitude = abs(value_mm)
    if magnitude >= 1.0:
        return f"{value_mm:.3f}"
    if magnitude >= 1e-3:
        return f"{value_mm:.6f}"
    return f"{value_mm:.3e}"


def _build_non_field_visualization_message(result) -> str:
    source = result.visualization_source.replace("_", " ")
    backend = getattr(result, "solver_mode", "unknown")
    details: list[str] = [
        f"Current result uses `{source}` visualization from backend `{backend}`.",
        "PyVista is only available for runs that produced real solver field artifacts.",
    ]
    if result.warnings:
        details.append(f"Run warnings: {' | '.join(result.warnings)}")
    return " ".join(details)


def _ensure_pyvista_preview(
    result,
    simulation_service: SimulationService,
) -> tuple[object | None, str | None]:
    if result.pyvista_image is not None:
        return result.pyvista_image, None
    if result.visualization_source != "solver_field":
        return None, _build_non_field_visualization_message(result)

    try:
        visualization = simulation_service.visualizer.build_visualization(
            result.spec,
            result.metrics,
            result.artifacts,
        )
    except Exception as exc:  # pragma: no cover - defensive UI retry path
        return None, f"PyVista preview unavailable: {exc}"

    if visualization.pyvista_image is not None:
        result.pyvista_image = visualization.pyvista_image
        return visualization.pyvista_image, None
    return None, _extract_pyvista_warning(visualization.warnings)


def _render_result(result, simulation_service: SimulationService) -> None:
    st.subheader("Results summary")
    st.write(result.summary)

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Max deflection (mm)", _format_deflection_mm(result.metrics.get("max_deflection", 0.0)))
    with col2:
        st.metric("Max stress (MPa)", f"{result.metrics.get('max_stress', 0.0) / 1e6:.2f}")

    st.subheader("Visualizations")
    st.caption(f"Visualization source: {result.visualization_source.replace('_', ' ')}")
    plotly_tab, pyvista_tab = st.tabs(["Plotly", "PyVista"])
    with plotly_tab:
        st.plotly_chart(result.figure, use_container_width=True)
    with pyvista_tab:
        pyvista_image, pyvista_warning = _ensure_pyvista_preview(result, simulation_service)
        if pyvista_image is not None:
            st.image(pyvista_image, use_container_width=True)
        else:
            if pyvista_warning is not None:
                st.warning(pyvista_warning)
            else:
                st.info("PyVista preview is unavailable for this run.")

    st.subheader("Generated FEniCS script")
    st.code(result.script, language="python")
    st.download_button(
        label="Download script",
        file_name="simulation.py",
        mime="text/x-python",
        data=result.script,
    )

    st.subheader("Parsed specification")
    st.json(spec_to_display_dict(result.spec))
    if result.warnings:
        st.subheader("Warnings")
        for warning in result.warnings:
            st.warning(warning)
        dependency_help = _build_dependency_help(result)
        if dependency_help is not None:
            st.info(dependency_help)

    if result.visualization_source != "solver_field" or _build_dependency_help(result) is not None:
        with st.expander("Runtime diagnostics"):
            diagnostics = _build_runtime_diagnostics()
            st.code(
                "\n".join(f"{key}: {value}" for key, value in diagnostics.items()),
                language="text",
            )

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

try:
    runtime_settings = RuntimeSettings.from_env()
except ConfigurationError as exc:
    st.error(str(exc))
    st.stop()

solver_modes = ["mock", "docker", "auto"]

with st.sidebar:
    st.header("Settings")
    solver_mode = st.selectbox(
        "Solver mode",
        solver_modes,
        index=solver_modes.index(runtime_settings.default_solver_mode),
    )
    mesh_density = st.slider(
        "Mesh density",
        min_value=12,
        max_value=80,
        value=runtime_settings.default_mesh_density,
        step=4,
    )
    selected_example = st.selectbox("Example prompt", list(EXAMPLE_PROMPTS.keys()), index=0)
    if st.button("Use example"):
        st.session_state["prompt_text"] = EXAMPLE_PROMPTS[selected_example]
    st.markdown("---")
    st.caption("OpenAI API key is optional but enables better parsing + summaries.")
    st.caption("Supported solver backends: mock, docker, or auto.")

prompt_default = st.session_state.get("prompt_text", EXAMPLE_PROMPTS["Cantilever beam"])
prompt = st.text_area("Simulation prompt", value=prompt_default, height=140)
run_clicked = st.button("Run simulation", type="primary")
status_placeholder = st.empty()

simulation_service = SimulationService(settings=runtime_settings)
result = st.session_state.get("last_result")

if run_clicked:
    if not prompt.strip():
        st.error("Please provide a simulation prompt.")
    else:
        try:
            result = simulation_service.run_simulation(
                prompt=prompt,
                mesh_density=mesh_density,
                solver_mode=solver_mode,
                progress_callback=status_placeholder.info,
            )
            st.session_state["last_result"] = result

            status_placeholder.success("Simulation completed ✅")
        except FEACopilotError as exc:
            status_placeholder.error(str(exc))
        except Exception as exc:  # pragma: no cover
            status_placeholder.error(f"Failed to complete simulation: {exc}")

if result is not None:
    _render_result(result, simulation_service)
