from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

from fea_engine import (
    ARTIFACT_SCHEMA_VERSION,
    EXPORT_MANIFEST_NAME,
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
    assert inspection_payload["triage"]["severity"] == "ok"


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
    assert "Triage severity: ok" in output
    assert "Issues: none" in output


def test_cli_inspection_reports_triage_for_degraded_bundle(tmp_path: Path) -> None:
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
    run_result_payload = json.loads(result_schema_path.read_text(encoding="utf-8"))

    backend_status_path = Path(run_payload["artifacts"]["backend_status_path"])
    backend_status_payload = json.loads(backend_status_path.read_text(encoding="utf-8"))
    backend_status_payload["status"] = "timed_out"
    backend_status_payload["exit_code"] = -1
    backend_status_payload["timed_out"] = True
    backend_status_payload["metrics_present"] = False
    backend_status_payload["container_id"] = "container-123"
    backend_status_payload["container_status"] = "exited"
    backend_status_payload["cleanup_status"] = "remove_failed"
    backend_status_path.write_text(json.dumps(backend_status_payload), encoding="utf-8")

    run_result_payload["status"] = "completed_with_fallback"
    run_result_payload["backend_mode"] = "docker"
    run_result_payload["backend_status"] = "timed_out"
    run_result_payload["fallback_used"] = True
    run_result_payload["warnings"] = ["Metrics fallback engaged after backend timeout."]
    run_result_payload["backend_status_details"] = backend_status_payload
    result_schema_path.write_text(json.dumps(run_result_payload), encoding="utf-8")

    Path(run_payload["artifacts"]["metrics_path"]).unlink()

    inspect_stdout = io.StringIO()
    inspect_exit_code = main(
        ["--inspect-run-result", str(result_schema_path)],
        stdout=inspect_stdout,
        stderr=io.StringIO(),
    )

    assert inspect_exit_code == 0
    output = inspect_stdout.getvalue()
    assert "Triage severity: error" in output
    assert "[error] backend_timed_out" in output
    assert "[warning] fallback_used" in output
    assert "Suggested actions:" in output


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


def test_cli_can_export_run_bundle(tmp_path: Path) -> None:
    settings = build_settings(tmp_path)
    initial_stdout = io.StringIO()
    main(
        ["--prompt", PROMPT, "--output", "json"],
        settings_loader=lambda: settings,
        stdout=initial_stdout,
        stderr=io.StringIO(),
    )
    run_payload = json.loads(initial_stdout.getvalue())
    run_result_path = run_payload["artifacts"]["result_schema_path"]
    archive_path = tmp_path / "export.zip"

    export_stdout = io.StringIO()
    export_stderr = io.StringIO()
    export_exit_code = main(
        ["--export-run-result", run_result_path, "--export-output", str(archive_path), "--output", "json"],
        stdout=export_stdout,
        stderr=export_stderr,
    )

    export_payload = json.loads(export_stdout.getvalue())
    assert export_exit_code == 0
    assert export_stderr.getvalue() == ""
    assert archive_path.exists()
    assert export_payload["archive_sha256"]
    assert export_payload["manifest_name"] == EXPORT_MANIFEST_NAME
    assert export_payload["manifest"]["file_count"] >= 7
    with zipfile.ZipFile(archive_path) as archive:
        names = set(archive.namelist())
    assert "run_result.json" in names
    assert EXPORT_MANIFEST_NAME in names


def test_cli_can_cleanup_workspace_with_dry_run(tmp_path: Path) -> None:
    settings = build_settings(tmp_path)
    first_stdout = io.StringIO()
    second_stdout = io.StringIO()
    main(
        ["--prompt", PROMPT, "--output", "json"],
        settings_loader=lambda: settings,
        stdout=first_stdout,
        stderr=io.StringIO(),
    )
    main(
        ["--prompt", PROMPT, "--output", "json"],
        settings_loader=lambda: settings,
        stdout=second_stdout,
        stderr=io.StringIO(),
    )
    first_payload = json.loads(first_stdout.getvalue())
    old_run_dir = Path(first_payload["artifacts"]["run_dir"])
    import os
    from datetime import datetime, timedelta, timezone

    old_time = (datetime.now(timezone.utc) - timedelta(days=10)).timestamp()
    os.utime(old_run_dir / "run_result.json", (old_time, old_time))
    os.utime(old_run_dir, (old_time, old_time))

    cleanup_stdout = io.StringIO()
    cleanup_stderr = io.StringIO()
    cleanup_exit_code = main(
        [
            "--cleanup-runs",
            "--workspace",
            str(settings.runs_workspace),
            "--retention-days",
            "7",
            "--keep-latest",
            "1",
            "--dry-run",
            "--output",
            "json",
        ],
        stdout=cleanup_stdout,
        stderr=cleanup_stderr,
    )

    payload = json.loads(cleanup_stdout.getvalue())
    assert cleanup_exit_code == 0
    assert cleanup_stderr.getvalue() == ""
    assert payload["summary"]["deleted_count"] == 1
    assert payload["summary"]["retained_count"] == 1
    assert payload["deleted_run_names"] == [old_run_dir.name]
    assert old_run_dir.exists() is True
