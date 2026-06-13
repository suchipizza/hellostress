from __future__ import annotations

from typing import Optional

from .llm_client import OpenAILLMClient
from .models import SimulationSpec


class ResultSummarizer:
    def __init__(self, llm_client: Optional[OpenAILLMClient] = None) -> None:
        self.llm_client = llm_client or OpenAILLMClient()

    def summarize(self, spec: SimulationSpec, metrics: dict[str, float]) -> str:
        template = (
            "Simulated {geometry} with length {length:.2f} m. Max deflection = {defl:.3e} m. "
            "Max stress = {stress:.3e} Pa. Material yield ~ {yield_strength} Pa."
        )
        fallback = template.format(
            geometry=spec.geometry.value,
            length=spec.length,
            defl=metrics.get("max_deflection", 0.0),
            stress=metrics.get("max_stress", 0.0),
            yield_strength=getattr(spec.material, "yield_strength", "unknown"),
        )

        if not self.llm_client.is_configured:
            return fallback

        try:
            user_prompt = (
                "Create a short engineering summary (<=60 words) for the following metrics:\n"
                f"Spec: {spec}\n"
                f"Metrics: {metrics}\n"
                "Highlight whether the max stress is below the material yield strength."
            )
            return self.llm_client.summarize(
                system_prompt="You are an FEA assistant providing concise safety insights.",
                user_prompt=user_prompt,
            )
        except Exception:
            return fallback


__all__ = ["ResultSummarizer"]
