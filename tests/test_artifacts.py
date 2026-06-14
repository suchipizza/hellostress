from __future__ import annotations

import json
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from fea_engine import (
    ARTIFACT_SCHEMA_VERSION,
    EXPORT_MANIFEST_NAME,
    EXPORT_MANIFEST_VERSION,
    MAX_SUPPORTED_ARTIFACT_SCHEMA_VERSION,
    ArtifactValidationError,
    ArtifactWorkflowError,
    build_bundle_summary,
    build_cleanup_summary,
    cleanup_run_workspace,
    export_artifact_bundle,
    load_artifact_bundle,
)


def write_bundle(tmp_path: Path) -> Path:
    return write_bundle_at_run_dir(tmp_path / "run")


def write_bundle_at_run_dir(run_dir: Path) -> Path:
    results_dir = run_dir / "results"
    results_dir.mkdir(parents=True)
    metrics_path = results_dir / "metrics.json"
    metrics_path.write_text(json.dumps({"max_deflection": 0.1, "max_stress": 2.0}), encoding="utf-8")
    (run_dir / "simulation.py").write_text("print('simulation')\n", encoding="utf-8")
    (run_dir / "solver.stdout.log").write_text("stdout\n", encoding="utf-8")
    (run_dir / "solver.stderr.log").write_text("", encoding="utf-8")
    backend_status_path = run_dir / "backend_status.json"
    backend_metadata_path = run_dir / "backend_metadata.json"
    run_result_path = run_dir / "run_result.json"

    backend_status_path.write_text(
        json.dumps(
            {
                "schema_version": ARTIFACT_SCHEMA_VERSION,
                "backend_mode": "mock",
                "status": "succeeded",
                "exit_code": 0,
                "timed_out": False,
                "metrics_path": str(metrics_path),
                "metrics_present": True,
                "container_id": None,
                "container_status": "not_applicable",
                "cleanup_status": "not_applicable",
            }
        ),
        encoding="utf-8",
    )
    backend_metadata_path.write_text(
        json.dumps(
            {
                "schema_version": ARTIFACT_SCHEMA_VERSION,
                "backend_mode": "mock",
                "run_dir": str(run_dir),
                "docker_image": None,
                "docker_version": None,
                "timeout_seconds": 60,
                "runtime": {"cleanup_status": "not_applicable"},
                "run_metadata": {"command": ["mock"], "exit_code": 0},
            }
        ),
        encoding="utf-8",
    )
    run_result_path.write_text(
        json.dumps(
            {
                "schema_version": ARTIFACT_SCHEMA_VERSION,
                "status": "completed",
                "backend_mode": "mock",
                "backend_status": "succeeded",
                "metrics_source": "solver_artifact",
                "fallback_used": False,
                "warnings": [],
                "backend_status_details": json.loads(backend_status_path.read_text(encoding="utf-8")),
                "backend_metadata": json.loads(backend_metadata_path.read_text(encoding="utf-8")),
                "artifacts": {
                    "run_dir": str(run_dir),
                    "script_path": str(run_dir / "simulation.py"),
                    "results_dir": str(results_dir),
                    "metrics_path": str(metrics_path),
                    "backend_status_path": str(backend_status_path),
                    "backend_metadata_path": str(backend_metadata_path),
                    "generated_files": [str(metrics_path)],
                },
                "run_metadata": {
                    "command": ["mock"],
                    "exit_code": 0,
                    "stdout_path": str(run_dir / "solver.stdout.log"),
                    "stderr_path": str(run_dir / "solver.stderr.log"),
                    "stdout_excerpt": "",
                    "stderr_excerpt": "",
                    "timed_out": False,
                },
                "runtime_metadata": {"cleanup_status": "not_applicable"},
            }
        ),
        encoding="utf-8",
    )
    return run_result_path


def mutate_bundle_to_failed_backend(run_result_path: Path) -> None:
    run_result_payload = json.loads(run_result_path.read_text(encoding="utf-8"))
    backend_status_path = Path(run_result_payload["artifacts"]["backend_status_path"])
    backend_metadata_path = Path(run_result_payload["artifacts"]["backend_metadata_path"])

    backend_status_payload = json.loads(backend_status_path.read_text(encoding="utf-8"))
    backend_status_payload["backend_mode"] = "docker"
    backend_status_payload["status"] = "failed"
    backend_status_payload["exit_code"] = 2
    backend_status_payload["timed_out"] = False
    backend_status_payload["metrics_present"] = True
    backend_status_payload["container_id"] = "container-123"
    backend_status_payload["container_status"] = "exited"
    backend_status_payload["cleanup_status"] = "removed"
    backend_status_path.write_text(json.dumps(backend_status_payload), encoding="utf-8")

    backend_metadata_payload = json.loads(backend_metadata_path.read_text(encoding="utf-8"))
    backend_metadata_payload["backend_mode"] = "docker"
    backend_metadata_path.write_text(json.dumps(backend_metadata_payload), encoding="utf-8")

    run_result_payload["backend_mode"] = "docker"
    run_result_payload["backend_status"] = "failed"
    run_result_payload["backend_status_details"] = backend_status_payload
    run_result_payload["backend_metadata"] = backend_metadata_payload
    run_result_path.write_text(json.dumps(run_result_payload), encoding="utf-8")


