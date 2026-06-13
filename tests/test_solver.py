from __future__ import annotations

from pathlib import Path
import subprocess

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

    assert artifacts.run_dir.exists()
    assert artifacts.backend_mode == "mock"
    assert artifacts.script_path.exists()
    assert artifacts.results_dir.exists()
    assert artifacts.metrics_path.exists()
    assert artifacts.run_metadata.command == ["mock"]
    assert artifacts.run_metadata.exit_code == 0
    assert artifacts.run_metadata.stdout_path.exists()
    assert artifacts.run_metadata.stderr_path.exists()
    assert "Mock solver produced analytical estimate." in artifacts.run_metadata.stdout_excerpt
    assert artifacts.generated_files == [artifacts.metrics_path]
    assert artifacts.warnings == []


def test_solver_docker_mode_requires_docker(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("shutil.which", lambda command: None)

    with pytest.raises(SolverExecutionError):
        FenicsSolver(mode="docker")


def test_solver_docker_success_captures_stdout_stderr_metadata(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr("shutil.which", lambda command: "/usr/bin/docker")

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=kwargs.get("args", args[0]),
            returncode=0,
            stdout="solver ok\nline two",
            stderr="warning line",
        )

    monkeypatch.setattr("subprocess.run", fake_run)
    solver = FenicsSolver(mode="docker", workspace=tmp_path)

    artifacts = solver.run(build_beam_spec(), "print('simulation')")

    assert artifacts.backend_mode == "docker"
    assert artifacts.run_metadata.command[0] == "docker"
    assert artifacts.run_metadata.exit_code == 0
    assert artifacts.run_metadata.stdout_excerpt == "solver ok line two"
    assert artifacts.run_metadata.stderr_excerpt == "warning line"
    assert artifacts.run_metadata.stdout_path.read_text(encoding="utf-8") == "solver ok\nline two"
    assert artifacts.run_metadata.stderr_path.read_text(encoding="utf-8") == "warning line"


def test_solver_docker_failure_exposes_structured_metadata(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr("shutil.which", lambda command: "/usr/bin/docker")

    def fake_run(*args, **kwargs):
        raise subprocess.CalledProcessError(
            returncode=125,
            cmd=kwargs.get("args", args[0]),
            output="stdout details",
            stderr="stderr details",
        )

    monkeypatch.setattr("subprocess.run", fake_run)
    solver = FenicsSolver(mode="docker", workspace=tmp_path)

    with pytest.raises(SolverExecutionError) as exc_info:
        solver.run(build_beam_spec(), "print('simulation')")

    error = exc_info.value
    assert error.backend_mode == "docker"
    assert error.exit_code == 125
    assert error.command[0] == "docker"
    assert error.stdout_excerpt == "stdout details"
    assert error.stderr_excerpt == "stderr details"
    assert error.stdout_path is not None and error.stdout_path.exists()
    assert error.stderr_path is not None and error.stderr_path.exists()
