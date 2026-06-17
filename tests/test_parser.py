from __future__ import annotations

import pytest

from fea_engine import PromptParseError, SpecValidationError
from fea_engine.models import GeometryType, LoadType


def test_beam_prompt_parses_expected_dimensions(parser) -> None:
    spec = parser.parse(
        "Simulate a 1 m long, 0.1 m thick steel cantilever beam with a 150 N downward tip load."
    )

    assert spec.geometry == GeometryType.BEAM
    assert spec.length == pytest.approx(1.0)
    assert spec.beam_section is not None
    assert spec.beam_section.height == pytest.approx(0.1)
    assert spec.beam_section.width == pytest.approx(0.1)
    assert spec.loads[0].magnitude == pytest.approx(150.0)
    assert spec.loads[0].load_type == LoadType.POINT
    assert spec.loads[0].location == pytest.approx(1.0)


def test_plate_prompt_parses_expected_dimensions(parser) -> None:
    spec = parser.parse(
        "Analyze a 0.5 m by 0.3 m aluminum plate 5 mm thick under a uniform pressure of 50 kPa."
    )

    assert spec.geometry == GeometryType.PLATE
    assert spec.length == pytest.approx(0.5)
    assert spec.plate_dimensions is not None
    assert spec.plate_dimensions.width == pytest.approx(0.3)
    assert spec.plate_dimensions.thickness == pytest.approx(0.005)
    assert spec.loads[0].magnitude == pytest.approx(50000.0)
    assert spec.loads[0].units == "Pa"


def test_beam_width_defaults_to_section_height(parser) -> None:
    spec = parser.parse("Analyze a 2 m long steel beam 50 mm thick with a 2 kN downward tip load.")

    assert spec.beam_section is not None
    assert spec.beam_section.width == pytest.approx(spec.beam_section.height)


def test_explicit_beam_width_is_preserved(parser) -> None:
    spec = parser.parse(
        "Analyze a 2 m long steel beam 50 mm thick and 80 mm wide with a 2 kN downward tip load."
    )

    assert spec.beam_section is not None
    assert spec.beam_section.height == pytest.approx(0.05)
    assert spec.beam_section.width == pytest.approx(0.08)


def test_kn_force_converts_to_newtons(parser) -> None:
    spec = parser.parse("Analyze a 2 m long steel beam 50 mm thick with a 2 kN downward tip load.")

    assert spec.loads[0].magnitude == pytest.approx(2000.0)
    assert spec.loads[0].units == "N"


def test_pressure_units_convert_to_pascals(parser) -> None:
    spec = parser.parse("Analyze a 0.5 m by 0.3 m aluminum plate 5 mm thick under 1.2 MPa pressure.")

    assert spec.loads[0].magnitude == pytest.approx(1_200_000.0)
    assert spec.loads[0].load_type == LoadType.PRESSURE
    assert spec.loads[0].units == "Pa"


def test_simply_supported_boundary_maps_to_roller(parser) -> None:
    spec = parser.parse(
        "Analyze a simply supported 1 m by 0.4 m aluminum plate 10 mm thick under 25 kPa pressure."
    )

    assert spec.boundary_condition == "roller"


def test_midspan_location_maps_to_half_span(parser) -> None:
    spec = parser.parse("Analyze a 2 m long steel beam 50 mm thick with a 300 N downward midspan load.")

    assert spec.loads[0].location == pytest.approx(0.5)


def test_requires_geometry_keyword(parser) -> None:
    with pytest.raises(PromptParseError):
        parser.parse("Analyze a 2 m long steel cantilever with a 300 N downward tip load.")


def test_requires_load_with_units(parser) -> None:
    with pytest.raises(PromptParseError):
        parser.parse("Analyze a 2 m long steel beam 50 mm thick.")


def test_rejects_unsupported_plate_point_load(parser) -> None:
    with pytest.raises(SpecValidationError):
        parser.parse("Analyze a 0.5 m by 0.3 m aluminum plate 5 mm thick with a 100 N downward point load.")


def test_bracket_prompt_parses_screening_dimensions(parser) -> None:
    spec = parser.parse(
        "Analyze a steel L-bracket with a 120 mm arm, 40 mm wide and 10 mm thick, fixed at the base with a 2 kN downward load at the free hole."
    )

    assert spec.geometry == GeometryType.BRACKET
    assert spec.length == pytest.approx(0.12)
    assert spec.beam_section is not None
    assert spec.beam_section.height == pytest.approx(0.01)
    assert spec.beam_section.width == pytest.approx(0.04)
    assert spec.loads[0].magnitude == pytest.approx(2000.0)
    assert spec.loads[0].location == pytest.approx(1.0)
    assert spec.metadata["analysis_mode"] == "analytical_screening"


def test_plate_with_hole_prompt_parses_screening_dimensions(parser) -> None:
    spec = parser.parse(
        "Analyze a 0.4 m by 0.2 m aluminum plate 8 mm thick with a 40 mm central hole under 40 MPa axial tension."
    )

    assert spec.geometry == GeometryType.PLATE_WITH_HOLE
    assert spec.length == pytest.approx(0.4)
    assert spec.plate_dimensions is not None
    assert spec.plate_dimensions.width == pytest.approx(0.2)
    assert spec.plate_dimensions.thickness == pytest.approx(0.008)
    assert spec.loads[0].magnitude == pytest.approx(40_000_000.0)
    assert spec.loads[0].direction == "+x"
    assert spec.metadata["hole_diameter_m"] == pytest.approx(0.04)
