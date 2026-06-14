from __future__ import annotations

import io
import json
import zipfile
from datetime import datetime, timedelta, timezone
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
    assert inspection_payload["policy"]["quality_gate"]["passed"] is True
    assert inspection_payload["policy"]["export"]["allowed"] is True


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
    assert "quality_gate_passed: True" in output
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
    assert "export_allowed: False" in output
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
    assert export_payload["policy"]["quality_gate"]["passed"] is True
    assert export_payload["policy_override_used"] is False
    assert export_payload["manifest_name"] == EXPORT_MANIFEST_NAME
    assert export_payload["manifest"]["file_count"] >= 7
    with zipfile.ZipFile(archive_path) as archive:
        names = set(archive.namelist())
    assert "run_result.json" in names
    assert EXPORT_MANIFEST_NAME in names


def test_cli_blocks_export_for_policy_failed_bundle_without_override(tmp_path: Path) -> None:
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

    backend_status_path = Path(run_payload["artifacts"]["backend_status_path"])
    backend_status_payload = json.loads(backend_status_path.read_text(encoding="utf-8"))
    backend_status_payload["backend_mode"] = "docker"
    backend_status_payload["status"] = "failed"
    backend_status_payload["exit_code"] = 2
    backend_status_payload["container_id"] = "container-123"
    backend_status_payload["container_status"] = "exited"
    backend_status_payload["cleanup_status"] = "removed"
    backend_status_path.write_text(json.dumps(backend_status_payload), encoding="utf-8")

    backend_metadata_path = Path(run_payload["artifacts"]["backend_metadata_path"])
    backend_metadata_payload = json.loads(backend_metadata_path.read_text(encoding="utf-8"))
    backend_metadata_payload["backend_mode"] = "docker"
    backend_metadata_path.write_text(json.dumps(backend_metadata_payload), encoding="utf-8")

    run_result_payload = json.loads(result_schema_path.read_text(encoding="utf-8"))
    run_result_payload["backend_mode"] = "docker"
    run_result_payload["backend_status"] = "failed"
    run_result_payload["backend_status_details"] = backend_status_payload
    run_result_payload["backend_metadata"] = backend_metadata_payload
    result_schema_path.write_text(json.dumps(run_result_payload), encoding="utf-8")

    export_stdout = io.StringIO()
    export_stderr = io.StringIO()
    export_exit_code = main(
        ["--export-run-result", str(result_schema_path)],
        stdout=export_stdout,
        stderr=export_stderr,
    )

    assert export_exit_code == 1
    assert export_stdout.getvalue() == ""
    assert "Export policy blocked" in export_stderr.getvalue()


def test_cli_can_override_export_policy_for_degraded_bundle(tmp_path: Path) -> None:
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
    archive_path = tmp_path / "override-export.zip"

    backend_status_path = Path(run_payload["artifacts"]["backend_status_path"])
    backend_status_payload = json.loads(backend_status_path.read_text(encoding="utf-8"))
    backend_status_payload["backend_mode"] = "docker"
    backend_status_payload["status"] = "failed"
    backend_status_payload["exit_code"] = 2
    backend_status_payload["container_id"] = "container-123"
    backend_status_payload["container_status"] = "exited"
    backend_status_payload["cleanup_status"] = "removed"
    backend_status_path.write_text(json.dumps(backend_status_payload), encoding="utf-8")

    backend_metadata_path = Path(run_payload["artifacts"]["backend_metadata_path"])
    backend_metadata_payload = json.loads(backend_metadata_path.read_text(encoding="utf-8"))
    backend_metadata_payload["backend_mode"] = "docker"
    backend_metadata_path.write_text(json.dumps(backend_metadata_payload), encoding="utf-8")

    run_result_payload = json.loads(result_schema_path.read_text(encoding="utf-8"))
    run_result_payload["backend_mode"] = "docker"
    run_result_payload["backend_status"] = "failed"
    run_result_payload["backend_status_details"] = backend_status_payload
    run_result_payload["backend_metadata"] = backend_metadata_payload
    result_schema_path.write_text(json.dumps(run_result_payload), encoding="utf-8")

    export_stdout = io.StringIO()
    export_stderr = io.StringIO()
    export_exit_code = main(
        [
            "--export-run-result",
            str(result_schema_path),
            "--export-output",
            str(archive_path),
            "--allow-degraded-export",
            "--output",
            "json",
        ],
        stdout=export_stdout,
        stderr=export_stderr,
    )

    export_payload = json.loads(export_stdout.getvalue())
    assert export_exit_code == 0
    assert export_stderr.getvalue() == ""
    assert archive_path.exists()
    assert export_payload["policy"]["quality_gate"]["passed"] is False
    assert export_payload["policy"]["export"]["allowed"] is False
    assert export_payload["policy_override_used"] is True


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