def test_load_artifact_bundle_validates_referenced_files(tmp_path: Path) -> None:
    run_result_path = write_bundle(tmp_path)

    bundle = load_artifact_bundle(run_result_path)

    assert bundle.run_result["schema_version"] == ARTIFACT_SCHEMA_VERSION
    assert bundle.backend_status["status"] == "succeeded"
    assert bundle.backend_metadata["backend_mode"] == "mock"
    summary = build_bundle_summary(bundle)
    assert summary["compatibility"]["supported"] is True
    assert summary["diagnostics"]["all_referenced_files_present"] is True
    assert summary["diagnostics"]["all_embedded_payloads_consistent"] is True
    assert summary["policy"]["quality_gate"]["passed"] is True
    assert summary["policy"]["export"]["allowed"] is True
    assert summary["policy"]["promotion"]["allowed"] is True


def test_load_artifact_bundle_rejects_missing_schema_version(tmp_path: Path) -> None:
    run_result_path = write_bundle(tmp_path)
    payload = json.loads(run_result_path.read_text(encoding="utf-8"))
    payload.pop("schema_version")
    run_result_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ArtifactValidationError, match="schema_version"):
        load_artifact_bundle(run_result_path)


def test_load_artifact_bundle_rejects_missing_backend_file(tmp_path: Path) -> None:
    run_result_path = write_bundle(tmp_path)
    payload = json.loads(run_result_path.read_text(encoding="utf-8"))
    payload["artifacts"]["backend_status_path"] = str(tmp_path / "missing.json")
    run_result_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ArtifactValidationError, match="backend_status.json does not exist"):
        load_artifact_bundle(run_result_path)


def test_load_artifact_bundle_rejects_unsupported_schema_version(tmp_path: Path) -> None:
    run_result_path = write_bundle(tmp_path)
    payload = json.loads(run_result_path.read_text(encoding="utf-8"))
    payload["schema_version"] = MAX_SUPPORTED_ARTIFACT_SCHEMA_VERSION + 1
    run_result_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ArtifactValidationError, match="unsupported"):
        load_artifact_bundle(run_result_path)


def test_build_bundle_summary_reports_inconsistent_embedded_payloads(tmp_path: Path) -> None:
    run_result_path = write_bundle(tmp_path)
    payload = json.loads(run_result_path.read_text(encoding="utf-8"))
    payload["backend_status_details"]["status"] = "failed"
    run_result_path.write_text(json.dumps(payload), encoding="utf-8")

    bundle = load_artifact_bundle(run_result_path)
    summary = build_bundle_summary(bundle)

    assert summary["diagnostics"]["all_embedded_payloads_consistent"] is False
    assert summary["diagnostics"]["consistency_checks"]["embedded_backend_status_matches_file"] is False


def test_build_bundle_summary_reports_triage_issues_for_degraded_run(tmp_path: Path) -> None:
    run_result_path = write_bundle(tmp_path)
    run_result_payload = json.loads(run_result_path.read_text(encoding="utf-8"))
    backend_status_path = Path(run_result_payload["artifacts"]["backend_status_path"])
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
    run_result_path.write_text(json.dumps(run_result_payload), encoding="utf-8")

    metrics_path = Path(run_result_payload["artifacts"]["metrics_path"])
    metrics_path.unlink()

    bundle = load_artifact_bundle(run_result_path)
    summary = build_bundle_summary(bundle)
    issue_codes = {issue["code"] for issue in summary["triage"]["issues"]}

    assert summary["triage"]["severity"] == "error"
    assert summary["triage"]["error_count"] >= 3
    assert "backend_timed_out" in issue_codes
    assert "metrics_missing" in issue_codes
    assert "fallback_used" in issue_codes
    assert "container_cleanup_incomplete" in issue_codes
    assert "missing_referenced_file" in issue_codes
    assert "missing_generated_file" in issue_codes
    assert summary["policy"]["quality_gate"]["passed"] is False
    assert summary["policy"]["export"]["allowed"] is False
    assert summary["policy"]["promotion"]["allowed"] is False
    assert any("stderr log" in action for action in summary["triage"]["suggested_actions"])
    assert any("Re-run the simulation" in action for action in summary["triage"]["suggested_actions"])


