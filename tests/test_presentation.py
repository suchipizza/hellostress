from __future__ import annotations

from fea_engine import BeamSection, LoadCase, SimulationSpec, spec_to_display_dict
from fea_engine.models import DEFAULT_MATERIALS, GeometryType, LoadType


def test_spec_to_display_dict_serializes_enums_for_ui() -> None:
    spec = SimulationSpec(
        prompt="beam fixture",
        geometry=GeometryType.BEAM,
        length=1.0,
        beam_section=BeamSection(height=0.1, width=0.1),
        boundary_condition="fixed",
        loads=[
            LoadCase(
                load_type=LoadType.POINT,
                magnitude=150.0,
                direction="-y",
                location=1.0,
                units="N",
            )
        ],
        material=DEFAULT_MATERIALS["steel"],
    )

    payload = spec_to_display_dict(spec)

    assert payload["geometry"] == "beam"
    assert payload["loads"][0]["load_type"] == "point"
    assert payload["material"]["name"] == "Steel"
