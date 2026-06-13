from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Dict

from .models import SimulationSpec
from .solver import SolverArtifacts
from .utils import AnalyticalEstimator


@dataclass
class MetricsCollectionResult:
    metrics: Dict[str, float]
    source: str
    fallback_used: bool = False
    warnings: list[str] = field(default_factory=list)


class ResultPostProcessor:
    """Loads solver outputs (metrics, fields) with safe fallbacks."""

    def collect_metrics(self, spec: SimulationSpec, artifacts: SolverArtifacts) -> MetricsCollectionResult:
        metrics_path = artifacts.metrics_path
        if metrics_path.exists():
            with open(metrics_path, "r", encoding="utf-8") as fh:
                return MetricsCollectionResult(
                    metrics=json.load(fh),
                    source="solver_artifact",
                )
        return MetricsCollectionResult(
            metrics=AnalyticalEstimator.estimate(spec),
            source="analytical_fallback",
            fallback_used=True,
            warnings=["Metrics artifact missing; analytical fallback estimate used."],
        )


__all__ = ["MetricsCollectionResult", "ResultPostProcessor"]
