from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .models import SimulationSpec
from .utils import AnalyticalEstimator


@dataclass
class SolverArtifacts:
    script_path: Path
    results_dir: Path


class FenicsSolver:
    """Executes generated FEniCS scripts via Docker, local Python, or mock mode."""

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
        if requested != "auto":
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

        if self.mode == "docker":
            self._run_in_docker(script_path)
        elif self.mode == "local":
            self._run_locally(script_path)
        else:
            self._run_mock(spec, results_dir)

        return SolverArtifacts(script_path=script_path, results_dir=results_dir)

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
        subprocess.run(cmd, check=True, timeout=self.timeout_seconds)

    def _run_locally(self, script_path: Path) -> None:
        subprocess.run([
            "python3",
            str(script_path),
        ], check=True, timeout=self.timeout_seconds)

    def _run_mock(self, spec: SimulationSpec, results_dir: Path) -> None:
        metrics = AnalyticalEstimator.estimate(spec)
        results_dir.mkdir(exist_ok=True)
        with open(results_dir / "metrics.json", "w", encoding="utf-8") as fh:
            json.dump(metrics, fh)


__all__ = ["FenicsSolver", "SolverArtifacts"]
