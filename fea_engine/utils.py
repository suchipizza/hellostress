from __future__ import annotations

from typing import Dict

from .models import DEFAULT_MATERIALS, GeometryType, SimulationSpec


class AnalyticalEstimator:
    """Provides quick closed-form estimates for basic beam/plate cases."""

    @staticmethod
    def estimate(spec: SimulationSpec) -> Dict[str, float]:
        material = spec.material or DEFAULT_MATERIALS["steel"]
        load = spec.loads[0]
        length = spec.length
        height = spec.height
        width = spec.width or height
        thickness = spec.thickness or height

        if spec.geometry == GeometryType.BEAM:
            inertia = width * height**3 / 12.0
            E = material.youngs_modulus
            force = load.magnitude
            deflection = force * length**3 / (3 * E * inertia)
            max_stress = force * length * (height / 2.0) / inertia
        else:
            # Simplified small-deflection clamped rectangular plate under uniform load
            q = load.magnitude / (length * width)
            D = material.youngs_modulus * thickness**3 / (12 * (1 - material.poisson_ratio**2))
            deflection = (q * length**4) / (100 * D)
            max_stress = q * length**2 / thickness

        return {
            "max_deflection": float(max(deflection, 0.0)),
            "max_stress": float(max(max_stress, 0.0)),
        }


__all__ = ["AnalyticalEstimator"]
