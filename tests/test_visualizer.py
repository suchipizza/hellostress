from __future__ import annotations

from pathlib import Path

import h5py

from fea_engine import BeamSection, LoadCase, SimulationSpec
from fea_engine.models import DEFAULT_MATERIALS, GeometryType, LoadType
from fea_engine.solver import BackendRuntimeMetadata, SolverArtifacts, SolverRunMetadata
from fea_engine.visualizer import SimulationVisualizer


def build_beam_spec() -> SimulationSpec:
    return SimulationSpec(
        prompt="beam fixture",
        geometry=GeometryType.BEAM,
        length=1.0,
        beam_section=BeamSection(height=0.1, width=0.1),
        boundary_condition="fixed",
        loads=[
            LoadCase(
                load_type=LoadType.POINT,
                magnitude=150.0,
                direction="-y",
                location=1.0,
                units="N",
            )
        ],
        material=DEFAULT_MATERIALS["steel"],
    )


def build_artifacts(tmp_path: Path) -> SolverArtifacts:
    run_dir = tmp_path / "run"
    results_dir = run_dir / "results"
    results_dir.mkdir(parents=True)
    script_path = run_dir / "simulation.py"
    script_path.write_text("print('simulation')\n", encoding="utf-8")
    metrics_path = results_dir / "metrics.json"
    metrics_path.write_text('{"max_deflection": 0.01, "max_stress": 2.5}', encoding="utf-8")
    stdout_path = run_dir / "solver.stdout.log"
    stderr_path = run_dir / "solver.stderr.log"
    stdout_path.write_text("", encoding="utf-8")
    stderr_path.write_text("", encoding="utf-8")
    backend_status_path = run_dir / "backend_status.json"
    backend_status_path.write_text("{}", encoding="utf-8")
    backend_metadata_path = run_dir / "backend_metadata.json"
    backend_metadata_path.write_text("{}", encoding="utf-8")
    return SolverArtifacts(
        run_dir=run_dir,
        backend_mode="docker",
        backend_status="succeeded",
        script_path=script_path,
        results_dir=results_dir,
        metrics_path=metrics_path,
        backend_status_path=backend_status_path,
        backend_metadata_path=backend_metadata_path,
        run_metadata=SolverRunMetadata(
            command=["docker"],
            exit_code=0,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
        ),
        runtime_metadata=BackendRuntimeMetadata(),
        generated_files=[metrics_path],
    )


def write_field_file(path: Path, *, attribute_type: str, values) -> None:
    h5_path = path.with_suffix(".h5")
    topology = [[0, 1, 2], [0, 2, 3]]
    geometry = [[0.0, 0.0], [1.0, 0.0], [1.0, 0.3], [0.0, 0.3]]

    with h5py.File(h5_path, "w") as handle:
        handle.create_dataset("/Mesh/mesh/topology", data=topology)
        handle.create_dataset("/Mesh/mesh/geometry", data=geometry)
        handle.create_dataset("/Function/f/0", data=values)

    path.write_text(
        f"""<?xml version="1.0"?>
<!DOCTYPE Xdmf SYSTEM "Xdmf.dtd" []>
<Xdmf Version="3.0" xmlns:xi="https://www.w3.org/2001/XInclude">
  <Domain>
    <Grid Name="mesh" GridType="Uniform">
      <Topology TopologyType="Triangle" NumberOfElements="2" NodesPerElement="3">
        <DataItem Dimensions="2 3" NumberType="Int" Format="HDF">{h5_path.name}:/Mesh/mesh/topology</DataItem>
      </Topology>
      <Geometry GeometryType="XY">
        <DataItem Dimensions="4 2" Format="HDF">{h5_path.name}:/Mesh/mesh/geometry</DataItem>
      </Geometry>
    </Grid>
    <Grid Name="f" GridType="Collection" CollectionType="Temporal">
      <Grid Name="f" GridType="Uniform">
        <xi:include xpointer="xpointer(/Xdmf/Domain/Grid[@GridType='Uniform'][1]/*[self::Topology or self::Geometry])" />
        <Time Value="0" />
        <Attribute Name="f" AttributeType="{attribute_type}" Center="Node">
          <DataItem Dimensions="4 {'3' if attribute_type == 'Vector' else '1'}" Format="HDF">{h5_path.name}:/Function/f/0</DataItem>
        </Attribute>
      </Grid>
    </Grid>
  </Domain>
</Xdmf>
""",
        encoding="utf-8",
    )


def test_visualizer_builds_solver_field_plotly_and_pyvista_views(tmp_path: Path) -> None:
    artifacts = build_artifacts(tmp_path)
    write_field_file(
        artifacts.results_dir / "displacement.xdmf",
        attribute_type="Vector",
        values=[
            [0.0, 0.0, 0.0],
            [0.0, -0.01, 0.0],
            [0.0, -0.02, 0.0],
            [0.0, -0.01, 0.0],
        ],
    )
    write_field_file(
        artifacts.results_dir / "stress.xdmf",
        attribute_type="Scalar",
        values=[[1.0], [2.0], [3.0], [4.0]],
    )

    visualization = SimulationVisualizer().build_visualization(
        build_beam_spec(),
        {"max_deflection": 0.02, "max_stress": 4.0},
        artifacts,
    )

    assert visualization.source == "solver_field"
    assert visualization.plotly_figure.data[0].type == "mesh3d"
    assert visualization.pyvista_image is not None
    assert visualization.pyvista_image.shape[2] == 3
    assert visualization.warnings == []


def test_visualizer_falls_back_to_estimated_plot_when_field_files_are_missing(tmp_path: Path) -> None:
    artifacts = build_artifacts(tmp_path)

    visualization = SimulationVisualizer().build_visualization(
        build_beam_spec(),
        {"max_deflection": 0.02, "max_stress": 4.0},
        artifacts,
    )

    assert visualization.source == "estimated_profile"
    assert visualization.plotly_figure.data[0].type == "scatter"
    assert visualization.pyvista_image is None
