from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import plotly.graph_objects as go
import pytest

from fea_engine import (
    ARTIFACT_SCHEMA_VERSION,
    BeamSection,
    FenicsScriptGenerator,
    LoadCase,
    SimulationService,
    SimulationSpec,
)
from fea_engine.models import DEFAULT_MATERIALS, GeometryType, LoadType
from fea_engine.solver import FenicsSolver


pytestmark = pytest.mark.integration


class StaticParser:
    def __init__(self, spec: SimulationSpec) -> None:
        self.spec = spec

    def parse(self, prompt: str) -> SimulationSpec:
        return self.spec


class StaticGenerator:
    def __init__(self, script: str) -> None:
        self.script = script

    def render(self, spec: SimulationSpec) -> str:
        return self.script


class StaticVisualizer:
    def build_figure(self, spec: SimulationSpec, metrics: dict[str, float]) -> go.Figure:
        return go.Figure()


class StaticSummarizer:
    def summarize(self, spec: SimulationSpec, metrics: dict[str, float]) -> str:
        return "docker smoke summary"


def build_beam_spec() -> SimulationSpec:
    return SimulationSpec(
        prompt="docker smoke beam",
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


def docker_runtime_available() -> bool:
    if not shutil.which("docker"):
        return False
    try:
        subprocess.run(
            ["docker", "version"],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except Exception:
        return False
    return True


def smoke_script() -> str:
    return """
from pathlib import Path
import json
import sys

results_dir = Path("/workspace/results")
results_dir.mkdir(parents=True, exist_ok=True)
(results_dir / "metrics.json").write_text(
    json.dumps({"max_deflection": 0.00125, "max_stress": 2400000.0}),
    encoding="utf-8",
)
print("docker smoke stdout")
print("docker smoke stderr", file=sys.stderr)
""".strip()


def test_service_docker_smoke_writes_backend_and_result_artifacts(tmp_path: Path) -> None:
    if not docker_runtime_available():
        pytest.skip("Docker runtime is not available for the integration smoke test.")

    service = SimulationService(
        parser=StaticParser(build_beam_spec()),
        generator=StaticGenerator(smoke_script()),
        visualizer=StaticVisualizer(),
        summarizer=StaticSummarizer(),
        solver_factory=lambda mode: FenicsSolver(mode=mode, workspace=tmp_path),
    )

    result = service.run_simulation(
        prompt="ignored",
        mesh_density=24,
        solver_mode="docker",
    )

    assert result.status == "completed"
    assert result.solver_mode == "docker"
    assert result.metrics_source == "solver_artifact"
    assert result.fallback_used is False
    assert result.warnings == []
    assert result.metrics == {"max_deflection": 0.00125, "max_stress": 2400000.0}
    assert result.artifacts.backend_mode == "docker"
    assert result.artifacts.backend_status == "succeeded"
    assert result.artifacts.metrics_path.exists()
    assert result.artifacts.backend_status_path.exists()
    assert result.artifacts.backend_metadata_path.exists()
    assert result.result_schema_path.exists()
    assert result.artifacts.generated_files == [result.artifacts.metrics_path]
    assert result.artifacts.run_metadata.command[0] == "docker"
    assert result.artifacts.run_metadata.exit_code == 0
    assert "docker smoke stdout" in result.artifacts.run_metadata.stdout_excerpt
    assert "docker smoke stderr" in result.artifacts.run_metadata.stderr_excerpt

    status_payload = json.loads(result.artifacts.backend_status_path.read_text(encoding="utf-8"))
    assert status_payload == {
        "schema_version": ARTIFACT_SCHEMA_VERSION,
        "backend_mode": "docker",
        "status": "succeeded",
        "exit_code": 0,
        "timed_out": False,
        "metrics_path": str(result.artifacts.metrics_path),
        "metrics_present": True,
        "container_id": result.artifacts.runtime_metadata.container_id,
        "container_status": result.artifacts.runtime_metadata.container_status,
        "cleanup_status": result.artifacts.runtime_metadata.cleanup_status,
    }

    metadata_payload = json.loads(result.artifacts.backend_metadata_path.read_text(encoding="utf-8"))
    assert metadata_payload["schema_version"] == ARTIFACT_SCHEMA_VERSION
    assert metadata_payload["backend_mode"] == "docker"
    assert metadata_payload["run_dir"] == str(result.artifacts.run_dir)
    assert metadata_payload["docker_image"] == "dolfinx/dolfinx:v0.7.3"
    assert metadata_payload["docker_version"]
    assert metadata_payload["timeout_seconds"] == 60
    assert metadata_payload["runtime"]["container_id"] == result.artifacts.runtime_metadata.container_id
    assert metadata_payload["runtime"]["cleanup_status"] == "removed"
    assert metadata_payload["run_metadata"]["command"][0] == "docker"
    assert metadata_payload["run_metadata"]["exit_code"] == 0
    assert metadata_payload["run_metadata"]["stdout_path"] == str(result.artifacts.run_metadata.stdout_path)
    assert metadata_payload["run_metadata"]["stderr_path"] == str(result.artifacts.run_metadata.stderr_path)

    schema_payload = json.loads(result.result_schema_path.read_text(encoding="utf-8"))
    assert schema_payload["schema_version"] == ARTIFACT_SCHEMA_VERSION
    assert schema_payload["status"] == "completed"
    assert schema_payload["backend_mode"] == "docker"
    assert schema_payload["backend_status"] == "succeeded"
    assert schema_payload["metrics_source"] == "solver_artifact"
    assert schema_payload["fallback_used"] is False
    assert schema_payload["warnings"] == []
    assert schema_payload["backend_status_details"]["cleanup_status"] == "removed"
    assert schema_payload["backend_metadata"]["runtime"]["container_id"] == result.artifacts.runtime_metadata.container_id
    assert schema_payload["artifacts"] == {
        "run_dir": str(result.artifacts.run_dir),
        "script_path": str(result.artifacts.script_path),
        "results_dir": str(result.artifacts.results_dir),
        "metrics_path": str(result.artifacts.metrics_path),
        "backend_status_path": str(result.artifacts.backend_status_path),
        "backend_metadata_path": str(result.artifacts.backend_metadata_path),
        "generated_files": [str(result.artifacts.metrics_path)],
    }
    assert schema_payload["run_metadata"]["command"][0] == "docker"
    assert schema_payload["run_metadata"]["exit_code"] == 0
    assert schema_payload["run_metadata"]["timed_out"] is False
    assert schema_payload["run_metadata"]["stdout_path"] == str(result.artifacts.run_metadata.stdout_path)
    assert schema_payload["run_metadata"]["stderr_path"] == str(result.artifacts.run_metadata.stderr_path)
    assert schema_payload["runtime_metadata"]["cleanup_status"] == "removed"


def test_generated_dolfinx_beam_script_runs_in_docker(tmp_path: Path) -> None:
    if not docker_runtime_available():
        pytest.skip("Docker runtime is not available for the integration smoke test.")

    spec = build_beam_spec()
    spec.mesh_density = 8
    solver = FenicsSolver(mode="docker", workspace=tmp_path)
    script = FenicsScriptGenerator().render(spec)

    artifacts = solver.run(spec, script)

    metrics_payload = json.loads(artifacts.metrics_path.read_text(encoding="utf-8"))
    assert artifacts.backend_mode == "docker"
    assert artifacts.backend_status == "succeeded"
    assert artifacts.run_metadata.exit_code == 0
    assert artifacts.metrics_path.exists()
    assert (artifacts.results_dir / "displacement.xdmf").exists()
    assert (artifacts.results_dir / "stress.xdmf").exists()
    assert metrics_payload["max_deflection"] >= 0.0
    assert metrics_payload["max_stress"] >= 0.0


def test_beam_tip_load_scaling_changes_metrics_in_docker(tmp_path: Path) -> None:
    if not docker_runtime_available():
        pytest.skip("Docker runtime is not available for the integration smoke test.")

    light_spec = build_beam_spec()
    light_spec.mesh_density = 8
    heavy_spec = build_beam_spec()
    heavy_spec.mesh_density = 8
    heavy_spec.loads[0].magnitude = 300.0

    solver = FenicsSolver(mode="docker", workspace=tmp_path)
    generator = FenicsScriptGenerator()

    light_artifacts = solver.run(light_spec, generator.render(light_spec))
    heavy_artifacts = solver.run(heavy_spec, generator.render(heavy_spec))

    light_metrics = json.loads(light_artifacts.metrics_path.read_text(encoding="utf-8"))
    heavy_metrics = json.loads(heavy_artifacts.metrics_path.read_text(encoding="utf-8"))

    assert light_metrics["max_deflection"] > 0.0
    assert heavy_metrics["max_deflection"] > light_metrics["max_deflection"]
    assert heavy_metrics["max_stress"] > light_metrics["max_stress"]
    assert heavy_metrics["max_deflection"] / light_metrics["max_deflection"] == pytest.approx(2.0, rel=0.25)
    assert heavy_metrics["max_stress"] / light_metrics["max_stress"] == pytest.approx(2.0, rel=0.25)
