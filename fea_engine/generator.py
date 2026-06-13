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
        context = {
            "length": spec.length,
            "mesh_nx": mesh_nx,
            "mesh_ny": mesh_ny,
            "youngs_modulus": material.youngs_modulus,
            "poisson_ratio": material.poisson_ratio,
        }

        if spec.geometry == GeometryType.BEAM:
            if spec.beam_section is None:
                raise ValueError("Beam simulations require beam_section dimensions.")
            section = spec.beam_section
            cross_section = section.width * section.height
            volume = spec.length * cross_section
            context.update(
                {
                    "height": section.height,
                    "width": section.width,
                    "load_density": load.magnitude / max(volume, 1e-6),
                    "pressure": load.magnitude / max(cross_section, 1e-6),
                }
            )
        else:
            if spec.plate_dimensions is None:
                raise ValueError("Plate simulations require plate dimensions.")
            plate = spec.plate_dimensions
            body_force = load.magnitude
            if load.load_type == LoadType.PRESSURE:
                body_force = load.magnitude / max(plate.thickness, 1e-6)
            context.update(
                {
                    "width": plate.width,
                    "pressure": load.magnitude,
                    "load_density": body_force,
                }
            )
        return template.render(**context)


__all__ = ["FenicsScriptGenerator"]
