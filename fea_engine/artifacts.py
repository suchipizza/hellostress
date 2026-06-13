from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .errors import ArtifactValidationError


ARTIFACT_SCHEMA_VERSION = 1

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
    return {
        "valid": True,
        "schema_version": run_result["schema_version"],
        "status": run_result["status"],
        "backend_mode": run_result["backend_mode"],
        "backend_status": run_result["backend_status"],
        "metrics_source": run_result["metrics_source"],
        "fallback_used": run_result["fallback_used"],
        "warnings": run_result["warnings"],
        "paths": {
            "run_result_path": str(bundle.run_result_path),
            "backend_status_path": str(bundle.backend_status_path),
            "backend_metadata_path": str(bundle.backend_metadata_path),
            "run_dir": bundle.run_result["artifacts"]["run_dir"],
            "metrics_path": bundle.run_result["artifacts"]["metrics_path"],
            "script_path": bundle.run_result["artifacts"]["script_path"],
        },
    }


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
    if version != ARTIFACT_SCHEMA_VERSION:
        raise ArtifactValidationError(
            _with_path(
                f"{artifact_name} schema_version must be {ARTIFACT_SCHEMA_VERSION}; got {version!r}.",
                path,
            )
        )


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
    "build_bundle_summary",
    "load_artifact_bundle",
    "validate_backend_metadata_payload",
    "validate_backend_status_payload",
    "validate_run_result_payload",
]
