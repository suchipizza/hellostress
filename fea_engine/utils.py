from __future__ import annotations

from typing import Dict

from .models import DEFAULT_MATERIALS, GeometryType, LoadType, SimulationSpec


class AnalyticalEstimator:
    """Provides quick closed-form estimates for basic beam and plate cases."""

    # Source for clamped rectangular plate coefficients:
    # Timoshenko and Woinowsky-Krieger, Theory of Plates and Shells, Table 35 (nu = 0.3)
    _CLAMPED_PLATE_TABLE = [
        (1.0, 0.00126, 0.0513, 0.0513, 0.0231, 0.0231),
        (1.1, 0.00150, 0.0581, 0.0538, 0.0264, 0.0231),
        (1.2, 0.00172, 0.0639, 0.0554, 0.0299, 0.0228),
        (1.3, 0.00191, 0.0687, 0.0563, 0.0327, 0.0222),
        (1.4, 0.00207, 0.0726, 0.0568, 0.0349, 0.0212),
        (1.5, 0.00220, 0.0757, 0.0570, 0.0368, 0.0203),
        (1.6, 0.00230, 0.0780, 0.0571, 0.0381, 0.0193),
        (1.7, 0.00238, 0.0799, 0.0571, 0.0392, 0.0182),
        (1.8, 0.00245, 0.0812, 0.0571, 0.0401, 0.0174),
        (1.9, 0.00249, 0.0822, 0.0571, 0.0407, 0.0165),
        (2.0, 0.00254, 0.0829, 0.0571, 0.0412, 0.0158),
    ]

    @staticmethod
    def estimate(spec: SimulationSpec) -> Dict[str, float]:
        if spec.geometry == GeometryType.BEAM:
            return AnalyticalEstimator._estimate_beam(spec)
        if spec.geometry == GeometryType.PLATE:
            return AnalyticalEstimator._estimate_plate(spec)
        if spec.geometry == GeometryType.BRACKET:
            return AnalyticalEstimator._estimate_bracket(spec)
        return AnalyticalEstimator._estimate_plate_with_hole(spec)

    @staticmethod
    def _estimate_beam(spec: SimulationSpec) -> Dict[str, float]:
        material = spec.material or DEFAULT_MATERIALS["steel"]
        load = spec.loads[0]
        length = spec.length
        if spec.beam_section is None:
            raise ValueError("Beam simulations require beam_section dimensions.")

        height = spec.beam_section.height
        width = spec.beam_section.width
        inertia = width * height**3 / 12.0
        E = material.youngs_modulus
        force = load.magnitude

        if load.load_type == LoadType.DISTRIBUTED:
            line_load = force / max(length, 1e-9)
            if spec.boundary_condition == "roller":
                deflection = 5.0 * line_load * length**4 / (384.0 * E * inertia)
                max_moment = line_load * length**2 / 8.0
            else:
                deflection = line_load * length**4 / (8.0 * E * inertia)
                max_moment = line_load * length**2 / 2.0
        else:
            location = (load.location if load.location is not None else 1.0) * length
            location = max(0.0, min(length, location))
            if spec.boundary_condition == "roller":
                remaining = length - location
                deflection = force * location**2 * remaining**2 / (3.0 * length * E * inertia)
                max_moment = force * location * remaining / max(length, 1e-9)
            else:
                deflection = force * location**2 * (3.0 * length - location) / (6.0 * E * inertia)
                max_moment = force * location

        max_stress = max_moment * (height / 2.0) / inertia
        return {
            "max_deflection": float(max(deflection, 0.0)),
            "max_stress": float(max(max_stress, 0.0)),
        }

    @staticmethod
    def _estimate_plate(spec: SimulationSpec) -> Dict[str, float]:
        material = spec.material or DEFAULT_MATERIALS["steel"]
        load = spec.loads[0]
        if spec.plate_dimensions is None:
            raise ValueError("Plate simulations require plate dimensions.")
        if load.load_type != LoadType.PRESSURE:
            raise ValueError("Plate analytical estimates require a pressure load.")

        short_span = min(spec.length, spec.plate_dimensions.width)
        long_span = max(spec.length, spec.plate_dimensions.width)
        thickness = spec.plate_dimensions.thickness
        aspect_ratio = long_span / max(short_span, 1e-9)
        pressure = load.magnitude
        rigidity = (
            material.youngs_modulus
            * thickness**3
            / (12.0 * (1.0 - material.poisson_ratio**2))
        )

        if spec.boundary_condition == "fixed":
            (
                deflection_coeff,
                mx_center_coeff,
                my_mid_edge_coeff,
                mx_corner_coeff,
                my_corner_coeff,
            ) = AnalyticalEstimator._interpolate_clamped_plate_coefficients(aspect_ratio)
            deflection = deflection_coeff * pressure * short_span**4 / rigidity
            max_moment_coeff = max(
                abs(mx_center_coeff),
                abs(my_mid_edge_coeff),
                abs(mx_corner_coeff),
                abs(my_corner_coeff),
            )
            max_stress = 6.0 * max_moment_coeff * pressure * short_span**2 / (thickness**2)
        else:
            # Preserve a lightweight simply supported estimate for non-benchmark workflows.
            q = pressure
            deflection = 0.00406 * q * short_span**4 / rigidity
            max_stress = 0.2874 * q * short_span**2 / (thickness**2)

        return {
            "max_deflection": float(max(deflection, 0.0)),
            "max_stress": float(max(max_stress, 0.0)),
        }

    @staticmethod
    def _estimate_bracket(spec: SimulationSpec) -> Dict[str, float]:
        if spec.beam_section is None:
            raise ValueError("Bracket analytical estimates require thickness and width dimensions.")
        material = spec.material or DEFAULT_MATERIALS["steel"]
        load = spec.loads[0]
        thickness = spec.beam_section.height
        width = spec.beam_section.width
        length = spec.length
        inertia = width * thickness**3 / 12.0
        force = load.magnitude
        deflection = force * length**3 / (3.0 * material.youngs_modulus * inertia)
        max_stress = force * length * (thickness / 2.0) / inertia
        return {
            "max_deflection": float(max(deflection, 0.0)),
            "max_stress": float(max(max_stress, 0.0)),
        }

    @staticmethod
    def _estimate_plate_with_hole(spec: SimulationSpec) -> Dict[str, float]:
        if spec.plate_dimensions is None:
            raise ValueError("Plate-with-hole analytical estimates require plate dimensions.")
        material = spec.material or DEFAULT_MATERIALS["steel"]
        load = spec.loads[0]
        hole_diameter = float(spec.metadata.get("hole_diameter_m", 0.0))
        if hole_diameter <= 0.0:
            raise ValueError("Plate-with-hole analytical estimates require a positive hole diameter.")
        nominal_stress = load.magnitude
        # Wide-plate Kirsch screening: peak stress near the hole edge is about 3x the far-field tension.
        stress_concentration_factor = 3.0
        max_stress = stress_concentration_factor * nominal_stress
        axial_strain = nominal_stress / material.youngs_modulus
        effective_length = spec.length
        net_width = max(spec.plate_dimensions.width - hole_diameter, 1e-9)
        ligament_factor = spec.plate_dimensions.width / net_width
        deflection = axial_strain * effective_length * ligament_factor
        return {
            "max_deflection": float(max(deflection, 0.0)),
            "max_stress": float(max(max_stress, 0.0)),
        }

    @staticmethod
    def _interpolate_clamped_plate_coefficients(
        aspect_ratio: float,
    ) -> tuple[float, float, float, float, float]:
        table = AnalyticalEstimator._CLAMPED_PLATE_TABLE
        if aspect_ratio <= table[0][0]:
            return table[0][1:]
        if aspect_ratio >= table[-1][0]:
            return table[-1][1:]

        for lower, upper in zip(table, table[1:]):
            if lower[0] <= aspect_ratio <= upper[0]:
                span = upper[0] - lower[0]
                weight = (aspect_ratio - lower[0]) / span
                return tuple(
                    lower[idx] + weight * (upper[idx] - lower[idx])
                    for idx in range(1, 6)
                )

        return table[-1][1:]


__all__ = ["AnalyticalEstimator"]
