from __future__ import annotations

import pytest

from fea_engine import BeamSection, LoadCase, PlateDimensions, SimulationSpec, SimulationSpecValidator, SpecValidationError
from fea_engine.models import DEFAULT_MATERIALS, GeometryType, LoadType


def test_validator_accepts_supported_beam_spec(sample_beam_spec) -> None:
    validated = SimulationSpecValidator().validate(sample_beam_spec)

    assert validated is sample_beam_spec


def test_validator_rejects_missing_beam_section() -> None:
    spec = SimulationSpec(
        prompt="beam",
        geometry=GeometryType.BEAM,
        length=1.0,
        boundary_condition="fixed",
        loads=[LoadCase(load_type=LoadType.POINT, magnitude=100.0, units="N")],
        material=DEFAULT_MATERIALS["steel"],
    )

    with pytest.raises(SpecValidationError):
        SimulationSpecValidator().validate(spec)


def test_validator_rejects_plate_point_load() -> None:
    spec = SimulationSpec(
        prompt="plate",
        geometry=GeometryType.PLATE,
        length=0.5,
        plate_dimensions=PlateDimensions(width=0.3, thickness=0.005),
        boundary_condition="fixed",
        loads=[LoadCase(load_type=LoadType.POINT, magnitude=100.0, units="N")],
        material=DEFAULT_MATERIALS["aluminum"],
    )

    with pytest.raises(SpecValidationError):
        SimulationSpecValidator().validate(spec)


def test_validator_rejects_mesh_density_out_of_range(sample_beam_spec) -> None:
    sample_beam_spec.mesh_density = 4

    with pytest.raises(SpecValidationError):
        SimulationSpecValidator().validate(sample_beam_spec)


def test_validator_rejects_out_of_bounds_load_location(sample_beam_spec) -> None:
    sample_beam_spec.loads[0].location = 1.5

    with pytest.raises(SpecValidationError):
        SimulationSpecValidator().validate(sample_beam_spec)


def test_validator_rejects_invalid_boundary_condition(sample_beam_spec) -> None:
    sample_beam_spec.boundary_condition = "pinned"

    with pytest.raises(SpecValidationError):
        SimulationSpecValidator().validate(sample_beam_spec)
