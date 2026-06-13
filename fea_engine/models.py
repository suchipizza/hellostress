from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class GeometryType(str, Enum):
    BEAM = "beam"
    PLATE = "plate"


class LoadType(str, Enum):
    POINT = "point"
    DISTRIBUTED = "distributed"
    PRESSURE = "pressure"


@dataclass
class LoadCase:
    load_type: LoadType
    magnitude: float  # Magnitude in SI units (N or Pa)
    direction: str = "-y"
    location: Optional[float] = None  # relative (0-1) for beam loads
    description: str = ""
    units: str = "N"


@dataclass
class MaterialSpec:
    name: str
    youngs_modulus: float  # Pascals
    poisson_ratio: float
    density: Optional[float] = None
    yield_strength: Optional[float] = None


@dataclass
class BeamSection:
    height: float  # meters
    width: float  # meters


@dataclass
class PlateDimensions:
    width: float  # meters
    thickness: float  # meters


@dataclass
class SimulationSpec:
    prompt: str
    geometry: GeometryType
    length: float  # meters
    beam_section: Optional[BeamSection] = None
    plate_dimensions: Optional[PlateDimensions] = None
    mesh_density: int = 32
    boundary_condition: str = "fixed"
    loads: List[LoadCase] = field(default_factory=list)
    material: Optional[MaterialSpec] = None
    units: str = "SI"
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def beam_height(self) -> Optional[float]:
        return self.beam_section.height if self.beam_section else None

    @property
    def beam_width(self) -> Optional[float]:
        return self.beam_section.width if self.beam_section else None

    @property
    def plate_width(self) -> Optional[float]:
        return self.plate_dimensions.width if self.plate_dimensions else None

    @property
    def plate_thickness(self) -> Optional[float]:
        return self.plate_dimensions.thickness if self.plate_dimensions else None


@dataclass
class SimulationResult:
    spec: SimulationSpec
    script_path: Optional[Path]
    results_dir: Optional[Path]
    max_deflection: Optional[float]
    max_stress: Optional[float]
    figure_json: Optional[str]
    summary: Optional[str]
    warnings: List[str] = field(default_factory=list)


DEFAULT_MATERIALS: Dict[str, MaterialSpec] = {
    "steel": MaterialSpec(
        name="Steel",
        youngs_modulus=200e9,
        poisson_ratio=0.3,
        density=7850,
        yield_strength=250e6,
    ),
    "aluminum": MaterialSpec(
        name="Aluminum",
        youngs_modulus=70e9,
        poisson_ratio=0.33,
        density=2700,
        yield_strength=150e6,
    ),
    "titanium": MaterialSpec(
        name="Titanium",
        youngs_modulus=116e9,
        poisson_ratio=0.34,
        density=4500,
        yield_strength=830e6,
    ),
}