def test_export_artifact_bundle_writes_zip_with_expected_files(tmp_path: Path) -> None:
    run_result_path = write_bundle(tmp_path)
    export_result = export_artifact_bundle(run_result_path)
    archive_path = export_result.archive_path

    assert archive_path.exists()
    with zipfile.ZipFile(archive_path) as archive:
        names = set(archive.namelist())
        manifest_payload = json.loads(archive.read(EXPORT_MANIFEST_NAME).decode("utf-8"))
    assert "run_result.json" in names
    assert "backend_status.json" in names
    assert "backend_metadata.json" in names
    assert "simulation.py" in names
    assert "results/metrics.json" in names
    assert "solver.stdout.log" in names
    assert "solver.stderr.log" in names
    assert EXPORT_MANIFEST_NAME in names
    assert export_result.archive_sha256
    assert export_result.policy["export"]["allowed"] is True
    assert export_result.policy_override_used is False
    assert manifest_payload["manifest_version"] == EXPORT_MANIFEST_VERSION
    assert manifest_payload["file_count"] >= 7
    manifest_paths = {entry["relative_path"] for entry in manifest_payload["files"]}
    assert "run_result.json" in manifest_paths
    assert "results/metrics.json" in manifest_paths
    for entry in manifest_payload["files"]:
        assert len(entry["sha256"]) == 64


def test_export_artifact_bundle_blocks_policy_failed_bundle_by_default(tmp_path: Path) -> None:
    run_result_path = write_bundle(tmp_path)
    mutate_bundle_to_failed_backend(run_result_path)

    with pytest.raises(ArtifactWorkflowError, match="Export policy blocked"):
        export_artifact_bundle(run_result_path)


def test_export_artifact_bundle_can_override_policy_failure(tmp_path: Path) -> None:
    run_result_path = write_bundle(tmp_path)
    mutate_bundle_to_failed_backend(run_result_path)

    export_result = export_artifact_bundle(run_result_path, allow_degraded=True)

    assert export_result.archive_path.exists()
    assert export_result.policy["quality_gate"]["passed"] is False
    assert export_result.policy["export"]["allowed"] is False
    assert export_result.policy_override_used is True


def test_cleanup_run_workspace_deletes_old_runs_and_keeps_latest(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    old_run = write_bundle_at_run_dir(workspace / "old-run")
    recent_run = write_bundle_at_run_dir(workspace / "recent-run")
    keep_run = write_bundle_at_run_dir(workspace / "keep-run")

    old_time = (datetime.now(timezone.utc) - timedelta(days=10)).timestamp()
    recent_time = (datetime.now(timezone.utc) - timedelta(days=5)).timestamp()
    keep_time = datetime.now(timezone.utc).timestamp()
    import os

    for path, value in [(old_run, old_time), (recent_run, recent_time), (keep_run, keep_time)]:
        run_dir = path.parent
        os.utime(path, (value, value))
        os.utime(run_dir, (value, value))

    result = cleanup_run_workspace(workspace, retention_days=7, keep_latest=1, dry_run=False)

    deleted_names = {path.name for path in result.deleted_runs}
    retained_names = {path.name for path in result.retained_runs}
    assert deleted_names == {"old-run"}
    assert retained_names == {"recent-run", "keep-run"}
    assert (workspace / "old-run").exists() is False
    assert (workspace / "recent-run").exists() is True
    assert (workspace / "keep-run").exists() is True


def test_cleanup_run_workspace_dry_run_keeps_files(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    old_run = write_bundle_at_run_dir(workspace / "old-run")
    old_time = (datetime.now(timezone.utc) - timedelta(days=10)).timestamp()
    import os

    os.utime(old_run, (old_time, old_time))
    os.utime(old_run.parent, (old_time, old_time))

    result = cleanup_run_workspace(workspace, retention_days=7, dry_run=True)

    assert len(result.deleted_runs) == 1
    assert old_run.parent.exists() is True
    summary = build_cleanup_summary(result)
    assert summary["summary"]["deleted_count"] == 1
    assert summary["summary"]["retained_count"] == 0
    assert summary["deleted_run_names"] == ["old-run"]
