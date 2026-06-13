from __future__ import annotations

import json
import shutil
import zipfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .errors import ArtifactValidationError, ArtifactWorkflowError


ARTIFACT_SCHEMA_VERSION = 1
MIN_SUPPORTED_ARTIFACT_SCHEMA_VERSION = 1
MAX_SUPPORTED_ARTIFACT_SCHEMA_VERSION = ARTIFACT_SCHEMA_VERSION

RUN_RESULT_REQUIRED_KEYS = {
    "schema_version",
    "status",
    "backend_mode",
    "backend_status",
    "metrics_source",
    "fallback_used",
    "warnings",
    "backend_status_details",
    "backend_metadata",
    "artifacts",
    "run_metadata",
    "runtime_metadata",
}

BACKEND_STATUS_REQUIRED_KEYS = {
    "schema_version",
    "backend_mode",
    "status",
    "exit_code",
    "timed_out",
    "metrics_path",
    "metrics_present",
    "container_id",
    "container_status",
    "cleanup_status",
}

BACKEND_METADATA_REQUIRED_KEYS = {
    "schema_version",
    "backend_mode",
    "run_dir",
    "docker_image",
    "docker_version",
    "timeout_seconds",
    "runtime",
    "run_metadata",
}


@dataclass(frozen=True)
class ArtifactBundle:
    run_result_path: Path
    backend_status_path: Path
    backend_metadata_path: Path
    run_result: dict[str, Any]
    backend_status: dict[str, Any]
    backend_metadata: dict[str, Any]


@dataclass(frozen=True)
class RetentionCleanupResult:
    workspace: Path
    retention_days: int
    keep_latest: int
    dry_run: bool
    deleted_runs: list[Path]
    retained_runs: list[Path]
    skipped_paths: list[Path]


def load_artifact_bundle(run_result_path: Path) -> ArtifactBundle:
    run_result_payload = _load_json(run_result_path, artifact_name="run_result.json")
    validate_run_result_payload(run_result_payload, path=run_result_path)

    artifacts = run_result_payload["artifacts"]
    backend_status_path = _coerce_path(artifacts.get("backend_status_path"), "backend_status_path", run_result_path)
    backend_metadata_path = _coerce_path(
        artifacts.get("backend_metadata_path"),
        "backend_metadata_path",
        run_result_path,
    )

    backend_status_payload = _load_json(backend_status_path, artifact_name="backend_status.json")
    validate_backend_status_payload(backend_status_payload, path=backend_status_path)

    backend_metadata_payload = _load_json(backend_metadata_path, artifact_name="backend_metadata.json")
    validate_backend_metadata_payload(backend_metadata_payload, path=backend_metadata_path)

    return ArtifactBundle(
        run_result_path=run_result_path,
        backend_status_path=backend_status_path,
        backend_metadata_path=backend_metadata_path,
        run_result=run_result_payload,
        backend_status=backend_status_payload,
        backend_metadata=backend_metadata_payload,
    )


def validate_run_result_payload(payload: dict[str, Any], *, path: Path | None = None) -> None:
    _validate_required_keys(payload, RUN_RESULT_REQUIRED_KEYS, artifact_name="run_result.json", path=path)
    _validate_schema_version(payload, artifact_name="run_result.json", path=path)
    artifacts = payload["artifacts"]
    if not isinstance(artifacts, dict):
        raise ArtifactValidationError(_with_path("run_result.json field 'artifacts' must be an object.", path))
    for key in {"run_dir", "script_path", "results_dir", "metrics_path", "backend_status_path", "backend_metadata_path"}:
        if key not in artifacts:
            raise ArtifactValidationError(_with_path(f"run_result.json artifacts missing '{key}'.", path))


def validate_backend_status_payload(payload: dict[str, Any], *, path: Path | None = None) -> None:
    _validate_required_keys(payload, BACKEND_STATUS_REQUIRED_KEYS, artifact_name="backend_status.json", path=path)
    _validate_schema_version(payload, artifact_name="backend_status.json", path=path)


def validate_backend_metadata_payload(payload: dict[str, Any], *, path: Path | None = None) -> None:
    _validate_required_keys(payload, BACKEND_METADATA_REQUIRED_KEYS, artifact_name="backend_metadata.json", path=path)
    _validate_schema_version(payload, artifact_name="backend_metadata.json", path=path)


