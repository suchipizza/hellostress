from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None


STRUCTURED_SCHEMA: Dict[str, Any] = {
    "name": "fea_simulation_extract",
    "schema": {
        "type": "object",
        "properties": {
            "geometry_type": {"type": "string"},
            "length_m": {"type": "number"},
            "beam_height_m": {"type": "number"},
            "beam_width_m": {"type": "number"},
            "plate_width_m": {"type": "number"},
            "plate_thickness_m": {"type": "number"},
            "height_m": {"type": "number"},
            "thickness_m": {"type": "number"},
            "width_m": {"type": "number"},
            "material": {"type": "string"},
            "boundary_condition": {"type": "string"},
            "load_type": {"type": "string"},
            "load_magnitude_N": {"type": "number"},
            "load_direction": {"type": "string"},
            "load_location_relative": {"type": "number"},
        },
        "required": [
            "geometry_type",
            "length_m",
            "material",
            "boundary_condition",
            "load_type",
            "load_magnitude_N",
            "load_direction",
        ],
        "additionalProperties": False,
    },
}


class OpenAILLMClient:
    """Thin wrapper around the OpenAI Responses API."""

    def __init__(
        self,
        model: Optional[str] = None,
        temperature: float = 0.1,
        api_key: Optional[str] = None,
    ) -> None:
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.temperature = temperature
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self._client = OpenAI(api_key=self.api_key) if self.api_key and OpenAI else None

    @property
    def is_configured(self) -> bool:
        return self._client is not None

    def extract_structured(self, prompt: str, instructions: str) -> Dict[str, Any]:
        if not self.is_configured:
            raise RuntimeError("OpenAI client not configured")

        response = self._client.responses.create(
            model=self.model,
            temperature=self.temperature,
            input=[
                {"role": "system", "content": instructions},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_schema", "json_schema": STRUCTURED_SCHEMA},
        )
        # The Responses API can return multiple outputs; use the first chunk.
        output = response.output[0].content[0].text  # type: ignore[index]
        return json.loads(output)

    def summarize(self, system_prompt: str, user_prompt: str) -> str:
        if not self.is_configured:
            raise RuntimeError("OpenAI client not configured")
        response = self._client.responses.create(
            model=self.model,
            temperature=self.temperature,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.output[0].content[0].text  # type: ignore[index]


__all__ = ["OpenAILLMClient"]
