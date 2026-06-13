from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Optional

import plotly.graph_objects as go

from .errors import SimulationRunError, SolverExecutionError
from .generator import FenicsScriptGenerator
from .models import SimulationSpec
from .parser import PromptParser
from .postprocessor import MetricsCollectionResult, ResultPostProcessor
from .solver import FenicsSolver, SolverArtifacts
from .summarizer import ResultSummarizer
from .visualizer import SimulationVisualizer


ProgressCallback = Callable[[str], None]
SolverFactory = Callable[[str], FenicsSolver]


@dataclass
class SimulationRunResult:
    status: str
    spec: SimulationSpec
    script: str
    artifacts: SolverArtifacts
    metrics_source: str
    fallback_used: bool
    warnings: list[str]
    result_schema_path: Path
    metrics: dict[str, float]
    figure: go.Figure
    summary: str
    solver_mode: str


class SimulationService:
    """Coordinates the end-to-end simulation pipeline outside the UI layer."""

    def __init__(
        self,
        parser: Optional[PromptParser] = None,
        generator: Optional[FenicsScriptGenerator] = None,
        postprocessor: Optional[ResultPostProcessor] = None,
        visualizer: Optional[SimulationVisualizer] = None,
        summarizer: Optional[ResultSummarizer] = None,
        solver_factory: Optional[SolverFactory] = None,
    ) -> None:
        self.parser = parser or PromptParser()
        self.generator = generator or FenicsScriptGenerator()
        self.postprocessor = postprocessor or ResultPostProcessor()
        self.visualizer = visualizer or SimulationVisualizer()
        self.summarizer = summarizer or ResultSummarizer()
        self.solver_factory = solver_factory or self._default_solver_factory

    def run_simulation(
        self,
        prompt: str,
        mesh_density: int,
        solver_mode: str,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> SimulationRunResult:
        self._emit(progress_callback, "Parsing prompt with heuristic + LLM assist…")
        spec = self.parser.parse(prompt)
        spec.mesh_density = mesh_density

        self._emit(progress_callback, "Generating FEniCS script…")
        script = self.generator.render(spec)

        self._emit(progress_callback, f"Running solver in {solver_mode} mode…")
        solver = self.solver_factory(solver_mode)
        try:
            artifacts = solver.run(spec, script)
        except SolverExecutionError as exc:
            raise SimulationRunError.from_solver_error(exc) from exc

        self._emit(progress_callback, "Post-processing results…")
        metrics_result = self.postprocessor.collect_metrics(spec, artifacts)
        metrics = metrics_result.metrics
        figure = self.visualizer.build_figure(spec, metrics)
        summary = self.summarizer.summarize(spec, metrics)
        warnings = [*artifacts.warnings, *metrics_result.warnings]
        status = "completed_with_fallback" if metrics_result.fallback_used else "completed"
        result_schema_path = self._write_result_schema(
            artifacts=artifacts,
            metrics_result=metrics_result,
            status=status,
        )

        return SimulationRunResult(
            status=status,
            spec=spec,
            script=script,
            artifacts=artifacts,
            metrics_source=metrics_result.source,
            fallback_used=metrics_result.fallback_used,
            warnings=warnings,
            result_schema_path=result_schema_path,
            metrics=metrics,
            figure=figure,
            summary=summary,
            solver_mode=artifacts.backend_mode,
        )

    def _default_solver_factory(self, solver_mode: str) -> FenicsSolver:
        return FenicsSolver(mode=solver_mode)

    def _emit(
        self,
        progress_callback: Optional[ProgressCallback],
        message: str,
    ) -> None:
        if progress_callback is not None:
            progress_callback(message)

    def _write_result_schema(
        self,
        *,
        artifacts: SolverArtifacts,
        metrics_result: MetricsCollectionResult,
        status: str,
    ) -> Path:
        result_schema_path = artifacts.run_dir / "run_result.json"
        payload = {
            "status": status,
            "backend_mode": artifacts.backend_mode,
            "backend_status": artifacts.backend_status,
            "metrics_source": metrics_result.source,
            "fallback_used": metrics_result.fallback_used,
            "warnings": [*artifacts.warnings, *metrics_result.warnings],
            "backend_status_details": self._load_json(artifacts.backend_status_path),
            "backend_metadata": self._load_json(artifacts.backend_metadata_path),
            "artifacts": {
                "run_dir": str(artifacts.run_dir),
                "script_path": str(artifacts.script_path),
                "results_dir": str(artifacts.results_dir),
                "metrics_path": str(artifacts.metrics_path),
                "backend_status_path": str(artifacts.backend_status_path),
                "backend_metadata_path": str(artifacts.backend_metadata_path),
                "generated_files": [str(path) for path in artifacts.generated_files],
            },
            "run_metadata": asdict(artifacts.run_metadata),
            "runtime_metadata": asdict(artifacts.runtime_metadata),
        }
        payload["run_metadata"]["stdout_path"] = str(artifacts.run_metadata.stdout_path)
        payload["run_metadata"]["stderr_path"] = str(artifacts.run_metadata.stderr_path)
        result_schema_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return result_schema_path

    def _load_json(self, path: Path) -> dict[str, object]:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))


__all__ = ["SimulationRunResult", "SimulationService"]
