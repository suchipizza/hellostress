from __future__ import annotations

from typing import Dict

from jinja2 import Environment, BaseLoader

from templates import BEAM_TEMPLATE, BRACKET_TEMPLATE, PLATE_TEMPLATE, PLATE_WITH_HOLE_TEMPLATE
from .models import GeometryType, LoadType, SimulationSpec


class FenicsScriptGenerator:
    """Renders a FEniCS Python script based on the simulation spec."""

    def __init__(self) -> None:
        self.env = Environment(loader=BaseLoader(), trim_blocks=True, lstrip_blocks=True)
        self.templates: Dict[GeometryType, str] = {
            GeometryType.BEAM: BEAM_TEMPLATE,
            GeometryType.PLATE: PLATE_TEMPLATE,
            GeometryType.BRACKET: BRACKET_TEMPLATE,
            GeometryType.PLATE_WITH_HOLE: PLATE_WITH_HOLE_TEMPLATE,
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
        load_x, load_y = self._direction_components(load.direction)
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
            beam_load_mode = "body_force"
            traction_x = 0.0
            traction_y = 0.0
            if load.load_type == LoadType.POINT and (load.location is None or load.location >= 0.999):
                beam_load_mode = "end_traction"
                traction_scale = load.magnitude / max(section.height, 1e-6)
                traction_x = load_x * traction_scale
                traction_y = load_y * traction_scale
            context.update(
                {
                    "height": section.height,
                    "width": section.width,
                    "beam_load_mode": beam_load_mode,
                    "body_force_x": load_x * (load.magnitude / max(volume, 1e-6)),
                    "body_force_y": load_y * (load.magnitude / max(volume, 1e-6)),
                    "traction_x": traction_x,
                    "traction_y": traction_y,
                }
            )
        elif spec.geometry == GeometryType.PLATE:
            if spec.plate_dimensions is None:
                raise ValueError("Plate simulations require plate dimensions.")
            plate = spec.plate_dimensions
            body_force = load.magnitude
            if load.load_type == LoadType.PRESSURE:
                body_force = load.magnitude / max(plate.thickness, 1e-6)
            context.update(
                {
                    "width": plate.width,
                    "body_force_x": load_x * body_force,
                    "body_force_y": load_y * body_force,
                }
            )
        elif spec.geometry == GeometryType.BRACKET:
            if spec.beam_section is None:
                raise ValueError("Bracket workflows require thickness and width dimensions.")
            context.update(
                {
                    "height": spec.beam_section.height,
                    "width": spec.beam_section.width,
                }
            )
        else:
            if spec.plate_dimensions is None:
                raise ValueError("Plate-with-hole workflows require plate dimensions.")
            context.update(
                {
                    "width": spec.plate_dimensions.width,
                    "hole_diameter": spec.metadata.get("hole_diameter_m", 0.0),
                }
            )
        return template.render(**context)

    def _direction_components(self, direction: str) -> tuple[float, float]:
        normalized = (direction or "").strip().lower()
        mapping = {
            "+x": (1.0, 0.0),
            "-x": (-1.0, 0.0),
            "+y": (0.0, 1.0),
            "-y": (0.0, -1.0),
            "+z": (0.0, 1.0),
            "-z": (0.0, -1.0),
        }
        return mapping.get(normalized, (0.0, -1.0))


__all__ = ["FenicsScriptGenerator"]
