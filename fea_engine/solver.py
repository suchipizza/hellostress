from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

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
class SolverArtifacts:
    run_dir: Path
    backend_mode: str
    script_path: Path
    results_dir: Path
    metrics_path: Path
    run_metadata: SolverRunMetadata
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
        stdout_path = run_path / "solver.stdout.log"
        stderr_path = run_path / "solver.stderr.log"

        if self.mode == "docker":
            run_metadata = self._run_in_docker(script_path, stdout_path, stderr_path)
        else:
            run_metadata = self._run_mock(spec, metrics_path, stdout_path, stderr_path)

        generated_files = [path for path in sorted(results_dir.iterdir()) if path.is_file()]
        warnings: list[str] = []
        if not metrics_path.exists():
            warnings.append("Solver backend did not produce metrics.json; post-processing may fall back to estimates.")

        return SolverArtifacts(
            run_dir=run_path,
            backend_mode=self.mode,
            script_path=script_path,
            results_dir=results_dir,
            metrics_path=metrics_path,
            run_metadata=run_metadata,
            generated_files=generated_files,
            warnings=warnings,
        )

    def _run_in_docker(
        self,
        script_path: Path,
        stdout_path: Path,
        stderr_path: Path,
    ) -> SolverRunMetadata:
        cmd = [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{script_path.parent}:/workspace",
            self.docker_image,
            "python3",
            "/workspace/simulation.py",
        ]
        try:
            completed = subprocess.run(
                cmd,
                check=True,
                timeout=self.timeout_seconds,
                capture_output=True,
                text=True,
            )
            return self._write_run_metadata(
                command=cmd,
                exit_code=completed.returncode,
                stdout_text=completed.stdout or "",
                stderr_text=completed.stderr or "",
                stdout_path=stdout_path,
                stderr_path=stderr_path,
            )
        except subprocess.TimeoutExpired as exc:
            metadata = self._write_run_metadata(
                command=cmd,
                exit_code=-1,
                stdout_text=self._coerce_output(exc.stdout),
                stderr_text=self._coerce_output(exc.stderr),
                stdout_path=stdout_path,
                stderr_path=stderr_path,
                timed_out=True,
            )
            raise SolverExecutionError(
                f"Docker solver timed out after {self.timeout_seconds} seconds.",
                backend_mode="docker",
                exit_code=metadata.exit_code,
                command=metadata.command,
                stdout_path=metadata.stdout_path,
                stderr_path=metadata.stderr_path,
                stdout_excerpt=metadata.stdout_excerpt,
                stderr_excerpt=metadata.stderr_excerpt,
                timed_out=metadata.timed_out,
            ) from exc
        except subprocess.CalledProcessError as exc:
            metadata = self._write_run_metadata(
                command=cmd,
                exit_code=exc.returncode,
                stdout_text=self._coerce_output(exc.stdout),
                stderr_text=self._coerce_output(exc.stderr),
                stdout_path=stdout_path,
                stderr_path=stderr_path,
            )
            raise SolverExecutionError(
                "Docker solver execution failed.",
                backend_mode="docker",
                exit_code=metadata.exit_code,
                command=metadata.command,
                stdout_path=metadata.stdout_path,
                stderr_path=metadata.stderr_path,
                stdout_excerpt=metadata.stdout_excerpt,
                stderr_excerpt=metadata.stderr_excerpt,
            ) from exc

    def _run_mock(
        self,
        spec: SimulationSpec,
        metrics_path: Path,
        stdout_path: Path,
        stderr_path: Path,
    ) -> SolverRunMetadata:
        metrics = AnalyticalEstimator.estimate(spec)
        metrics_path.parent.mkdir(exist_ok=True)
        with open(metrics_path, "w", encoding="utf-8") as fh:
            json.dump(metrics, fh)
        return self._write_run_metadata(
            command=["mock"],
            exit_code=0,
            stdout_text="Mock solver produced analytical estimate.",
            stderr_text="",
            stdout_path=stdout_path,
            stderr_path=stderr_path,
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


__all__ = ["FenicsSolver", "SolverArtifacts", "SolverRunMetadata"]