def build_bundle_summary(bundle: ArtifactBundle) -> dict[str, Any]:
    run_result = bundle.run_result
    artifacts = run_result["artifacts"]
    diagnostics = _build_diagnostics(bundle)
    return {
        "valid": True,
        "schema_version": run_result["schema_version"],
        "compatibility": {
            "supported": True,
            "current_schema_version": ARTIFACT_SCHEMA_VERSION,
            "minimum_supported_schema_version": MIN_SUPPORTED_ARTIFACT_SCHEMA_VERSION,
            "maximum_supported_schema_version": MAX_SUPPORTED_ARTIFACT_SCHEMA_VERSION,
            "policy": (
                "Artifact bundles are supported when every artifact file declares a schema_version "
                f"between {MIN_SUPPORTED_ARTIFACT_SCHEMA_VERSION} and {MAX_SUPPORTED_ARTIFACT_SCHEMA_VERSION}."
            ),
        },
        "status": run_result["status"],
        "backend_mode": run_result["backend_mode"],
        "backend_status": run_result["backend_status"],
        "metrics_source": run_result["metrics_source"],
        "fallback_used": run_result["fallback_used"],
        "warnings": run_result["warnings"],
        "diagnostics": diagnostics,
        "paths": {
            "run_result_path": str(bundle.run_result_path),
            "backend_status_path": str(bundle.backend_status_path),
            "backend_metadata_path": str(bundle.backend_metadata_path),
            "run_dir": artifacts["run_dir"],
            "results_dir": artifacts["results_dir"],
            "metrics_path": artifacts["metrics_path"],
            "script_path": artifacts["script_path"],
            "stdout_path": run_result["run_metadata"]["stdout_path"],
            "stderr_path": run_result["run_metadata"]["stderr_path"],
        },
    }


