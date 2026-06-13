from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .models import SimulationSpec


def spec_to_display_dict(spec: SimulationSpec) -> dict[str, Any]:
    """Serialize a simulation spec into UI-safe primitive values."""

    data = asdict(spec)
    data["geometry"] = spec.geometry.value
    for load in data["loads"]:
        load["load_type"] = load["load_type"].value
    if spec.material:
        data["material"]["name"] = spec.material.name
    return data


__all__ = ["spec_to_display_dict"]