def test_cli_can_report_workspace_policy_in_json(tmp_path: Path) -> None:
    settings = build_settings(tmp_path)
    run_payloads: list[dict[str, object]] = []
    for _ in range(4):
        stdout = io.StringIO()
        exit_code = main(
            ["--prompt", PROMPT, "--output", "json"],
            settings_loader=lambda: settings,
            stdout=stdout,
            stderr=io.StringIO(),
        )
        assert exit_code == 0
        run_payloads.append(json.loads(stdout.getvalue()))

    clean_payload, warning_payload, blocked_payload, invalid_payload = run_payloads

    warning_result_path = Path(warning_payload["artifacts"]["result_schema_path"])
    warning_result = json.loads(warning_result_path.read_text(encoding="utf-8"))
    warning_result["status"] = "completed_with_fallback"
    warning_result["metrics_source"] = "fallback_estimate"
    warning_result["fallback_used"] = True
    warning_result["warnings"] = ["Fallback-derived metrics should be reviewed before promotion."]
    warning_result_path.write_text(json.dumps(warning_result), encoding="utf-8")

    blocked_result_path = Path(blocked_payload["artifacts"]["result_schema_path"])
    blocked_backend_status_path = Path(blocked_payload["artifacts"]["backend_status_path"])
    blocked_backend_status = json.loads(blocked_backend_status_path.read_text(encoding="utf-8"))
    blocked_backend_status["backend_mode"] = "docker"
    blocked_backend_status["status"] = "failed"
    blocked_backend_status["exit_code"] = 2
    blocked_backend_status["container_id"] = "container-123"
    blocked_backend_status["container_status"] = "exited"
    blocked_backend_status["cleanup_status"] = "removed"
    blocked_backend_status_path.write_text(json.dumps(blocked_backend_status), encoding="utf-8")

    blocked_backend_metadata_path = Path(blocked_payload["artifacts"]["backend_metadata_path"])
    blocked_backend_metadata = json.loads(blocked_backend_metadata_path.read_text(encoding="utf-8"))
    blocked_backend_metadata["backend_mode"] = "docker"
    blocked_backend_metadata_path.write_text(json.dumps(blocked_backend_metadata), encoding="utf-8")

    blocked_result = json.loads(blocked_result_path.read_text(encoding="utf-8"))
    blocked_result["backend_mode"] = "docker"
    blocked_result["backend_status"] = "failed"
    blocked_result["backend_status_details"] = blocked_backend_status
    blocked_result["backend_metadata"] = blocked_backend_metadata
    blocked_result_path.write_text(json.dumps(blocked_result), encoding="utf-8")

    invalid_result_path = Path(invalid_payload["artifacts"]["result_schema_path"])
    invalid_result = json.loads(invalid_result_path.read_text(encoding="utf-8"))
    invalid_result.pop("schema_version")
    invalid_result_path.write_text(json.dumps(invalid_result), encoding="utf-8")

    skipped_dir = settings.runs_workspace / "skipped-dir"
    skipped_dir.mkdir(parents=True)

    import os

    old_time = (datetime.now(timezone.utc) - timedelta(days=10)).timestamp()
    blocked_run_dir = Path(blocked_payload["artifacts"]["run_dir"])
    os.utime(blocked_result_path, (old_time, old_time))
    os.utime(blocked_run_dir, (old_time, old_time))

    report_stdout = io.StringIO()
    report_stderr = io.StringIO()
    report_exit_code = main(
        [
            "--report-workspace-policy",
            "--workspace",
            str(settings.runs_workspace),
            "--retention-days",
            "7",
            "--keep-latest",
            "1",
            "--output",
            "json",
        ],
        stdout=report_stdout,
        stderr=report_stderr,
    )

    payload = json.loads(report_stdout.getvalue())
    assert report_exit_code == 0
    assert report_stderr.getvalue() == ""
    assert payload["summary"]["discovered_count"] == 5
    assert payload["summary"]["valid_run_count"] == 3
    assert payload["summary"]["invalid_run_count"] == 1
    assert payload["summary"]["skipped_path_count"] == 1
    assert payload["summary"]["export_ready_count"] == 2
    assert payload["summary"]["promotion_ready_count"] == 1
    assert payload["summary"]["manual_review_count"] == 2
    assert payload["summary"]["retention_candidate_count"] == 1
    assert payload["invalid_run_names"] == [Path(invalid_payload["artifacts"]["run_dir"]).name]
    assert payload["skipped_path_names"] == ["skipped-dir"]

    runs_by_name = {record["run_name"]: record for record in payload["runs"]}
    assert runs_by_name[Path(clean_payload["artifacts"]["run_dir"]).name]["promotion_ready"] is True
    assert runs_by_name[Path(warning_payload["artifacts"]["run_dir"]).name]["manual_review_required"] is True
    assert runs_by_name[Path(blocked_payload["artifacts"]["run_dir"]).name]["export_ready"] is False
    assert runs_by_name[Path(blocked_payload["artifacts"]["run_dir"]).name]["retention_candidate"] is True


