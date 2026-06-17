from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import plotly.graph_objects as go
import pytest

from fea_engine import (
    ARTIFACT_SCHEMA_VERSION,
    BeamSection,
    LoadCase,
    RuntimeSettings,
    SimulationRunError,
    SimulationService,
    SimulationSpec,
    SolverExecutionError,
)
from fea_engine.models import DEFAULT_MATERIALS, GeometryType, LoadType
from fea_engine.postprocessor import MetricsCollectionResult
from fea_engine.solver import BackendRuntimeMetadata, SolverArtifacts, SolverRunMetadata


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

    def collect_metrics(self, spec: SimulationSpec, artifacts: SolverArtifacts) -> MetricsCollectionResult:
        self.calls.append((spec, artifacts))
        return MetricsCollectionResult(metrics=self.metrics, source="solver_artifact")


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
        run_dir=tmp_path,
        backend_mode="mock",
        backend_status="succeeded",
        script_path=tmp_path / "simulation.py",
        results_dir=tmp_path / "results",
        metrics_path=tmp_path / "results" / "metrics.json",
        backend_status_path=tmp_path / "backend_status.json",
        backend_metadata_path=tmp_path / "backend_metadata.json",
        run_metadata=SolverRunMetadata(
            command=["mock"],
            exit_code=0,
            stdout_path=tmp_path / "solver.stdout.log",
            stderr_path=tmp_path / "solver.stderr.log",
            stdout_excerpt="",
            stderr_excerpt="",
        ),
        runtime_metadata=BackendRuntimeMetadata(),
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
    assert result.status == "completed"
    assert result.metrics_source == "solver_artifact"
    assert result.fallback_used is False
    assert result.warnings == []
    assert result.result_schema_path.exists()
    assert result.metrics == {"max_deflection": 1.2e-3, "max_stress": 2.4e6}
    assert result.figure is figure
    assert result.pyvista_image is None
    assert result.visualization_source == "estimated_profile"
    assert result.summary == "summary"
    assert result.solver_mode == "mock"
    schema_payload = json.loads(result.result_schema_path.read_text(encoding="utf-8"))
    assert schema_payload["schema_version"] == ARTIFACT_SCHEMA_VERSION
    assert schema_payload["status"] == "completed"
    assert schema_payload["metrics_source"] == "solver_artifact"
    assert schema_payload["backend_status_details"] == {}
    assert schema_payload["backend_metadata"] == {}
    assert schema_payload["runtime_metadata"]["cleanup_status"] == "not_applicable"


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
    assert result.artifacts.run_dir.exists()
    assert result.artifacts.backend_mode == "mock"
    assert result.artifacts.backend_status == "succeeded"
    assert result.artifacts.run_metadata.command == ["mock"]
    assert result.artifacts.run_metadata.exit_code == 0
    assert result.artifacts.run_metadata.stdout_path.exists()
    assert result.artifacts.run_metadata.stderr_path.exists()
    assert result.artifacts.metrics_path.name == "metrics.json"
    assert result.artifacts.metrics_path.exists()
    assert result.artifacts.generated_files == [result.artifacts.metrics_path]
    assert result.artifacts.warnings == []
    assert result.status == "completed"
    assert result.metrics_source == "solver_artifact"
    assert result.fallback_used is False
    assert result.warnings == []
    assert result.result_schema_path.exists()
    assert result.metrics["max_deflection"] > 0
    assert result.metrics["max_stress"] > 0
    assert result.summary
    assert result.solver_mode == "mock"
    assert result.visualization_source == "estimated_profile"
    assert result.pyvista_image is None
    assert result.result_schema_path.exists()
    schema_payload = json.loads(result.result_schema_path.read_text(encoding="utf-8"))
    assert schema_payload["schema_version"] == ARTIFACT_SCHEMA_VERSION
    assert schema_payload["runtime_metadata"]["cleanup_status"] == "not_applicable"