def export_artifact_bundle(run_result_path: Path, output_path: Path | None = None) -> Path:
    bundle = load_artifact_bundle(run_result_path)
    run_dir = Path(bundle.run_result["artifacts"]["run_dir"]).resolve()
    if output_path is None:
        output_path = run_dir / f"{run_dir.name}-artifacts.zip"
    output_path = output_path.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    files_to_export = _bundle_files(bundle)
    with zipfile.ZipFile(output_path, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files_to_export:
            archive.write(path, arcname=str(path.relative_to(run_dir)))
    return output_path


def cleanup_run_workspace(
    workspace: Path,
    *,
    retention_days: int,
    keep_latest: int = 0,
    dry_run: bool = False,
) -> RetentionCleanupResult:
    if retention_days < 0:
        raise ArtifactWorkflowError("retention_days must be >= 0.")
    if keep_latest < 0:
        raise ArtifactWorkflowError("keep_latest must be >= 0.")

    workspace = workspace.expanduser().resolve()
    if not workspace.exists():
        return RetentionCleanupResult(
            workspace=workspace,
            retention_days=retention_days,
            keep_latest=keep_latest,
            dry_run=dry_run,
            deleted_runs=[],
            retained_runs=[],
            skipped_paths=[],
        )

    run_dirs = _discover_run_dirs(workspace)
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    sorted_runs = sorted(run_dirs, key=_run_sort_key, reverse=True)
    protected_runs = set(sorted_runs[:keep_latest])
    deleted_runs: list[Path] = []
    retained_runs: list[Path] = []
    skipped_paths: list[Path] = []

    for run_dir in sorted_runs:
        run_result_path = run_dir / "run_result.json"
        if not run_result_path.exists():
            skipped_paths.append(run_dir)
            continue

        run_time = datetime.fromtimestamp(run_result_path.stat().st_mtime, tz=timezone.utc)
        should_delete = run_dir not in protected_runs and run_time < cutoff
        if should_delete:
            deleted_runs.append(run_dir)
            if not dry_run:
                shutil.rmtree(run_dir)
        else:
            retained_runs.append(run_dir)

    return RetentionCleanupResult(
        workspace=workspace,
        retention_days=retention_days,
        keep_latest=keep_latest,
        dry_run=dry_run,
        deleted_runs=deleted_runs,
        retained_runs=retained_runs,
        skipped_paths=skipped_paths,
    )


def _load_json(path: Path, *, artifact_name: str) -> dict[str, Any]:
    if not path.exists():
        raise ArtifactValidationError(f"{artifact_name} does not exist: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ArtifactValidationError(f"{artifact_name} is not valid JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise ArtifactValidationError(f"{artifact_name} must contain a JSON object: {path}")
    return payload


def _validate_required_keys(
    payload: dict[str, Any],
    required_keys: set[str],
    *,
    artifact_name: str,
    path: Path | None,
) -> None:
    missing = sorted(required_keys - payload.keys())
    if missing:
        raise ArtifactValidationError(
            _with_path(f"{artifact_name} is missing required keys: {', '.join(missing)}.", path)
        )


def _validate_schema_version(payload: dict[str, Any], *, artifact_name: str, path: Path | None) -> None:
    version = payload.get("schema_version")
    if not isinstance(version, int):
        raise ArtifactValidationError(
            _with_path(
                f"{artifact_name} schema_version must be an integer; got {version!r}.",
                path,
            )
        )
    if version < MIN_SUPPORTED_ARTIFACT_SCHEMA_VERSION or version > MAX_SUPPORTED_ARTIFACT_SCHEMA_VERSION:
        raise ArtifactValidationError(
            _with_path(
                f"{artifact_name} schema_version {version} is unsupported; supported range is "
                f"{MIN_SUPPORTED_ARTIFACT_SCHEMA_VERSION}..{MAX_SUPPORTED_ARTIFACT_SCHEMA_VERSION}.",
                path,
            )
        )


def _build_diagnostics(bundle: ArtifactBundle) -> dict[str, Any]:
    run_result = bundle.run_result
    artifacts = run_result["artifacts"]
    generated_files = [Path(path) for path in artifacts.get("generated_files", [])]
    referenced_paths = {
        "run_dir": Path(artifacts["run_dir"]),
        "results_dir": Path(artifacts["results_dir"]),
        "script_path": Path(artifacts["script_path"]),
        "metrics_path": Path(artifacts["metrics_path"]),
        "backend_status_path": bundle.backend_status_path,
        "backend_metadata_path": bundle.backend_metadata_path,
        "stdout_path": Path(run_result["run_metadata"]["stdout_path"]),
        "stderr_path": Path(run_result["run_metadata"]["stderr_path"]),
    }
    path_checks = {name: path.exists() for name, path in referenced_paths.items()}
    generated_file_checks = {str(path): path.exists() for path in generated_files}
    consistency_checks = {
        "embedded_backend_status_matches_file": run_result["backend_status_details"] == bundle.backend_status,
        "embedded_backend_metadata_matches_file": run_result["backend_metadata"] == bundle.backend_metadata,
        "run_result_backend_status_matches_backend_status_file": run_result["backend_status"] == bundle.backend_status["status"],
        "run_result_backend_mode_matches_backend_status_file": run_result["backend_mode"] == bundle.backend_status["backend_mode"],
        "run_result_backend_mode_matches_backend_metadata_file": run_result["backend_mode"] == bundle.backend_metadata["backend_mode"],
    }
    all_files_present = all(path_checks.values()) and all(generated_file_checks.values())
    all_consistent = all(consistency_checks.values())
    return {
        "all_referenced_files_present": all_files_present,
        "all_embedded_payloads_consistent": all_consistent,
        "path_checks": path_checks,
        "generated_file_checks": generated_file_checks,
        "consistency_checks": consistency_checks,
        "generated_file_count": len(generated_files),
        "metrics_present": bool(bundle.backend_status["metrics_present"]),
    }


def _bundle_files(bundle: ArtifactBundle) -> list[Path]:
    run_result = bundle.run_result
    artifacts = run_result["artifacts"]
    run_dir = Path(artifacts["run_dir"]).resolve()
    candidate_paths = [
        bundle.run_result_path,
        bundle.backend_status_path,
        bundle.backend_metadata_path,
        Path(artifacts["script_path"]),
        Path(artifacts["metrics_path"]),
        Path(run_result["run_metadata"]["stdout_path"]),
        Path(run_result["run_metadata"]["stderr_path"]),
        *[Path(path) for path in artifacts.get("generated_files", [])],
    ]
    files: list[Path] = []
    seen: set[Path] = set()
    for path in candidate_paths:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        if not resolved.exists():
            raise ArtifactWorkflowError(f"Cannot export artifact bundle because a referenced file is missing: {path}")
        if run_dir not in resolved.parents and resolved != run_dir:
            raise ArtifactWorkflowError(f"Refusing to export file outside the run directory: {path}")
        if resolved.is_file():
            files.append(resolved)
    return files


def _discover_run_dirs(workspace: Path) -> list[Path]:
    if not workspace.exists():
        return []
    return sorted(path for path in workspace.iterdir() if path.is_dir())


def _run_sort_key(run_dir: Path) -> float:
    run_result_path = run_dir / "run_result.json"
    if run_result_path.exists():
        return run_result_path.stat().st_mtime
    return run_dir.stat().st_mtime


def _coerce_path(value: Any, field_name: str, run_result_path: Path) -> Path:
    if not isinstance(value, str) or not value:
        raise ArtifactValidationError(
            _with_path(f"run_result.json field '{field_name}' must be a non-empty string.", run_result_path)
        )
    return Path(value)


def _with_path(message: str, path: Path | None) -> str:
    if path is None:
        return message
    return f"{message} Path: {path}"


__all__ = [
    "ARTIFACT_SCHEMA_VERSION",
    "ArtifactBundle",
    "MAX_SUPPORTED_ARTIFACT_SCHEMA_VERSION",
    "MIN_SUPPORTED_ARTIFACT_SCHEMA_VERSION",
    "RetentionCleanupResult",
    "build_bundle_summary",
    "cleanup_run_workspace",
    "export_artifact_bundle",
    "load_artifact_bundle",
    "validate_backend_metadata_payload",
    "validate_backend_status_payload",
    "validate_run_result_payload",
]