def test_cli_workspace_policy_text_output_lists_flagged_runs(tmp_path: Path) -> None:
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
    warning_payload = json.loads(first_stdout.getvalue())
    invalid_payload = json.loads(second_stdout.getvalue())

    warning_result_path = Path(warning_payload["artifacts"]["result_schema_path"])
    warning_result = json.loads(warning_result_path.read_text(encoding="utf-8"))
    warning_result["fallback_used"] = True
    warning_result["warnings"] = ["Fallback-derived metrics should be reviewed before promotion."]
    warning_result_path.write_text(json.dumps(warning_result), encoding="utf-8")

    invalid_result_path = Path(invalid_payload["artifacts"]["result_schema_path"])
    invalid_result = json.loads(invalid_result_path.read_text(encoding="utf-8"))
    invalid_result.pop("schema_version")
    invalid_result_path.write_text(json.dumps(invalid_result), encoding="utf-8")

    skipped_dir = settings.runs_workspace / "skipped-dir"
    skipped_dir.mkdir(parents=True)

    report_stdout = io.StringIO()
    report_exit_code = main(
        [
            "--report-workspace-policy",
            "--workspace",
            str(settings.runs_workspace),
            "--retention-days",
            "7",
        ],
        stdout=report_stdout,
        stderr=io.StringIO(),
    )

    output = report_stdout.getvalue()
    assert report_exit_code == 0
    assert "Workspace policy report: completed" in output
    assert "Manual review required: 1" in output
    assert "Invalid runs: 1" in output
    assert "Flagged runs:" in output
    assert Path(warning_payload["artifacts"]["run_dir"]).name in output
    assert Path(invalid_payload["artifacts"]["run_dir"]).name in output
    assert "Skipped path names: skipped-dir" in output


