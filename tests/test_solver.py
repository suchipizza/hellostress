from __future__ import annotations

from pathlib import Path

import pytest

from fea_engine import BeamSection, LoadCase, SolverExecutionError, UnsupportedSolverModeError
from fea_engine.models import DEFAULT_MATERIALS, GeometryType, LoadType, SimulationSpec
from fea_engine.solver import FenicsSolver


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


def test_solver_rejects_unsupported_local_mode() -> None:
    with pytest.raises(UnsupportedSolverModeError):
        FenicsSolver(mode="local")


def test_solver_mock_contract_writes_metrics(tmp_path: Path) -> None:
    solver = FenicsSolver(mode="mock", workspace=tmp_path)

    artifacts = solver.run(build_beam_spec(), "print('simulation')")

    assert artifacts.backend_mode == "mock"
    assert artifacts.script_path.exists()
    assert artifacts.results_dir.exists()
    assert artifacts.metrics_path.exists()
    assert artifacts.generated_files == [artifacts.metrics_path]
    assert artifacts.warnings == []


def test_solver_docker_mode_requires_docker(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("shutil.which", lambda command: None)

    with pytest.raises(SolverExecutionError):
        FenicsSolver(mode="docker")
