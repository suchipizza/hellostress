from __future__ import annotations

from typing import Dict

from jinja2 import Environment, BaseLoader

from templates import BEAM_TEMPLATE, PLATE_TEMPLATE
from .models import GeometryType, LoadType, SimulationSpec


class FenicsScriptGenerator:
    """Renders a FEniCS Python script based on the simulation spec."""

    def __init__(self) -> None:
        self.env = Environment(loader=BaseLoader(), trim_blocks=True, lstrip_blocks=True)
        self.templates: Dict[GeometryType, str] = {
            GeometryType.BEAM: BEAM_TEMPLATE,
            GeometryType.PLATE: PLATE_TEMPLATE,
        }

    def render(self, spec: SimulationSpec) -> str:
        template_str = self.templates[spec.geometry]
        template = self.env.from_string(template_str)
        material = spec.material
        if material is None:
            raise ValueError("SimulationSpec.material must be provided before rendering")

        mesh_nx = max(8, int(spec.mesh_density))
        mesh_ny = max(4, int(spec.mesh_density // 2))
        load = spec.loads[0]
        width = spec.width or spec.height or 0.1
        thickness = spec.thickness or spec.height or 0.1
        cross_section = width * thickness
        volume = spec.length * cross_section
        body_force = load.magnitude / max(volume, 1e-6)
        surface_pressure = load.magnitude
        if load.load_type == LoadType.PRESSURE:
            body_force = load.magnitude / max(thickness, 1e-6)
            surface_pressure = load.magnitude
        else:
            surface_pressure = load.magnitude / max(cross_section, 1e-6)

        context = {
            "length": spec.length,
            "height": spec.height,
            "width": spec.width or spec.height,
            "mesh_nx": mesh_nx,
            "mesh_ny": mesh_ny,
            "youngs_modulus": material.youngs_modulus,
            "poisson_ratio": material.poisson_ratio,
            "load_density": body_force,
            "pressure": surface_pressure,
        }
        return template.render(**context)


__all__ = ["FenicsScriptGenerator"]