def test_cli_can_bulk_export_workspace_runs_in_json(tmp_path: Path) -> None:
    settings = build_settings(tmp_path)
    run_payloads: list[dict[str, object]] = []
    for _ in range(5):
        stdout = io.StringIO()
        exit_code = main(
            ["--prompt", PROMPT, "--output", "json"],
            settings_loader=lambda: settings,
            stdout=stdout,
            stderr=io.StringIO(),
        )
        assert exit_code == 0
        run_payloads.append(json.loads(stdout.getvalue()))

    clean_payload, warning_payload, blocked_payload, invalid_payload, broken_payload = run_payloads

    warning_result_path = Path(warning_payload["artifacts"]["result_schema_path"])
    warning_result = json.loads(warning_result_path.read_text(encoding="utf-8"))
    warning_result["status"] = "completed_with_fallback"
    warning_result["metrics_source"] = "fallback_estimate"
    warning_result["fallback_used"] = True
    warning_result["warnings"] = ["Fallback-derived metrics should be reviewed before promotion."]
    warning_result_path.write_text(json.dumps(warning_result), encoding="utf-8")

    for payload in (blocked_payload, broken_payload):
        result_path = Path(payload["artifacts"]["result_schema_path"])
        backend_status_path = Path(payload["artifacts"]["backend_status_path"])
        backend_status = json.loads(backend_status_path.read_text(encoding="utf-8"))
        backend_status["backend_mode"] = "docker"
        backend_status["status"] = "failed"
        backend_status["exit_code"] = 2
        backend_status["container_id"] = "container-123"
        backend_status["container_status"] = "exited"
        backend_status["cleanup_status"] = "removed"
        backend_status_path.write_text(json.dumps(backend_status), encoding="utf-8")

        backend_metadata_path = Path(payload["artifacts"]["backend_metadata_path"])
        backend_metadata = json.loads(backend_metadata_path.read_text(encoding="utf-8"))
        backend_metadata["backend_mode"] = "docker"
        backend_metadata_path.write_text(json.dumps(backend_metadata), encoding="utf-8")

        result = json.loads(result_path.read_text(encoding="utf-8"))
        result["backend_mode"] = "docker"
        result["backend_status"] = "failed"
        result["backend_status_details"] = backend_status
        result["backend_metadata"] = backend_metadata
        result_path.write_text(json.dumps(result), encoding="utf-8")

    invalid_result_path = Path(invalid_payload["artifacts"]["result_schema_path"])
    invalid_result = json.loads(invalid_result_path.read_text(encoding="utf-8"))
    invalid_result.pop("schema_version")
    invalid_result_path.write_text(json.dumps(invalid_result), encoding="utf-8")

    broken_result = json.loads(Path(broken_payload["artifacts"]["result_schema_path"]).read_text(encoding="utf-8"))
    Path(broken_result["artifacts"]["metrics_path"]).unlink()

    skipped_dir = settings.runs_workspace / "skipped-dir"
    skipped_dir.mkdir(parents=True)

    export_stdout = io.StringIO()
    export_stderr = io.StringIO()
    export_output_dir = tmp_path / "workspace-exports"
    export_exit_code = main(
        [
            "--export-workspace-runs",
            "--workspace",
            str(settings.runs_workspace),
            "--export-output-dir",
            str(export_output_dir),
            "--output",
            "json",
        ],
        stdout=export_stdout,
        stderr=export_stderr,
    )

    payload = json.loads(export_stdout.getvalue())
    assert export_exit_code == 0
    assert export_stderr.getvalue() == ""
    assert payload["summary"]["discovered_count"] == 6
    assert payload["summary"]["exported_count"] == 2
    assert payload["summary"]["blocked_count"] == 3
    assert payload["summary"]["skipped_count"] == 1
    assert payload["summary"]["failed_count"] == 0
    assert (export_output_dir / f"{Path(clean_payload['artifacts']['run_dir']).name}-artifacts.zip").exists() is True
    assert (export_output_dir / f"{Path(warning_payload['artifacts']['run_dir']).name}-artifacts.zip").exists() is True
    assert sorted(payload["blocked_run_names"]) == sorted(
        [
            Path(blocked_payload["artifacts"]["run_dir"]).name,
            Path(broken_payload["artifacts"]["run_dir"]).name,
            Path(invalid_payload["artifacts"]["run_dir"]).name,
        ]
    )

    override_stdout = io.StringIO()
    override_output_dir = tmp_path / "workspace-override-exports"
    override_exit_code = main(
        [
            "--export-workspace-runs",
            "--workspace",
            str(settings.runs_workspace),
            "--export-output-dir",
            str(override_output_dir),
            "--allow-degraded-export",
            "--output",
            "json",
        ],
        stdout=override_stdout,
        stderr=io.StringIO(),
    )

    override_payload = json.loads(override_stdout.getvalue())
    assert override_exit_code == 0
    assert override_payload["summary"]["exported_count"] == 3
    assert override_payload["summary"]["blocked_count"] == 1
    assert override_payload["summary"]["failed_count"] == 1
    assert override_payload["summary"]["override_export_count"] == 1
    assert (override_output_dir / f"{Path(blocked_payload['artifacts']['run_dir']).name}-artifacts.zip").exists() is True
    assert override_payload["failed_run_names"] == [Path(broken_payload["artifacts"]["run_dir"]).name]


