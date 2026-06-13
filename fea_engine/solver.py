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
class SolverArtifacts:
    backend_mode: str
    script_path: Path
    results_dir: Path
    metrics_path: Path
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
                    "Docker solver mode was requested, but Docker is not available on this machine."
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

        if self.mode == "docker":
            self._run_in_docker(script_path)
        else:
            self._run_mock(spec, metrics_path)

        generated_files = [path for path in sorted(results_dir.iterdir()) if path.is_file()]
        warnings: list[str] = []
        if not metrics_path.exists():
            warnings.append("Solver backend did not produce metrics.json; post-processing may fall back to estimates.")

        return SolverArtifacts(
            backend_mode=self.mode,
            script_path=script_path,
            results_dir=results_dir,
            metrics_path=metrics_path,
            generated_files=generated_files,
            warnings=warnings,
        )

    def _run_in_docker(self, script_path: Path) -> None:
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
            subprocess.run(
                cmd,
                check=True,
                timeout=self.timeout_seconds,
                capture_output=True,
                text=True,
            )
        except subprocess.TimeoutExpired as exc:
            raise SolverExecutionError(
                f"Docker solver timed out after {self.timeout_seconds} seconds."
            ) from exc
        except subprocess.CalledProcessError as exc:
            stderr = (exc.stderr or "").strip()
            detail = f" Docker stderr: {stderr}" if stderr else ""
            raise SolverExecutionError(f"Docker solver execution failed.{detail}") from exc

    def _run_mock(self, spec: SimulationSpec, metrics_path: Path) -> None:
        metrics = AnalyticalEstimator.estimate(spec)
        metrics_path.parent.mkdir(exist_ok=True)
        with open(metrics_path, "w", encoding="utf-8") as fh:
            json.dump(metrics, fh)


__all__ = ["FenicsSolver", "SolverArtifacts"]
