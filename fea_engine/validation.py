from __future__ import annotations

from .errors import SpecValidationError
from .models import GeometryType, LoadType, SimulationSpec


class SimulationSpecValidator:
    """Validates that a simulation spec fits the supported MVP problem set."""

    min_mesh_density = 8
    max_mesh_density = 200
    supported_boundary_conditions = {"fixed", "roller"}

    def validate(self, spec: SimulationSpec) -> SimulationSpec:
        if not spec.prompt.strip():
            raise SpecValidationError("Prompt cannot be empty.")
        if spec.length <= 0:
            raise SpecValidationError("Length must be positive.")
        if not self.min_mesh_density <= spec.mesh_density <= self.max_mesh_density:
            raise SpecValidationError(
                f"Mesh density must be between {self.min_mesh_density} and {self.max_mesh_density}."
            )
        if spec.boundary_condition not in self.supported_boundary_conditions:
            raise SpecValidationError(
                "Boundary condition must be one of: fixed, roller."
            )
        if not spec.loads:
            raise SpecValidationError("At least one load case is required.")
        if spec.material is None:
            raise SpecValidationError("A material must be provided.")

        for load in spec.loads:
            if load.magnitude <= 0:
                raise SpecValidationError("Load magnitude must be positive.")
            if not load.direction.strip():
                raise SpecValidationError("Load direction cannot be empty.")
            if load.location is not None and not 0.0 <= load.location <= 1.0:
                raise SpecValidationError("Load location must be between 0.0 and 1.0.")

        if spec.geometry == GeometryType.BEAM:
            if spec.beam_section is None:
                raise SpecValidationError("Beam simulations require beam_section dimensions.")
            if spec.plate_dimensions is not None:
                raise SpecValidationError("Beam simulations cannot include plate dimensions.")
            if spec.beam_section.height <= 0 or spec.beam_section.width <= 0:
                raise SpecValidationError("Beam section height and width must be positive.")
            if any(load.load_type == LoadType.PRESSURE for load in spec.loads):
                raise SpecValidationError("Beam simulations do not support pressure loads.")
        else:
            if spec.plate_dimensions is None:
                raise SpecValidationError("Plate simulations require plate dimensions.")
            if spec.beam_section is not None:
                raise SpecValidationError("Plate simulations cannot include beam section dimensions.")
            if spec.plate_dimensions.width <= 0 or spec.plate_dimensions.thickness <= 0:
                raise SpecValidationError("Plate width and thickness must be positive.")
            if any(load.load_type != LoadType.PRESSURE for load in spec.loads):
                raise SpecValidationError("Plate simulations currently support pressure loads only.")

        return spec
