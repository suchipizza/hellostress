from __future__ import annotations

import io
import json
from pathlib import Path

from fea_engine import RuntimeSettings, SimulationRunError, SimulationService
from fea_engine.cli import main


PROMPT = "Simulate a 1 m long, 0.1 m thick steel cantilever beam with a 150 N downward tip load."


def build_settings(tmp_path: Path) -> RuntimeSettings:
    return RuntimeSettings(
        default_solver_mode="mock",
        default_mesh_density=28,
        docker_image="dolfinx/dolfinx:v0.7.3",
        solver_timeout_seconds=60,
        runs_workspace=tmp_path / "runs",
        openai_model="gpt-4o-mini",
    )


def test_cli_json_output_runs_real_mock_pipeline(tmp_path: Path) -> None:
    settings = build_settings(tmp_path)
    stdout = io.StringIO()
    stderr = io.StringIO()

    exit_code = main(
        ["--prompt", PROMPT, "--output", "json"],
        settings_loader=lambda: settings,
        stdout=stdout,
        stderr=stderr,
    )

    payload = json.loads(stdout.getvalue())
    assert exit_code == 0
    assert stderr.getvalue() == ""
    assert payload["status"] == "completed"
    assert payload["solver_mode"] == "mock"
    assert payload["backend_status"] == "succeeded"
    assert payload["metrics_source"] == "solver_artifact"
    assert payload["fallback_used"] is False
    assert payload["metrics"]["max_deflection"] > 0
    assert payload["metrics"]["max_stress"] > 0
    assert Path(payload["artifacts"]["result_schema_path"]).exists()
    assert Path(payload["artifacts"]["metrics_path"]).exists()
    assert payload["spec"]["geometry"] == "beam"


def test_cli_text_output_uses_runtime_defaults(tmp_path: Path) -> None:
    settings = build_settings(tmp_path)
    stdout = io.StringIO()

    exit_code = main(
        ["--prompt", PROMPT],
        settings_loader=lambda: settings,
        stdout=stdout,
        stderr=io.StringIO(),
    )

    output = stdout.getvalue()
    assert exit_code == 0
    assert "Status: completed" in output
    assert "Solver mode: mock" in output
    assert "Metrics source: solver_artifact" in output
    assert "Warnings: none" in output


def test_cli_returns_non_zero_for_recoverable_service_failures(tmp_path: Path) -> None:
    settings = build_settings(tmp_path)
    stdout = io.StringIO()
    stderr = io.StringIO()

    class FailingService:
        def run_simulation(self, prompt: str, mesh_density: int, solver_mode: str):
            raise SimulationRunError("backend exploded", backend_mode=solver_mode)

    exit_code = main(
        ["--prompt", PROMPT, "--solver-mode", "docker"],
        settings_loader=lambda: settings,
        service_factory=lambda runtime_settings: FailingService(),
        stdout=stdout,
        stderr=stderr,
    )

    assert exit_code == 1
    assert stdout.getvalue() == ""
    assert "backend exploded" in stderr.getvalue()