def test_service_uses_runtime_settings_for_default_dependencies(tmp_path: Path) -> None:
    settings = RuntimeSettings(
        default_solver_mode="mock",
        default_mesh_density=36,
        docker_image="custom/dolfinx:latest",
        solver_timeout_seconds=45,
        runs_workspace=tmp_path / "runs",
        openai_model="gpt-4.1-mini",
    )

    service = SimulationService(settings=settings)

    result = service.run_simulation(
        prompt="Simulate a 1 m long, 0.1 m thick steel cantilever beam with a 150 N downward tip load.",
        mesh_density=settings.default_mesh_density,
        solver_mode=settings.default_solver_mode,
    )

    assert service.parser.llm_client.model == "gpt-4.1-mini"
    assert service.summarizer.llm_client.model == "gpt-4.1-mini"
    assert result.spec.mesh_density == 36
    assert result.artifacts.run_dir.parent == settings.runs_workspace
    assert result.artifacts.run_metadata.command == ["mock"]
    assert result.visualization_source == "estimated_profile"


def test_service_normalizes_solver_failures() -> None:
    class FailingSolver:
        mode = "docker"

        def run(self, spec: SimulationSpec, script: str) -> SolverArtifacts:
            raise SolverExecutionError(
                "Docker solver execution failed.",
                backend_mode="docker",
                exit_code=125,
                command=["docker", "run"],
                stderr_excerpt="container boot failed",
            )

    service = SimulationService(solver_factory=lambda mode: FailingSolver())

    with pytest.raises(SimulationRunError) as exc_info:
        service.run_simulation(
            prompt="Simulate a 1 m long, 0.1 m thick steel cantilever beam with a 150 N downward tip load.",
            mesh_density=32,
            solver_mode="docker",
        )

    assert "Solver backend 'docker' failed with exit code 125." in str(exc_info.value)
    assert "stderr: container boot failed" in str(exc_info.value)


def test_service_marks_fallback_runs(tmp_path: Path) -> None:
    spec = build_beam_spec()
    parser = StubParser(spec)
    generator = StubGenerator()
    run_dir = tmp_path / "run"
    results_dir = run_dir / "results"
    results_dir.mkdir(parents=True)
    stdout_path = run_dir / "solver.stdout.log"
    stderr_path = run_dir / "solver.stderr.log"
    stdout_path.write_text("stdout", encoding="utf-8")
    stderr_path.write_text("", encoding="utf-8")
    backend_status_path = run_dir / "backend_status.json"
    backend_status_path.write_text(
        json.dumps({"backend_mode": "docker", "status": "succeeded", "metrics_present": False}),
        encoding="utf-8",
    )
    backend_metadata_path = run_dir / "backend_metadata.json"
    backend_metadata_path.write_text(json.dumps({"backend_mode": "docker"}), encoding="utf-8")
    artifacts = SolverArtifacts(
        run_dir=run_dir,
        backend_mode="docker",
        backend_status="succeeded",
        script_path=run_dir / "simulation.py",
        results_dir=results_dir,
        metrics_path=results_dir / "metrics.json",
        backend_status_path=backend_status_path,
        backend_metadata_path=backend_metadata_path,
        run_metadata=SolverRunMetadata(
            command=["docker", "run"],
            exit_code=0,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
        ),
        runtime_metadata=BackendRuntimeMetadata(
            container_id="abc123",
            container_status="exited",
            cleanup_status="removed",
        ),
        warnings=["Solver backend did not produce metrics.json; post-processing may fall back to estimates."],
    )
    seen_specs: list[SimulationSpec] = []
    seen_scripts: list[str] = []
    solver = StubSolver("docker", artifacts, seen_specs, seen_scripts)
    visualizer = StubVisualizer(go.Figure())
    summarizer = StubSummarizer("summary")

    service = SimulationService(
        parser=parser,
        generator=generator,
        visualizer=visualizer,
        summarizer=summarizer,
        solver_factory=lambda mode: solver,
    )

    result = service.run_simulation(
        prompt="beam prompt",
        mesh_density=48,
        solver_mode="docker",
    )

    assert result.status == "completed_with_fallback"
    assert result.metrics_source == "analytical_fallback"
    assert result.fallback_used is True
    assert any("analytical fallback estimate used" in warning for warning in result.warnings)
    schema_payload = json.loads(result.result_schema_path.read_text(encoding="utf-8"))
    assert schema_payload["schema_version"] == ARTIFACT_SCHEMA_VERSION
    assert schema_payload["status"] == "completed_with_fallback"
    assert schema_payload["fallback_used"] is True
    assert schema_payload["metrics_source"] == "analytical_fallback"
    assert schema_payload["runtime_metadata"]["container_id"] == "abc123"
