from __future__ import annotations

import io
import json
from pathlib import Path

from fea_engine import (
    ARTIFACT_SCHEMA_VERSION,
    MAX_SUPPORTED_ARTIFACT_SCHEMA_VERSION,
    RuntimeSettings,
    SimulationRunError,
    SimulationService,
)
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
    result_schema_path = Path(payload["artifacts"]["result_schema_path"])
    assert result_schema_path.exists()
    assert Path(payload["artifacts"]["metrics_path"]).exists()
    assert payload["spec"]["geometry"] == "beam"
    run_result_payload = json.loads(result_schema_path.read_text(encoding="utf-8"))
    assert run_result_payload["schema_version"] == ARTIFACT_SCHEMA_VERSION


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


def test_cli_can_inspect_run_result_json(tmp_path: Path) -> None:
    settings = build_settings(tmp_path)
    initial_stdout = io.StringIO()

    exit_code = main(
        ["--prompt", PROMPT, "--output", "json"],
        settings_loader=lambda: settings,
        stdout=initial_stdout,
        stderr=io.StringIO(),
    )
    assert exit_code == 0
    run_payload = json.loads(initial_stdout.getvalue())
    run_result_path = run_payload["artifacts"]["result_schema_path"]

    inspect_stdout = io.StringIO()
    inspect_stderr = io.StringIO()
    inspect_exit_code = main(
        ["--inspect-run-result", run_result_path, "--output", "json"],
        stdout=inspect_stdout,
        stderr=inspect_stderr,
    )

    inspection_payload = json.loads(inspect_stdout.getvalue())
    assert inspect_exit_code == 0
    assert inspect_stderr.getvalue() == ""
    assert inspection_payload["valid"] is True
    assert inspection_payload["schema_version"] == ARTIFACT_SCHEMA_VERSION
    assert inspection_payload["compatibility"]["supported"] is True
    assert inspection_payload["status"] == "completed"
    assert inspection_payload["backend_status"] == "succeeded"
    assert inspection_payload["diagnostics"]["all_referenced_files_present"] is True


def test_cli_can_inspect_run_directory(tmp_path: Path) -> None:
    settings = build_settings(tmp_path)
    initial_stdout = io.StringIO()
    main(
        ["--prompt", PROMPT, "--output", "json"],
        settings_loader=lambda: settings,
        stdout=initial_stdout,
        stderr=io.StringIO(),
    )
    run_payload = json.loads(initial_stdout.getvalue())
    run_dir = run_payload["artifacts"]["run_dir"]

    inspect_stdout = io.StringIO()
    inspect_exit_code = main(
        ["--inspect-run-dir", run_dir],
        stdout=inspect_stdout,
        stderr=io.StringIO(),
    )

    assert inspect_exit_code == 0
    output = inspect_stdout.getvalue()
    assert "Inspection: valid" in output
    assert "Schema version: 1" in output
    assert "Compatibility supported: True" in output
    assert "Run status: completed" in output


def test_cli_inspection_returns_non_zero_for_unsupported_schema_version(tmp_path: Path) -> None:
    settings = build_settings(tmp_path)
    initial_stdout = io.StringIO()
    main(
        ["--prompt", PROMPT, "--output", "json"],
        settings_loader=lambda: settings,
        stdout=initial_stdout,
        stderr=io.StringIO(),
    )
    run_payload = json.loads(initial_stdout.getvalue())
    result_schema_path = Path(run_payload["artifacts"]["result_schema_path"])
    result_payload = json.loads(result_schema_path.read_text(encoding="utf-8"))
    result_payload["schema_version"] = MAX_SUPPORTED_ARTIFACT_SCHEMA_VERSION + 1
    result_schema_path.write_text(json.dumps(result_payload), encoding="utf-8")

    inspect_stdout = io.StringIO()
    inspect_stderr = io.StringIO()
    inspect_exit_code = main(
        ["--inspect-run-result", str(result_schema_path)],
        stdout=inspect_stdout,
        stderr=inspect_stderr,
    )

    assert inspect_exit_code == 1
    assert inspect_stdout.getvalue() == ""
    assert "unsupported" in inspect_stderr.getvalue()
