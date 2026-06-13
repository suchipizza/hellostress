"""Core FEA Copilot engine modules."""

from .errors import (
    ConfigurationError,
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
from .solver import BackendRuntimeMetadata, FenicsSolver, SolverRunMetadata
from .postprocessor import MetricsCollectionResult, ResultPostProcessor
from .presentation import spec_to_display_dict
from .visualizer import SimulationVisualizer
from .summarizer import ResultSummarizer
from .service import SimulationRunResult, SimulationService
from .settings import RuntimeSettings
from .validation import SimulationSpecValidator

__all__ = [
    "BeamSection",
    "BackendRuntimeMetadata",
    "ConfigurationError",
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
    "RuntimeSettings",
    "ResultSummarizer",
    "spec_to_display_dict",
    "SimulationSpecValidator",
    "SpecValidationError",
    "UnsupportedSolverModeError",
]
