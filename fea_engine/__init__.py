"""Core FEA Copilot engine modules."""

from .errors import FEACopilotError, PromptParseError, SpecValidationError
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
from .solver import FenicsSolver
from .postprocessor import ResultPostProcessor
from .visualizer import SimulationVisualizer
from .summarizer import ResultSummarizer
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
    "PlateDimensions",
    "PromptParseError",
    "PromptParser",
    "FenicsScriptGenerator",
    "FenicsSolver",
    "ResultPostProcessor",
    "SimulationVisualizer",
    "ResultSummarizer",
    "SimulationSpecValidator",
    "SpecValidationError",
]
