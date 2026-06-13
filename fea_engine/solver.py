from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .artifacts import ARTIFACT_SCHEMA_VERSION
from .errors import SolverExecutionError, UnsupportedSolverModeError
from .models import SimulationSpec
from .utils import AnalyticalEstimator


@dataclass
class SolverRunMetadata:
    command: list[str]
    exit_code: int
    stdout_path: Path
    stderr_path: Path
    stdout_excerpt: str = ""
    stderr_excerpt: str = ""
    timed_out: bool = False


@dataclass
class BackendRuntimeMetadata:
    container_id: Optional[str] = None
    created_at: str = ""
    started_at: str = ""
    finished_at: str = ""
    duration_seconds: Optional[float] = None
    container_status: str = "not_applicable"
    cleanup_status: str = "not_applicable"
    cleanup_error: str = ""
    state: dict[str, Any] = field(default_factory=dict)


@dataclass
class SolverArtifacts:
    run_dir: Path
    backend_mode: str
    backend_status: str
    script_path: Path
    results_dir: Path
    metrics_path: Path
    backend_status_path: Path
    backend_metadata_path: Path
    run_metadata: SolverRunMetadata
    runtime_metadata: BackendRuntimeMetadata
    generated_files: list[Path] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class FenicsSolver:
    """Executes generated FEniCS scripts via Docker or mock mode."""

    supported_modes = {"auto", "docker", "mock"}

    def __init__(
        self,
        mode: str = "auto",
        docker_image: str = "dolfinx/dolfinx:v0.7.3",
        timeout_seconds: int = 60,
        workspace: Optional[Path] = None,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.docker_image = docker_image
        self.workspace = workspace or Path(tempfile.gettempdir()) / "fea_runs"
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.mode = self._resolve_mode(mode)

    def _resolve_mode(self, requested: str) -> str:
        if requested not in self.supported_modes:
            raise UnsupportedSolverModeError(
                f"Unsupported solver mode '{requested}'. Supported modes: auto, docker, mock."
            )
        if requested != "auto":
            if requested == "docker" and not shutil.which("docker"):
                raise SolverExecutionError(
                    "Docker solver mode was requested, but Docker is not available on this machine.",
                    backend_mode="docker",
                )
            return requested
        if shutil.which("docker"):
            return "docker"
        return "mock"

    def run(self, spec: SimulationSpec, script: str) -> SolverArtifacts:
        run_dir = tempfile.mkdtemp(prefix="fea_", dir=self.workspace)
        run_path = Path(run_dir)
        script_path = run_path / "simulation.py"
        script_path.write_text(script, encoding="utf-8")
        results_dir = run_path / "results"
        results_dir.mkdir(exist_ok=True)
        metrics_path = results_dir / "metrics.json"
        backend_status_path = run_path / "backend_status.json"
        backend_metadata_path = run_path / "backend_metadata.json"
        stdout_path = run_path / "solver.stdout.log"
        stderr_path = run_path / "solver.stderr.log"

        if self.mode == "docker":
            run_metadata, runtime_metadata = self._run_in_docker(
                script_path,
                run_path,
                metrics_path,
                backend_status_path,
                backend_metadata_path,
                stdout_path,
                stderr_path,
            )
        else:
            run_metadata, runtime_metadata = self._run_mock(
                spec,
                metrics_path,
                backend_status_path,
                backend_metadata_path,
                stdout_path,
                stderr_path,
            )

        generated_files = [path for path in sorted(results_dir.iterdir()) if path.is_file()]
        warnings: list[str] = []
        if not metrics_path.exists():
            warnings.append("Solver backend did not produce metrics.json; post-processing may fall back to estimates.")
        backend_status = "succeeded"
        self._write_backend_artifacts(
            backend_mode=self.mode,
            backend_status=backend_status,
            run_dir=run_path,
            metrics_path=metrics_path,
            backend_status_path=backend_status_path,
            backend_metadata_path=backend_metadata_path,
            run_metadata=run_metadata,
            runtime_metadata=runtime_metadata,
        )

        return SolverArtifacts(
            run_dir=run_path,
            backend_mode=self.mode,
            backend_status=backend_status,
            script_path=script_path,
            results_dir=results_dir,
            metrics_path=metrics_path,
            backend_status_path=backend_status_path,
            backend_metadata_path=backend_metadata_path,
            run_metadata=run_metadata,
            runtime_metadata=runtime_metadata,
            generated_files=generated_files,
            warnings=warnings,
        )

    def _run_in_docker(
        self,
        script_path: Path,
        run_path: Path,
        metrics_path: Path,
        backend_status_path: Path,
        backend_metadata_path: Path,
        stdout_path: Path,
        stderr_path: Path,
    ) -> tuple[SolverRunMetadata, BackendRuntimeMetadata]:
        cmd = [
            "docker",
            "create",
            "-v",
            f"{script_path.parent}:/workspace",
            self.docker_image,
            "python3",
            "/workspace/simulation.py",
        ]
        runtime_metadata = BackendRuntimeMetadata(
            created_at=self._utcnow(),
            cleanup_status="pending",
            container_status="creating",
        )
        try:
            created = subprocess.run(
                cmd,
                check=True,
                timeout=self.timeout_seconds,
                capture_output=True,
                text=True,
            )
            runtime_metadata.container_id = (created.stdout or "").strip() or None
            if runtime_metadata.container_id is None:
                raise subprocess.CalledProcessError(
                    returncode=1,
                    cmd=cmd,
                    output=created.stdout,
                    stderr="docker create did not return a container id",
                )

            subprocess.run(
                ["docker", "start", runtime_metadata.container_id],
                check=True,
                capture_output=True,
                text=True,
            )
            runtime_metadata.started_at = self._utcnow()
            runtime_metadata.container_status = "running"

            wait_result = subprocess.run(
                ["docker", "wait", runtime_metadata.container_id],
                check=True,
                timeout=self.timeout_seconds,
                capture_output=True,
                text=True,
            )
            runtime_metadata.finished_at = self._utcnow()
            state = self._inspect_container_state(runtime_metadata.container_id)
            runtime_metadata.state = state
            runtime_metadata.container_status = state.get("Status", "exited")
            runtime_metadata.duration_seconds = self._duration_seconds(
                runtime_metadata.started_at,
                runtime_metadata.finished_at,
            )
            stdout_text, stderr_text = self._read_container_logs(runtime_metadata.container_id)
            metadata = self._write_run_metadata(
                command=cmd,
                exit_code=self._parse_exit_code(wait_result.stdout, state),
                stdout_text=stdout_text,
                stderr_text=stderr_text,
                stdout_path=stdout_path,
                stderr_path=stderr_path,
            )
            cleanup_status, cleanup_error = self._remove_container(runtime_metadata.container_id)
            runtime_metadata.cleanup_status = cleanup_status
            runtime_metadata.cleanup_error = cleanup_error

            if metadata.exit_code != 0:
                self._write_backend_artifacts(
                    backend_mode="docker",
                    backend_status="failed",
                    run_dir=run_path,
                    metrics_path=metrics_path,
                    backend_status_path=backend_status_path,
                    backend_metadata_path=backend_metadata_path,
                    run_metadata=metadata,
                    runtime_metadata=runtime_metadata,
                )
                raise SolverExecutionError(
                    "Docker solver execution failed.",
                    backend_mode="docker",
                    exit_code=metadata.exit_code,
                    command=metadata.command,
                    run_dir=run_path,
                    status_path=backend_status_path,
                    metadata_path=backend_metadata_path,
                    stdout_path=metadata.stdout_path,
                    stderr_path=metadata.stderr_path,
                    stdout_excerpt=metadata.stdout_excerpt,
                    stderr_excerpt=metadata.stderr_excerpt,
                    container_id=runtime_metadata.container_id,
                    cleanup_status=runtime_metadata.cleanup_status,
                )

            return metadata, runtime_metadata
        except subprocess.TimeoutExpired as exc:
            runtime_metadata.finished_at = self._utcnow()
            if runtime_metadata.container_id is not None:
                self._stop_container(runtime_metadata.container_id)
                runtime_metadata.state = self._inspect_container_state(runtime_metadata.container_id)
                runtime_metadata.container_status = runtime_metadata.state.get("Status", "timed_out")
            else:
                runtime_metadata.container_status = "timed_out"
                runtime_metadata.cleanup_status = "not_needed"
            runtime_metadata.duration_seconds = self._duration_seconds(
                runtime_metadata.started_at,
                runtime_metadata.finished_at,
            )
            stdout_text, stderr_text = self._read_container_logs(runtime_metadata.container_id)
            if not stdout_text and not stderr_text:
                stdout_text = self._coerce_output(exc.stdout)
                stderr_text = self._coerce_output(exc.stderr)
            metadata = self._write_run_metadata(
                command=cmd,
                exit_code=-1,
                stdout_text=stdout_text,
                stderr_text=stderr_text,
                stdout_path=stdout_path,
                stderr_path=stderr_path,
                timed_out=True,
            )
            if runtime_metadata.container_id is not None:
                cleanup_status, cleanup_error = self._remove_container(runtime_metadata.container_id)
                runtime_metadata.cleanup_status = cleanup_status
                runtime_metadata.cleanup_error = cleanup_error
            self._write_backend_artifacts(
                backend_mode="docker",
                backend_status="timed_out",
                run_dir=run_path,
                metrics_path=metrics_path,
                backend_status_path=backend_status_path,
                backend_metadata_path=backend_metadata_path,
                run_metadata=metadata,
                runtime_metadata=runtime_metadata,
            )
            raise SolverExecutionError(
                f"Docker solver timed out after {self.timeout_seconds} seconds.",
                backend_mode="docker",
                exit_code=metadata.exit_code,
                command=metadata.command,
                run_dir=run_path,
                status_path=backend_status_path,
                metadata_path=backend_metadata_path,
                stdout_path=metadata.stdout_path,
                stderr_path=metadata.stderr_path,
                stdout_excerpt=metadata.stdout_excerpt,
                stderr_excerpt=metadata.stderr_excerpt,
                timed_out=metadata.timed_out,
                container_id=runtime_metadata.container_id,
                cleanup_status=runtime_metadata.cleanup_status,
            ) from exc
        except subprocess.CalledProcessError as exc:
            runtime_metadata.finished_at = self._utcnow()
            if runtime_metadata.container_id is not None:
                runtime_metadata.state = self._inspect_container_state(runtime_metadata.container_id)
                runtime_metadata.container_status = runtime_metadata.state.get("Status", "failed")
            runtime_metadata.duration_seconds = self._duration_seconds(
                runtime_metadata.started_at,
                runtime_metadata.finished_at,
            )
            stdout_text, stderr_text = self._read_container_logs(runtime_metadata.container_id)
            if not stdout_text and not stderr_text:
                stdout_text = self._coerce_output(exc.stdout)
                stderr_text = self._coerce_output(exc.stderr)
            metadata = self._write_run_metadata(
                command=cmd,
                exit_code=exc.returncode,
                stdout_text=stdout_text,
                stderr_text=stderr_text,
                stdout_path=stdout_path,
                stderr_path=stderr_path,
            )
            if runtime_metadata.container_id is not None:
                cleanup_status, cleanup_error = self._remove_container(runtime_metadata.container_id)
                runtime_metadata.cleanup_status = cleanup_status
                runtime_metadata.cleanup_error = cleanup_error
            else:
                runtime_metadata.container_status = "failed"
                runtime_metadata.cleanup_status = "not_needed"
            self._write_backend_artifacts(
                backend_mode="docker",
                backend_status="failed",
                run_dir=run_path,
                metrics_path=metrics_path,
                backend_status_path=backend_status_path,
                backend_metadata_path=backend_metadata_path,
                run_metadata=metadata,
                runtime_metadata=runtime_metadata,
            )
            raise SolverExecutionError(
                "Docker solver execution failed.",
                backend_mode="docker",
                exit_code=metadata.exit_code,
                command=metadata.command,
                run_dir=run_path,
                status_path=backend_status_path,
                metadata_path=backend_metadata_path,
                stdout_path=metadata.stdout_path,
                stderr_path=metadata.stderr_path,
                stdout_excerpt=metadata.stdout_excerpt,
                stderr_excerpt=metadata.stderr_excerpt,
                container_id=runtime_metadata.container_id,
                cleanup_status=runtime_metadata.cleanup_status,
            ) from exc

    def _run_mock(
        self,
        spec: SimulationSpec,
        metrics_path: Path,
        backend_status_path: Path,
        backend_metadata_path: Path,
        stdout_path: Path,
        stderr_path: Path,
    ) -> tuple[SolverRunMetadata, BackendRuntimeMetadata]:
        metrics = AnalyticalEstimator.estimate(spec)
        metrics_path.parent.mkdir(exist_ok=True)
        with open(metrics_path, "w", encoding="utf-8") as fh:
            json.dump(metrics, fh)
        return (
            self._write_run_metadata(
                command=["mock"],
                exit_code=0,
                stdout_text="Mock solver produced analytical estimate.",
                stderr_text="",
                stdout_path=stdout_path,
                stderr_path=stderr_path,
            ),
            BackendRuntimeMetadata(),
        )

    def _write_run_metadata(
        self,
        *,
        command: list[str],
        exit_code: int,
        stdout_text: str,
        stderr_text: str,
        stdout_path: Path,
        stderr_path: Path,
        timed_out: bool = False,
    ) -> SolverRunMetadata:
        stdout_path.write_text(stdout_text, encoding="utf-8")
        stderr_path.write_text(stderr_text, encoding="utf-8")
        return SolverRunMetadata(
            command=command,
            exit_code=exit_code,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            stdout_excerpt=self._excerpt(stdout_text),
            stderr_excerpt=self._excerpt(stderr_text),
            timed_out=timed_out,
        )

    def _excerpt(self, value: str, limit: int = 240) -> str:
        return value.strip().replace("\n", " ")[:limit]

    def _coerce_output(self, value: object) -> str:
        if value is None:
            return ""
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="replace")
        return str(value)

    def _write_backend_artifacts(
        self,
        *,
        backend_mode: str,
        backend_status: str,
        run_dir: Path,
        metrics_path: Path,
        backend_status_path: Path,
        backend_metadata_path: Path,
        run_metadata: SolverRunMetadata,
        runtime_metadata: BackendRuntimeMetadata,
    ) -> None:
        status_payload = {
            "schema_version": ARTIFACT_SCHEMA_VERSION,
            "backend_mode": backend_mode,
            "status": backend_status,
            "exit_code": run_metadata.exit_code,
            "timed_out": run_metadata.timed_out,
            "metrics_path": str(metrics_path),
            "metrics_present": metrics_path.exists(),
            "container_id": runtime_metadata.container_id,
            "container_status": runtime_metadata.container_status,
            "cleanup_status": runtime_metadata.cleanup_status,
        }
        metadata_payload = {
            "schema_version": ARTIFACT_SCHEMA_VERSION,
            "backend_mode": backend_mode,
            "run_dir": str(run_dir),
            "docker_image": self.docker_image if backend_mode == "docker" else None,
            "docker_version": self._docker_version() if backend_mode == "docker" else None,
            "timeout_seconds": self.timeout_seconds,
            "runtime": asdict(runtime_metadata),
            "run_metadata": self._metadata_to_json(run_metadata),
        }
        backend_status_path.write_text(json.dumps(status_payload, indent=2), encoding="utf-8")
        backend_metadata_path.write_text(json.dumps(metadata_payload, indent=2), encoding="utf-8")

    def _metadata_to_json(self, metadata: SolverRunMetadata) -> dict[str, Any]:
        payload = asdict(metadata)
        payload["stdout_path"] = str(metadata.stdout_path)
        payload["stderr_path"] = str(metadata.stderr_path)
        return payload

    def _docker_version(self) -> str:
        try:
            completed = subprocess.run(
                ["docker", "--version"],
                check=True,
                capture_output=True,
                text=True,
            )
            return (completed.stdout or completed.stderr or "").strip()
        except Exception:
            return ""

    def _inspect_container_state(self, container_id: Optional[str]) -> dict[str, Any]:
        if container_id is None:
            return {}
        try:
            completed = subprocess.run(
                ["docker", "inspect", container_id, "--format", "{{json .State}}"],
                check=True,
                capture_output=True,
                text=True,
            )
            return json.loads((completed.stdout or "").strip() or "{}")
        except Exception:
            return {}

    def _read_container_logs(self, container_id: Optional[str]) -> tuple[str, str]:
        if container_id is None:
            return "", ""
        try:
            completed = subprocess.run(
                ["docker", "logs", container_id],
                check=False,
                capture_output=True,
                text=True,
            )
            return completed.stdout or "", completed.stderr or ""
        except Exception:
            return "", ""

    def _stop_container(self, container_id: Optional[str]) -> None:
        if container_id is None:
            return
        try:
            subprocess.run(
                ["docker", "stop", "-t", "0", container_id],
                check=False,
                capture_output=True,
                text=True,
            )
        except Exception:
            return

    def _remove_container(self, container_id: Optional[str]) -> tuple[str, str]:
        if container_id is None:
            return "not_needed", ""
        try:
            subprocess.run(
                ["docker", "rm", "-f", container_id],
                check=True,
                capture_output=True,
                text=True,
            )
            return "removed", ""
        except Exception as exc:
            return "remove_failed", str(exc)

    def _parse_exit_code(self, value: str, state: dict[str, Any]) -> int:
        try:
            return int((value or "").strip())
        except ValueError:
            return int(state.get("ExitCode", 1))

    def _utcnow(self) -> str:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def _duration_seconds(self, started_at: str, finished_at: str) -> Optional[float]:
        if not started_at or not finished_at:
            return None
        started = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        finished = datetime.fromisoformat(finished_at.replace("Z", "+00:00"))
        return round((finished - started).total_seconds(), 6)


__all__ = ["BackendRuntimeMetadata", "FenicsSolver", "SolverArtifacts", "SolverRunMetadata"]
