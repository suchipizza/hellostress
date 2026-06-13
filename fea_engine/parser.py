from __future__ import annotations

import re
from typing import Any, Dict, Iterable, Optional

from .errors import PromptParseError
from .llm_client import OpenAILLMClient
from .models import (
    BeamSection,
    DEFAULT_MATERIALS,
    GeometryType,
    LoadCase,
    LoadType,
    MaterialSpec,
    PlateDimensions,
    SimulationSpec,
)
from .validation import SimulationSpecValidator


class PromptParser:
    """Parses natural-language prompts into structured simulation specs."""

    def __init__(
        self,
        llm_client: Optional[OpenAILLMClient] = None,
        validator: Optional[SimulationSpecValidator] = None,
    ) -> None:
        self.llm_client = llm_client or OpenAILLMClient()
        self.validator = validator or SimulationSpecValidator()

    def parse(self, prompt: str) -> SimulationSpec:
        prompt = prompt.strip()
        if not prompt:
            raise PromptParseError("Please provide a non-empty simulation prompt.")

        if self.llm_client.is_configured:
            try:
                return self._parse_with_llm(prompt)
            except Exception:
                # Fall back to heuristics if the LLM response is incomplete or malformed.
                pass

        return self._parse_with_rules(prompt)

    def _parse_with_llm(self, prompt: str) -> SimulationSpec:
        instructions = (
            "Convert the FEA description into JSON with keys: geometry_type (beam|plate), "
            "length_m, beam_height_m, beam_width_m, plate_width_m, plate_thickness_m, "
            "material, boundary_condition (fixed|roller), load_type (point|distributed|pressure), "
            "load_magnitude_N, load_direction, load_location_relative. Use SI units. "
            "For pressure loads, return Pascals in load_magnitude_N."
        )
        raw = self.llm_client.extract_structured(prompt, instructions)
        data = self._coerce_llm_payload(raw)
        return self._build_spec(prompt, data)

    def _coerce_llm_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        numeric_fields = [
            "length_m",
            "beam_height_m",
            "beam_width_m",
            "plate_width_m",
            "plate_thickness_m",
            "height_m",
            "width_m",
            "thickness_m",
            "load_magnitude_N",
            "load_location_relative",
        ]
        for field in numeric_fields:
            value = payload.get(field)
            if value is None:
                continue
            if isinstance(value, (int, float)):
                payload[field] = float(value)
                continue
            match = re.search(r"-?\d+(?:\.\d+)?", str(value))
            if match:
                payload[field] = float(match.group(0))
        return payload

    def _build_spec(self, prompt: str, data: Dict[str, Any]) -> SimulationSpec:
        geometry = self._coerce_geometry(data.get("geometry_type"))
        load_type = self._coerce_load_type(data.get("load_type"))
        material = self._detect_material(str(data.get("material", "")))

        load_case = LoadCase(
            load_type=load_type,
            magnitude=float(data.get("load_magnitude_N", 0.0)),
            direction=str(data.get("load_direction", "-y")),
            location=data.get("load_location_relative"),
            units="Pa" if load_type == LoadType.PRESSURE else "N",
            description="LLM-parsed load",
        )

        if geometry == GeometryType.BEAM:
            beam_height = self._first_present(data, ["beam_height_m", "height_m", "thickness_m"])
            beam_width = self._first_present(data, ["beam_width_m", "width_m"], fallback=beam_height)
            spec = SimulationSpec(
                prompt=prompt,
                geometry=geometry,
                length=float(data.get("length_m", 0.0)),
                beam_section=BeamSection(height=beam_height, width=beam_width),
                boundary_condition=str(data.get("boundary_condition", "fixed")),
                loads=[load_case],
                material=material,
            )
        else:
            plate_width = self._first_present(data, ["plate_width_m", "width_m"])
            plate_thickness = self._first_present(
                data,
                ["plate_thickness_m", "thickness_m", "height_m"],
            )
            spec = SimulationSpec(
                prompt=prompt,
                geometry=geometry,
                length=float(data.get("length_m", 0.0)),
                plate_dimensions=PlateDimensions(width=plate_width, thickness=plate_thickness),
                boundary_condition=str(data.get("boundary_condition", "fixed")),
                loads=[load_case],
                material=material,
            )

        return self.validator.validate(spec)

    def _parse_with_rules(self, prompt: str) -> SimulationSpec:
        tokens = prompt.lower()
        geometry = self._detect_geometry(tokens)
        material = self._detect_material(tokens)
        boundary = self._detect_boundary(tokens)
        load_mag, load_unit = self._extract_force(tokens)
        load_type = self._detect_load_type(tokens, load_unit)

        load_case = LoadCase(
            load_type=load_type,
            magnitude=load_mag,
            direction=self._detect_load_direction(tokens),
            location=self._detect_load_location(tokens, geometry, load_type),
            units=load_unit,
            description="Auto-parsed load",
        )

        if geometry == GeometryType.BEAM:
            beam_height = self._extract_required_dimension(
                tokens,
                ["thick", "thickness", "depth", "deep", "height", "high"],
                "beam thickness/height",
            )
            beam_width = self._extract_optional_dimension(tokens, ["wide", "width"]) or beam_height
            spec = SimulationSpec(
                prompt=prompt,
                geometry=geometry,
                length=self._extract_beam_length(tokens),
                beam_section=BeamSection(height=beam_height, width=beam_width),
                boundary_condition=boundary,
                loads=[load_case],
                material=material,
            )
        else:
            plate_length, plate_width = self._extract_plate_span(tokens)
            plate_thickness = self._extract_required_dimension(
                tokens,
                ["thick", "thickness"],
                "plate thickness",
            )
            spec = SimulationSpec(
                prompt=prompt,
                geometry=geometry,
                length=plate_length,
                plate_dimensions=PlateDimensions(width=plate_width, thickness=plate_thickness),
                boundary_condition=boundary,
                loads=[load_case],
                material=material,
            )

        return self.validator.validate(spec)

    def _detect_geometry(self, tokens: str) -> GeometryType:
        if "beam" in tokens:
            return GeometryType.BEAM
        if "plate" in tokens:
            return GeometryType.PLATE
        raise PromptParseError("Prompt must mention either a beam or a plate.")

    def _detect_material(self, tokens: str) -> MaterialSpec:
        lowered = (tokens or "").lower()
        for key, mat in DEFAULT_MATERIALS.items():
            if key in lowered:
                return mat
        return DEFAULT_MATERIALS["steel"]

    def _detect_boundary(self, tokens: str) -> str:
        if "simply supported" in tokens or "roller" in tokens:
            return "roller"
        if "cantilever" in tokens or "fixed" in tokens:
            return "fixed"
        return "fixed"

    def _detect_load_type(self, tokens: str, detected_unit: str) -> LoadType:
        if "pressure" in tokens or detected_unit == "Pa":
            return LoadType.PRESSURE
        if "distributed" in tokens or "uniform load" in tokens:
            return LoadType.DISTRIBUTED
        return LoadType.POINT

    def _detect_load_direction(self, tokens: str) -> str:
        if "upward" in tokens or "up " in tokens:
            return "+y"
        if "down" in tokens or "downward" in tokens:
            return "-y"
        return "-z"

    def _detect_load_location(
        self,
        tokens: str,
        geometry: GeometryType,
        load_type: LoadType,
    ) -> Optional[float]:
        if geometry != GeometryType.BEAM or load_type == LoadType.PRESSURE:
            return None
        if "tip" in tokens or "cantilever" in tokens or "end load" in tokens:
            return 1.0
        if "midspan" in tokens or "center" in tokens or "centre" in tokens:
            return 0.5
        if "root" in tokens or "start" in tokens:
            return 0.0
        return 0.5 if load_type == LoadType.POINT else None

    def _extract_beam_length(self, tokens: str) -> float:
        explicit = self._extract_optional_dimension(tokens, ["length", "long", "span"])
        if explicit is not None:
            return explicit
        all_dimensions = self._extract_all_dimensions(tokens)
        if all_dimensions:
            return all_dimensions[0]
        raise PromptParseError("Could not determine the beam length from the prompt.")

    def _extract_plate_span(self, tokens: str) -> tuple[float, float]:
        pair = self._extract_pair(tokens)
        if pair:
            return pair

        length = self._extract_optional_dimension(tokens, ["length", "long"])
        width = self._extract_optional_dimension(tokens, ["width", "wide"])
        if length is not None and width is not None:
            return length, width

        all_dimensions = self._extract_all_dimensions(tokens)
        if len(all_dimensions) >= 2:
            return all_dimensions[0], all_dimensions[1]

        raise PromptParseError("Could not determine both plate length and width from the prompt.")

    def _extract_required_dimension(
        self,
        tokens: str,
        keywords: Iterable[str],
        label: str,
    ) -> float:
        value = self._extract_optional_dimension(tokens, keywords)
        if value is None:
            raise PromptParseError(f"Could not determine {label} from the prompt.")
        return value

    def _extract_optional_dimension(
        self,
        tokens: str,
        keywords: Iterable[str],
    ) -> Optional[float]:
        for keyword in keywords:
            before = re.search(
                rf"(?P<value>-?\d+(?:\.\d+)?)\s*(?P<unit>mm|cm|m)\b(?:\s+[a-z-]+){{0,2}}\s+{re.escape(keyword)}\b",
                tokens,
            )
            if before:
                return self._to_meters(float(before.group("value")), before.group("unit"))

            after = re.search(
                rf"\b{re.escape(keyword)}\b[^0-9-]{{0,20}}(?P<value>-?\d+(?:\.\d+)?)\s*(?P<unit>mm|cm|m)\b",
                tokens,
            )
            if after:
                return self._to_meters(float(after.group("value")), after.group("unit"))
        return None

    def _extract_pair(self, tokens: str) -> Optional[tuple[float, float]]:
        match = re.search(
            r"(-?\d+(?:\.\d+)?)\s*(mm|cm|m)\s*(?:x|by)\s*(-?\d+(?:\.\d+)?)\s*(mm|cm|m)",
            tokens,
        )
        if not match:
            return None
        first = self._to_meters(float(match.group(1)), match.group(2))
        second = self._to_meters(float(match.group(3)), match.group(4))
        return first, second

    def _extract_all_dimensions(self, tokens: str) -> list[float]:
        return [
            self._to_meters(float(match.group("value")), match.group("unit"))
            for match in re.finditer(
                r"(?P<value>-?\d+(?:\.\d+)?)\s*(?P<unit>mm|cm|m)\b",
                tokens,
            )
        ]

    def _extract_force(self, tokens: str) -> tuple[float, str]:
        match = re.search(r"(-?\d+(?:\.\d+)?)\s*(kn|n|kgf|mpa|kpa|pa)\b", tokens)
        if not match:
            raise PromptParseError("Could not determine the load magnitude and units from the prompt.")

        value = float(match.group(1))
        unit = match.group(2).lower()
        multiplier = {
            "n": 1.0,
            "kn": 1e3,
            "kgf": 9.81,
            "pa": 1.0,
            "kpa": 1e3,
            "mpa": 1e6,
        }[unit]
        si_value = value * multiplier
        output_unit = "Pa" if unit in {"pa", "kpa", "mpa"} else "N"
        return si_value, output_unit

    def _coerce_geometry(self, geometry_token: Any) -> GeometryType:
        if geometry_token is None:
            raise PromptParseError("LLM output did not include a geometry type.")
        try:
            return GeometryType(str(geometry_token).lower())
        except ValueError as exc:
            raise PromptParseError(f"Unsupported geometry type: {geometry_token}") from exc

    def _coerce_load_type(self, load_token: Any) -> LoadType:
        if load_token is None:
            raise PromptParseError("LLM output did not include a load type.")
        try:
            return LoadType(str(load_token).lower())
        except ValueError as exc:
            raise PromptParseError(f"Unsupported load type: {load_token}") from exc

    def _first_present(
        self,
        data: Dict[str, Any],
        keys: Iterable[str],
        fallback: Optional[float] = None,
    ) -> float:
        for key in keys:
            value = data.get(key)
            if isinstance(value, (int, float)) and value > 0:
                return float(value)
        if fallback is not None:
            return fallback
        raise PromptParseError(f"LLM output is missing required numeric fields: {', '.join(keys)}")

    def _to_meters(self, value: float, unit: str) -> float:
        unit = unit.lower()
        if unit == "mm":
            return value / 1000.0
        if unit == "cm":
            return value / 100.0
        return value
