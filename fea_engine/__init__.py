"""Core FEA Copilot engine modules."""

from .models import SimulationSpec, SimulationResult, LoadCase, MaterialSpec
from .parser import PromptParser
from .generator import FenicsScriptGenerator
from .solver import FenicsSolver
from .postprocessor import ResultPostProcessor
from .visualizer import SimulationVisualizer
from .summarizer import ResultSummarizer

__all__ = [
    "SimulationSpec",
    "SimulationResult",
    "LoadCase",
    "MaterialSpec",
    "PromptParser",
    "FenicsScriptGenerator",
    "FenicsSolver",
    "ResultPostProcessor",
    "SimulationVisualizer",
    "ResultSummarizer",
]
