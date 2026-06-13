from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import plotly.graph_objects as go

from fea_engine import BeamSection, LoadCase, SimulationService, SimulationSpec
from fea_engine.models import DEFAULT_MATERIALS, GeometryType, LoadType
from fea_engine.solver import SolverArtifacts


class StubParser:
    def __init__(self, spec: SimulationSpec) -> None:
        self.spec = spec
        self.prompts: list[str] = []

    def parse(self, prompt: str) -> SimulationSpec:
        self.prompts.append(prompt)
        return self.spec


class StubGenerator:
    def __init__(self) -> None:
        self.specs: list[SimulationSpec] = []

    def render(self, spec: SimulationSpec) -> str:
        self.specs.append(spec)
        return "generated-script"


@dataclass
class StubSolver:
    mode: str
    artifacts: SolverArtifacts
    seen_specs: list[SimulationSpec]
    seen_scripts: list[str]

    def run(self, spec: SimulationSpec, script: str) -> SolverArtifacts:
        self.seen_specs.append(spec)
        self.seen_scripts.append(script)
        return self.artifacts


class StubPostProcessor:
    def __init__(self, metrics: dict[str, float]) -> None:
        self.metrics = metrics
        self.calls: list[tuple[SimulationSpec, SolverArtifacts]] = []

    def collect_metrics(self, spec: SimulationSpec, artifacts: SolverArtifacts) -> dict[str, float]:
        self.calls.append((spec, artifacts))
        return self.metrics


class StubVisualizer:
    def __init__(self, figure: go.Figure) -> None:
        self.figure = figure
        self.calls: list[tuple[SimulationSpec, dict[str, float]]] = []

    def build_figure(self, spec: SimulationSpec, metrics: dict[str, float]) -> go.Figure:
        self.calls.append((spec, metrics))
        return self.figure


class StubSummarizer:
    def __init__(self, summary: str) -> None:
        self.summary = summary
        self.calls: list[tuple[SimulationSpec, dict[str, float]]] = []

    def summarize(self, spec: SimulationSpec, metrics: dict[str, float]) -> str:
        self.calls.append((spec, metrics))
        return self.summary


def build_beam_spec() -> SimulationSpec:
    return SimulationSpec(
        prompt="beam fixture",
        geometry=GeometryType.BEAM,
        length=1.0,
        beam_section=BeamSection(height=0.1, width=0.1),
        boundary_condition="fixed",
        loads=[
            LoadCase(
                load_type=LoadType.POINT,
                magnitude=150.0,
                direction="-y",
                location=1.0,
                units="N",
            )
        ],
        material=DEFAULT_MATERIALS["steel"],
    )


def test_service_coordinates_pipeline_and_progress_messages(tmp_path: Path) -> None:
    spec = build_beam_spec()
    parser = StubParser(spec)
    generator = StubGenerator()
    artifacts = SolverArtifacts(
        backend_mode="mock",
        script_path=tmp_path / "simulation.py",
        results_dir=tmp_path / "results",
        metrics_path=tmp_path / "results" / "metrics.json",
    )
    seen_specs: list[SimulationSpec] = []
    seen_scripts: list[str] = []
    solver = StubSolver("mock", artifacts, seen_specs, seen_scripts)
    postprocessor = StubPostProcessor({"max_deflection": 1.2e-3, "max_stress": 2.4e6})
    figure = go.Figure()
    visualizer = StubVisualizer(figure)
    summarizer = StubSummarizer("summary")
    progress_messages: list[str] = []

    service = SimulationService(
        parser=parser,
        generator=generator,
        postprocessor=postprocessor,
        visualizer=visualizer,
        summarizer=summarizer,
        solver_factory=lambda mode: solver,
    )

    result = service.run_simulation(
        prompt="beam prompt",
        mesh_density=48,
        solver_mode="mock",
        progress_callback=progress_messages.append,
    )

    assert parser.prompts == ["beam prompt"]
    assert spec.mesh_density == 48
    assert generator.specs == [spec]
    assert seen_specs == [spec]
    assert seen_scripts == ["generated-script"]
    assert postprocessor.calls == [(spec, artifacts)]
    assert visualizer.calls == [(spec, {"max_deflection": 1.2e-3, "max_stress": 2.4e6})]
    assert summarizer.calls == [(spec, {"max_deflection": 1.2e-3, "max_stress": 2.4e6})]
    assert progress_messages == [
        "Parsing prompt with heuristic + LLM assist…",
        "Generating FEniCS script…",
        "Running solver in mock mode…",
        "Post-processing results…",
    ]
    assert result.spec is spec
    assert result.script == "generated-script"
    assert result.artifacts == artifacts
    assert result.metrics == {"max_deflection": 1.2e-3, "max_stress": 2.4e6}
    assert result.figure is figure
    assert result.summary == "summary"
    assert result.solver_mode == "mock"


def test_service_runs_real_mock_pipeline() -> None:
    service = SimulationService()

    result = service.run_simulation(
        prompt="Simulate a 1 m long, 0.1 m thick steel cantilever beam with a 150 N downward tip load.",
        mesh_density=32,
        solver_mode="mock",
    )

    assert result.spec.length == 1.0
    assert result.spec.mesh_density == 32
    assert result.script.strip()
    assert result.artifacts.backend_mode == "mock"
    assert result.artifacts.metrics_path.name == "metrics.json"
    assert result.artifacts.metrics_path.exists()
    assert result.artifacts.generated_files == [result.artifacts.metrics_path]
    assert result.artifacts.warnings == []
    assert result.metrics["max_deflection"] > 0
    assert result.metrics["max_stress"] > 0
    assert result.summary
    assert result.solver_mode == "mock"
