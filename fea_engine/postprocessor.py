from __future__ import annotations

import json
from typing import Dict

from .models import SimulationSpec
from .solver import SolverArtifacts
from .utils import AnalyticalEstimator


class ResultPostProcessor:
    """Loads solver outputs (metrics, fields) with safe fallbacks."""

    def collect_metrics(self, spec: SimulationSpec, artifacts: SolverArtifacts) -> Dict[str, float]:
        metrics_path = artifacts.results_dir / "metrics.json"
        if metrics_path.exists():
            with open(metrics_path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        return AnalyticalEstimator.estimate(spec)


__all__ = ["ResultPostProcessor"]
