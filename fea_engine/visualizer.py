from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from .models import GeometryType, SimulationSpec


class SimulationVisualizer:
    def build_figure(self, spec: SimulationSpec, metrics: dict[str, float]) -> go.Figure:
        if spec.geometry == GeometryType.BEAM:
            return self._beam_fig(spec, metrics)
        return self._plate_fig(spec, metrics)

    def _beam_fig(self, spec: SimulationSpec, metrics: dict[str, float]) -> go.Figure:
        x = np.linspace(0, spec.length, 50)
        max_deflection = metrics.get("max_deflection", 0.0)
        y = max_deflection * (2 * (x / spec.length) ** 2 - (x / spec.length) ** 3)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=x, y=y * 1e3, mode="lines", name="Deflection (mm)"))
        fig.update_layout(
            title="Estimated Beam Deflection Profile",
            xaxis_title="Length (m)",
            yaxis_title="Deflection (mm)",
            template="plotly_white",
        )
        return fig

    def _plate_fig(self, spec: SimulationSpec, metrics: dict[str, float]) -> go.Figure:
        size = 40
        x = np.linspace(0, spec.length, size)
        y = np.linspace(0, spec.width or spec.height, size)
        xv, yv = np.meshgrid(x, y)
        max_deflection = metrics.get("max_deflection", 0.0)
        z = max_deflection * (np.sin(np.pi * xv / spec.length) * np.sin(np.pi * yv / (spec.width or spec.height)))
        fig = go.Figure(
            data=[
                go.Surface(
                    x=xv,
                    y=yv,
                    z=z * 1e3,
                    colorscale="Viridis",
                    colorbar=dict(title="Deflection (mm)"),
                )
            ]
        )
        fig.update_layout(
            title="Estimated Plate Deflection Surface",
            scene=dict(
                xaxis_title="Length (m)",
                yaxis_title="Width (m)",
                zaxis_title="Deflection (mm)",
            ),
        )
        return fig


__all__ = ["SimulationVisualizer"]
