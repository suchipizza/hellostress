"""Core FEA Copilot engine modules."""

from .artifacts import (
    ARTIFACT_SCHEMA_VERSION,
    ArtifactBundle,
    MAX_SUPPORTED_ARTIFACT_SCHEMA_VERSION,
    MIN_SUPPORTED_ARTIFACT_SCHEMA_VERSION,
    build_bundle_summary,
    load_artifact_bundle,
)
from .errors import (
    ArtifactValidationError,
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
    "ARTIFACT_SCHEMA_VERSION",
    "ArtifactBundle",
    "ArtifactValidationError",
    "BackendRuntimeMetadata",
    "MAX_SUPPORTED_ARTIFACT_SCHEMA_VERSION",
    "MIN_SUPPORTED_ARTIFACT_SCHEMA_VERSION",
    "build_bundle_summary",
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
    "load_artifact_bundle",
    "ResultSummarizer",
    "spec_to_display_dict",
    "SimulationSpecValidator",
    "SpecValidationError",
    "UnsupportedSolverModeError",
]
