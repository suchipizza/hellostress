from __future__ import annotations

import json
from pathlib import Path

import pytest

from fea_engine import (
    ARTIFACT_SCHEMA_VERSION,
    MAX_SUPPORTED_ARTIFACT_SCHEMA_VERSION,
    ArtifactValidationError,
    build_bundle_summary,
    load_artifact_bundle,
)


def write_bundle(tmp_path: Path) -> Path:
    run_dir = tmp_path / "run"
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