def test_cli_workspace_export_text_output_summarizes_outcomes(tmp_path: Path) -> None:
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
    blocked_payload = json.loads(first_stdout.getvalue())
    invalid_payload = json.loads(second_stdout.getvalue())

    blocked_result_path = Path(blocked_payload["artifacts"]["result_schema_path"])
    blocked_backend_status_path = Path(blocked_payload["artifacts"]["backend_status_path"])
    blocked_backend_status = json.loads(blocked_backend_status_path.read_text(encoding="utf-8"))
    blocked_backend_status["backend_mode"] = "docker"
    blocked_backend_status["status"] = "failed"
    blocked_backend_status["exit_code"] = 2
    blocked_backend_status["container_id"] = "container-123"
    blocked_backend_status["container_status"] = "exited"
    blocked_backend_status["cleanup_status"] = "removed"
    blocked_backend_status_path.write_text(json.dumps(blocked_backend_status), encoding="utf-8")

    blocked_backend_metadata_path = Path(blocked_payload["artifacts"]["backend_metadata_path"])
    blocked_backend_metadata = json.loads(blocked_backend_metadata_path.read_text(encoding="utf-8"))
    blocked_backend_metadata["backend_mode"] = "docker"
    blocked_backend_metadata_path.write_text(json.dumps(blocked_backend_metadata), encoding="utf-8")

    blocked_result = json.loads(blocked_result_path.read_text(encoding="utf-8"))
    blocked_result["backend_mode"] = "docker"
    blocked_result["backend_status"] = "failed"
    blocked_result["backend_status_details"] = blocked_backend_status
    blocked_result["backend_metadata"] = blocked_backend_metadata
    blocked_result_path.write_text(json.dumps(blocked_result), encoding="utf-8")

    invalid_result_path = Path(invalid_payload["artifacts"]["result_schema_path"])
    invalid_result = json.loads(invalid_result_path.read_text(encoding="utf-8"))
    invalid_result.pop("schema_version")
    invalid_result_path.write_text(json.dumps(invalid_result), encoding="utf-8")

    skipped_dir = settings.runs_workspace / "skipped-dir"
    skipped_dir.mkdir(parents=True)

    export_stdout = io.StringIO()
    export_exit_code = main(
        [
            "--export-workspace-runs",
            "--workspace",
            str(settings.runs_workspace),
            "--export-output-dir",
            str(tmp_path / "exports"),
        ],
        stdout=export_stdout,
        stderr=io.StringIO(),
    )

    output = export_stdout.getvalue()
    assert export_exit_code == 0
    assert "Workspace export: completed" in output
    assert "Blocked runs: 2" in output
    assert "Skipped paths: 1" in output
    assert "Exported archives:" in output
    assert "Blocked or failed:" in output
    assert Path(blocked_payload["artifacts"]["run_dir"]).name in output
    assert Path(invalid_payload["artifacts"]["run_dir"]).name in output
    assert "Skipped path names: skipped-dir" in output
