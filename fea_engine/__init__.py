"""Core FEA Copilot engine modules."""

from .errors import (
    FEACopilotError,
    PromptParseError,
    SimulationRunError,
    SolverExecutionError,
    SpecValidationError,
    UnsupportedSolverModeError,
)
from .models import (
    BeamSection,
    GeometryType,
    LoadCase,
    LoadType,
    MaterialSpec,
    PlateDimensions,
    SimulationResult,
    SimulationSpec,
)
from .parser import PromptParser
from .generator import FenicsScriptGenerator
from .solver import FenicsSolver, SolverRunMetadata
from .postprocessor import MetricsCollectionResult, ResultPostProcessor
from .visualizer import SimulationVisualizer
from .summarizer import ResultSummarizer
from .service import SimulationRunResult, SimulationService
from .validation import SimulationSpecValidator

__all__ = [
    "BeamSection",
    "FEACopilotError",
    "GeometryType",
    "SimulationSpec",
    "SimulationResult",
    "LoadCase",
    "LoadType",
    "MaterialSpec",
    "MetricsCollectionResult",
    "PlateDimensions",
    "PromptParseError",
    "PromptParser",
    "SimulationRunError",
    "SolverExecutionError",
    "FenicsScriptGenerator",
    "FenicsSolver",
    "SolverRunMetadata",
    "ResultPostProcessor",
    "SimulationRunResult",
    "SimulationService",
    "SimulationVisualizer",
    "ResultSummarizer",
    "SimulationSpecValidator",
    "SpecValidationError",
    "UnsupportedSolverModeError",
]
