from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

import plotly.graph_objects as go

from .generator import FenicsScriptGenerator
from .models import SimulationSpec
from .parser import PromptParser
from .postprocessor import ResultPostProcessor
from .solver import FenicsSolver, SolverArtifacts
from .summarizer import ResultSummarizer
from .visualizer import SimulationVisualizer


ProgressCallback = Callable[[str], None]
SolverFactory = Callable[[str], FenicsSolver]


@dataclass
class SimulationRunResult:
    spec: SimulationSpec
    script: str
    artifacts: SolverArtifacts
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
        artifacts = solver.run(spec, script)

        self._emit(progress_callback, "Post-processing results…")
        metrics = self.postprocessor.collect_metrics(spec, artifacts)
        figure = self.visualizer.build_figure(spec, metrics)
        summary = self.summarizer.summarize(spec, metrics)

        return SimulationRunResult(
            spec=spec,
            script=script,
            artifacts=artifacts,
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


__all__ = ["SimulationRunResult", "SimulationService"]
