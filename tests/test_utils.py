from __future__ import annotations

import pytest

from fea_engine.models import DEFAULT_MATERIALS, BeamSection, GeometryType, LoadCase, LoadType, PlateDimensions, SimulationSpec
from fea_engine.utils import AnalyticalEstimator


def test_beam_estimator_supports_simply_supported_midspan_point_load() -> None:
    spec = SimulationSpec(
        prompt="simply supported beam",
        geometry=GeometryType.BEAM,
        length=2.0,
        beam_section=BeamSection(height=0.05, width=0.08),
        boundary_condition="roller",
        loads=[
            LoadCase(
                load_type=LoadType.POINT,
                magnitude=2000.0,
                direction="-y",
                location=0.5,
                units="N",
            )
        ],
        material=DEFAULT_MATERIALS["steel"],
    )

    metrics = AnalyticalEstimator.estimate(spec)

    assert metrics["max_deflection"] == pytest.approx(0.002, rel=1e-6)
    assert metrics["max_stress"] == pytest.approx(30000000.0, rel=1e-6)


def test_plate_estimator_uses_clamped_plate_reference_coefficients() -> None:
    spec = SimulationSpec(
        prompt="clamped plate",
        geometry=GeometryType.PLATE,
        length=0.5,
        plate_dimensions=PlateDimensions(width=0.5, thickness=0.005),
        boundary_condition="fixed",
        loads=[
            LoadCase(
                load_type=LoadType.PRESSURE,
                magnitude=50000.0,
                direction="-z",
                units="Pa",
            )
        ],
        material=DEFAULT_MATERIALS["steel"],
    )

    metrics = AnalyticalEstimator.estimate(spec)

    assert metrics["max_deflection"] == pytest.approx(0.0017199, rel=1e-4)
    assert metrics["max_stress"] == pytest.approx(153900000.0, rel=1e-4)


def test_bracket_estimator_uses_cantilever_strip_screening() -> None:
    spec = SimulationSpec(
        prompt="bracket",
        geometry=GeometryType.BRACKET,
        length=0.12,
        beam_section=BeamSection(height=0.01, width=0.04),
        boundary_condition="fixed",
        loads=[LoadCase(load_type=LoadType.POINT, magnitude=2000.0, direction="-y", units="N")],
        material=DEFAULT_MATERIALS["steel"],
    )

    metrics = AnalyticalEstimator.estimate(spec)

    assert metrics["max_deflection"] == pytest.approx(0.001728, rel=1e-6)
    assert metrics["max_stress"] == pytest.approx(360000000.0, rel=1e-6)


def test_plate_with_hole_estimator_uses_kirsch_style_screening() -> None:
    spec = SimulationSpec(
        prompt="plate with hole",
        geometry=GeometryType.PLATE_WITH_HOLE,
        length=0.4,
        plate_dimensions=PlateDimensions(width=0.2, thickness=0.008),
        boundary_condition="fixed",
        loads=[LoadCase(load_type=LoadType.PRESSURE, magnitude=40_000_000.0, direction="+x", units="Pa")],
        material=DEFAULT_MATERIALS["aluminum"],
        metadata={"hole_diameter_m": 0.04},
    )

    metrics = AnalyticalEstimator.estimate(spec)

    assert metrics["max_deflection"] == pytest.approx(0.0002857142857, rel=1e-6)
    assert metrics["max_stress"] == pytest.approx(120000000.0, rel=1e-6)
