from __future__ import annotations
import re
from typing import Dict, Optional

from .llm_client import OpenAILLMClient
from .models import DEFAULT_MATERIALS, GeometryType, LoadCase, LoadType, MaterialSpec, SimulationSpec


class PromptParser:
    """Parses natural-language prompts into structured simulation specs."""

    def __init__(self, llm_client: Optional[OpenAILLMClient] = None) -> None:
        self.llm_client = llm_client or OpenAILLMClient()

    def parse(self, prompt: str) -> SimulationSpec:
        prompt = prompt.strip()
        if not prompt:
            raise ValueError("Prompt cannot be empty")

        if self.llm_client.is_configured:
            try:
                return self._parse_with_llm(prompt)
            except Exception:
                # Fall back to heuristics if LLM fails
                pass

        return self._parse_with_rules(prompt)

    def _parse_with_llm(self, prompt: str) -> SimulationSpec:
        instructions = (
            "Convert the FEA description into JSON with keys: geometry_type (beam|plate), "
            "length_m, height_m, thickness_m, width_m, material, boundary_condition, "
            "load_type, load_magnitude_N, load_direction, load_location_relative. "
            "Use meters and SI units."
        )
        raw = self.llm_client.extract_structured(prompt, instructions)
        data = self._coerce_llm_payload(raw)
        return self._build_spec(prompt, data)

    def _coerce_llm_payload(self, payload: Dict[str, str]) -> Dict[str, float]:
        # Ensure numeric fields are floats
        numeric_fields = ["length_m", "height_m", "thickness_m", "width_m", "load_magnitude_N"]
        for field in numeric_fields:
            value = payload.get(field)
            if value is None:
                continue
            if isinstance(value, (int, float)):
                payload[field] = float(value)
            else:
                payload[field] = float(re.findall(r"-?\d+(?:\.\d+)?", str(value))[0])
        return payload

    def _build_spec(self, prompt: str, data: Dict[str, float]) -> SimulationSpec:
        geometry = GeometryType(data.get("geometry_type", "beam"))
        load_token = data.get("load_type")
        try:
            load_type = LoadType[load_token.upper()] if load_token else LoadType.POINT
        except (KeyError, AttributeError):
            load_type = LoadType.POINT
        material = self._detect_material(data.get("material", ""))

        load_case = LoadCase(
            load_type=load_type,
            magnitude=data.get("load_magnitude_N", 100.0),
            direction=data.get("load_direction", "-y"),
            location=data.get("load_location_relative"),
            units="Pa" if load_type == LoadType.PRESSURE else "N",
            description="LLM-parsed load",
        )

        return SimulationSpec(
            prompt=prompt,
            geometry=geometry,
            length=data.get("length_m", 1.0),
            height=data.get("height_m", 0.1),
            width=data.get("width_m"),
            thickness=data.get("thickness_m"),
            boundary_condition=data.get("boundary_condition", "fixed"),
            loads=[load_case],
            material=material,
        )

    def _parse_with_rules(self, prompt: str) -> SimulationSpec:
        tokens = prompt.lower()
        geometry = GeometryType.BEAM if "beam" in tokens else GeometryType.PLATE
        pair = self._extract_pair(tokens)
        length = pair[0] if pair else self._extract_dimension(tokens, ["length", "long"], default=1.0)
        height = self._extract_dimension(tokens, ["height", "thick", "depth"], default=0.1)
        thickness = self._extract_dimension(tokens, ["thick", "plate"], default=0.01)
        width = pair[1] if pair else self._extract_dimension(tokens, ["width"], default=0.1)
        boundary = self._detect_boundary(tokens)
        load_mag, detected_unit = self._extract_force(tokens, default=100.0)
        load_direction = "-y" if "down" in tokens or "downward" in tokens else "-z"
        location = 1.0 if "cantilever" in tokens or "tip" in tokens else 0.5

        material = self._detect_material(tokens)
        inferred_load_type = (
            LoadType.PRESSURE
            if geometry == GeometryType.PLATE or "pressure" in tokens or detected_unit == "Pa"
            else LoadType.POINT
        )
        load_units = "Pa" if inferred_load_type == LoadType.PRESSURE else "N"

        load_case = LoadCase(
            load_type=inferred_load_type,
            magnitude=load_mag,
            direction=load_direction,
            location=location,
            units=load_units,
            description="Auto-parsed load",
        )

        return SimulationSpec(
            prompt=prompt,
            geometry=geometry,
            length=length,
            height=height,
            thickness=None if geometry == GeometryType.BEAM else thickness,
            width=None if geometry == GeometryType.BEAM else width,
            boundary_condition=boundary,
            loads=[load_case],
            material=material,
        )

    def _detect_material(self, tokens: str) -> MaterialSpec:
        lowered = (tokens or "").lower()
        for key, mat in DEFAULT_MATERIALS.items():
            if key in lowered:
                return mat
        return DEFAULT_MATERIALS["steel"]

    def _detect_boundary(self, tokens: str) -> str:
        if "cantilever" in tokens or "fixed" in tokens:
            return "fixed"
        if "roller" in tokens or "simply supported" in tokens:
            return "roller"
        return "fixed"

    def _extract_dimension(self, tokens: str, keywords: list[str], default: float) -> float:
        for keyword in keywords:
            pattern = rf"{keyword}[^0-9]*(-?\d+(?:\.\d+)?)\s*(mm|cm|m)?"
            match = re.search(pattern, tokens)
            if match:
                value = float(match.group(1))
                unit = match.group(2) or "m"
                return self._to_meters(value, unit)
        return default

    def _extract_pair(self, tokens: str) -> Optional[tuple[float, float]]:
        pattern = r"(-?\d+(?:\.\d+)?)\s*(mm|cm|m)\s*(?:x|by)\s*(-?\d+(?:\.\d+)?)\s*(mm|cm|m)"
        match = re.search(pattern, tokens)
        if not match:
            return None
        first = self._to_meters(float(match.group(1)), match.group(2))
        second = self._to_meters(float(match.group(3)), match.group(4))
        return first, second

    def _extract_force(self, tokens: str, default: float) -> tuple[float, str]:
        pattern = r"(-?\d+(?:\.\d+)?)\s*(kn|n|kgf|mpa|kpa|pa)"
        match = re.search(pattern, tokens)
        if not match:
            return default, "N"
        value = float(match.group(1))
        unit = match.group(2)
        unit = unit.lower()
        multiplier = {
            "n": 1.0,
            "kn": 1e3,
            "kgf": 9.81,
            "pa": 1.0,
            "kpa": 1e3,
            "mpa": 1e6,
        }.get(unit, 1.0)
        si_value = value * multiplier
        output_unit = "Pa" if unit in {"pa", "kpa", "mpa"} else "N"
        return si_value, output_unit

    def _to_meters(self, value: float, unit: str) -> float:
        unit = unit.lower()
        if unit == "mm":
            return value / 1000.0
        if unit == "cm":
            return value / 100.0
        return value
