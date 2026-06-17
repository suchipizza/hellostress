from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import plotly.graph_objects as go

from .models import GeometryType, SimulationSpec
from .solver import SolverArtifacts


@dataclass(frozen=True)
class SimulationVisualization:
    plotly_figure: go.Figure
    pyvista_image: Any | None
    source: str
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class FieldVisualizationData:
    points: np.ndarray
    triangles: np.ndarray
    display_displacement: np.ndarray
    stress: np.ndarray
    warp_scale: float


class SimulationVisualizer:
    DEFAULT_WARP_SCALE = 1.0e4
    MAX_VISIBLE_FRACTION = 0.15

    def build_visualization(
        self,
        spec: SimulationSpec,
        metrics: dict[str, float],
        artifacts: SolverArtifacts,
    ) -> SimulationVisualization:
        warnings: list[str] = []
        try:
            field_data = self._load_field_visualization_data(artifacts)
        except Exception as exc:
            field_data = None
            warnings.append(f"Solver field visualization unavailable: {exc}")
        if field_data is None:
            return SimulationVisualization(
                plotly_figure=self.build_figure(spec, metrics),
                pyvista_image=None,
                source="estimated_profile",
                warnings=warnings,
            )

        pyvista_image = None
        try:
            pyvista_image = self._build_pyvista_image(field_data)
        except Exception as exc:  # pragma: no cover - environment-specific rendering fallback
            warnings.append(f"PyVista preview unavailable: {exc}")

        return SimulationVisualization(
            plotly_figure=self._build_field_plotly_figure(spec, field_data),
            pyvista_image=pyvista_image,
            source="solver_field",
            warnings=warnings,
        )

    def build_figure(self, spec: SimulationSpec, metrics: dict[str, float]) -> go.Figure:
        if spec.geometry in {GeometryType.BEAM, GeometryType.BRACKET}:
            return self._beam_fig(spec, metrics)
        if spec.geometry == GeometryType.PLATE_WITH_HOLE:
            return self._plate_with_hole_fig(spec, metrics)
        return self._plate_fig(spec, metrics)

    def _beam_fig(self, spec: SimulationSpec, metrics: dict[str, float]) -> go.Figure:
        x = np.linspace(0, spec.length, 50)
        max_deflection = metrics.get("max_deflection", 0.0)
        y = max_deflection * (2 * (x / spec.length) ** 2 - (x / spec.length) ** 3)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=x, y=y * 1e3, mode="lines", name="Deflection (mm)"))
        fig.update_layout(
            title="Analytical Bracket Deflection Profile" if spec.geometry == GeometryType.BRACKET else "Estimated Beam Deflection Profile",
            xaxis_title="Length (m)",
            yaxis_title="Deflection (mm)",
            template="plotly_white",
        )
        return fig

    def _plate_fig(self, spec: SimulationSpec, metrics: dict[str, float]) -> go.Figure:
        if spec.plate_dimensions is None:
            raise ValueError("Plate simulations require plate dimensions.")
        size = 40
        x = np.linspace(0, spec.length, size)
        y = np.linspace(0, spec.plate_dimensions.width, size)
        xv, yv = np.meshgrid(x, y)
        max_deflection = metrics.get("max_deflection", 0.0)
        z = max_deflection * (
            np.sin(np.pi * xv / spec.length)
            * np.sin(np.pi * yv / spec.plate_dimensions.width)
        )
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

    def _plate_with_hole_fig(self, spec: SimulationSpec, metrics: dict[str, float]) -> go.Figure:
        if spec.plate_dimensions is None:
            raise ValueError("Plate-with-hole simulations require plate dimensions.")
        size = 60
        hole_diameter = float(spec.metadata.get("hole_diameter_m", 0.0))
        radius = hole_diameter / 2.0
        x = np.linspace(0, spec.length, size)
        y = np.linspace(0, spec.plate_dimensions.width, size)
        xv, yv = np.meshgrid(x, y)
        xc = spec.length / 2.0
        yc = spec.plate_dimensions.width / 2.0
        rr = np.sqrt((xv - xc) ** 2 + (yv - yc) ** 2)
        max_deflection = metrics.get("max_deflection", 0.0)
        base = max_deflection * (xv / max(spec.length, 1e-9))
        concentration = 1.0 + 0.8 * np.exp(-((rr - radius) / max(radius, 1e-9)) ** 2)
        z = base * concentration
        z = np.where(rr <= radius, np.nan, z)
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
            title="Analytical Plate-With-Hole Screening Surface",
            scene=dict(
                xaxis_title="Length (m)",
                yaxis_title="Width (m)",
                zaxis_title="Deflection (mm)",
            ),
        )
        return fig

    def _load_field_visualization_data(self, artifacts: SolverArtifacts) -> FieldVisualizationData | None:
        displacement_path = artifacts.results_dir / "displacement.xdmf"
        stress_path = artifacts.results_dir / "stress.xdmf"
        if not displacement_path.exists() or not stress_path.exists():
            return None

        topology, geometry, displacement = self._read_xdmf_field(displacement_path)
        _, _, stress = self._read_xdmf_field(stress_path)

        if topology.ndim != 2 or topology.shape[1] != 3:
            return None
        if geometry.ndim != 2 or geometry.shape[1] < 2:
            return None
        if displacement.shape[0] != geometry.shape[0] or stress.shape[0] != geometry.shape[0]:
            return None

        points = np.column_stack(
            [
                geometry[:, 0],
                geometry[:, 1],
                np.zeros(geometry.shape[0], dtype=float),
            ]
        )
        display_displacement = self._build_display_displacement(displacement)
        stress_values = stress.reshape(stress.shape[0], -1)[:, 0].astype(float)
        warp_scale = self._compute_warp_scale(points, display_displacement)
        return FieldVisualizationData(
            points=points,
            triangles=topology.astype(int),
            display_displacement=display_displacement,
            stress=stress_values,
            warp_scale=warp_scale,
        )

    def _read_xdmf_field(self, xdmf_path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        root = ET.parse(xdmf_path).getroot()
        domain = root.find("Domain")
        if domain is None:
            raise ValueError(f"Invalid XDMF file with no Domain: {xdmf_path}")

        mesh_grid = domain.find("./Grid[@GridType='Uniform']")
        field_grid = domain.find("./Grid[@CollectionType='Temporal']/Grid")
        if mesh_grid is None or field_grid is None:
            raise ValueError(f"Unsupported XDMF grid layout: {xdmf_path}")

        topology_item = mesh_grid.find("./Topology/DataItem")
        geometry_item = mesh_grid.find("./Geometry/DataItem")
        attribute_item = field_grid.find("./Attribute/DataItem")
        if topology_item is None or geometry_item is None or attribute_item is None:
            raise ValueError(f"Incomplete XDMF payload: {xdmf_path}")

        topology = self._read_hdf_data_item(xdmf_path.parent, topology_item.text)
        geometry = self._read_hdf_data_item(xdmf_path.parent, geometry_item.text)
        attribute = self._read_hdf_data_item(xdmf_path.parent, attribute_item.text)
        return topology, geometry, attribute

    def _read_hdf_data_item(self, base_dir: Path, reference: str | None) -> np.ndarray:
        import h5py

        if reference is None or ":" not in reference:
            raise ValueError("Expected HDF data item reference in XDMF.")
        file_name, dataset_name = reference.split(":", maxsplit=1)
        hdf_path = (base_dir / file_name).resolve()
        with h5py.File(hdf_path, "r") as handle:
            return np.asarray(handle[dataset_name])

    def _build_display_displacement(self, displacement: np.ndarray) -> np.ndarray:
        disp = displacement.reshape(displacement.shape[0], -1).astype(float)
        x_component = disp[:, 0] if disp.shape[1] >= 1 else np.zeros(disp.shape[0], dtype=float)
        z_component = disp[:, 1] if disp.shape[1] >= 2 else x_component
        return np.column_stack([x_component, np.zeros(disp.shape[0], dtype=float), z_component])

    def _compute_warp_scale(self, points: np.ndarray, displacement: np.ndarray) -> float:
        base_span = max(
            float(np.ptp(points[:, 0])) if points.shape[0] else 0.0,
            float(np.ptp(points[:, 1])) if points.shape[0] else 0.0,
            1.0,
        )
        displacement_magnitude = np.linalg.norm(displacement, axis=1)
        max_magnitude = float(displacement_magnitude.max()) if displacement_magnitude.size else 0.0
        if max_magnitude <= 0.0:
            return 1.0
        max_visible_scale = self.MAX_VISIBLE_FRACTION * base_span / max_magnitude
        return min(self.DEFAULT_WARP_SCALE, max_visible_scale)

    def _build_field_plotly_figure(
        self,
        spec: SimulationSpec,
        field_data: FieldVisualizationData,
    ) -> go.Figure:
        warped_points = field_data.points + field_data.display_displacement * field_data.warp_scale
        displacement_magnitude = np.linalg.norm(field_data.display_displacement, axis=1)

        fig = go.Figure(
            data=[
                go.Mesh3d(
                    x=warped_points[:, 0],
                    y=warped_points[:, 1],
                    z=warped_points[:, 2],
                    i=field_data.triangles[:, 0],
                    j=field_data.triangles[:, 1],
                    k=field_data.triangles[:, 2],
                    intensity=field_data.stress,
                    intensitymode="vertex",
                    colorscale="Viridis",
                    colorbar=dict(title="Stress (Pa)"),
                    customdata=np.column_stack([field_data.stress, displacement_magnitude]),
                    hovertemplate=(
                        "stress=%{customdata[0]:.3e} Pa"
                        "<br>|u|=%{customdata[1]:.3e} m"
                        "<extra></extra>"
                    ),
                    opacity=0.95,
                    name="Solver field",
                )
            ]
        )
        fig.update_layout(
            title=f"{self._field_plotly_title(spec)} (display warp x{field_data.warp_scale:.2e})",
            template="plotly_white",
            scene=dict(
                xaxis_title="Length (m)",
                yaxis_title="Width / Height (m)",
                zaxis_title="Warped displacement",
                aspectmode="data",
            ),
            margin=dict(l=0, r=0, t=48, b=0),
        )
        return fig

    def _build_pyvista_image(self, field_data: FieldVisualizationData) -> Any | None:
        import pyvista as pv

        pv.OFF_SCREEN = True
        faces = np.hstack(
            [
                np.full((field_data.triangles.shape[0], 1), 3, dtype=np.int64),
                field_data.triangles.astype(np.int64),
            ]
        ).ravel()
        mesh = pv.PolyData(field_data.points, faces)
        mesh.point_data["display_displacement"] = field_data.display_displacement
        mesh.point_data["stress"] = field_data.stress
        warped = mesh.warp_by_vector("display_displacement", factor=field_data.warp_scale)

        plotter = pv.Plotter(off_screen=True, window_size=(900, 520))
        plotter.set_background("white")
        plotter.add_mesh(
            warped,
            scalars="stress",
            cmap="viridis",
            show_edges=True,
            scalar_bar_args={"title": "Stress (Pa)"},
        )
        plotter.view_isometric()
        image = plotter.screenshot(return_img=True)
        plotter.close()
        return image

    def _field_plotly_title(self, spec: SimulationSpec) -> str:
        if spec.geometry == GeometryType.BEAM:
            return "Solver Beam Field View"
        return "Solver Plate Field View"


__all__ = ["SimulationVisualization", "SimulationVisualizer"]
