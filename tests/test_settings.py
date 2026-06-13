from __future__ import annotations

from pathlib import Path

import pytest

from fea_engine import ConfigurationError, RuntimeSettings


def test_runtime_settings_from_env_uses_validated_defaults(tmp_path: Path) -> None:
    settings = RuntimeSettings.from_env(
        {
            "FEA_DEFAULT_SOLVER_MODE": "auto",
            "FEA_DEFAULT_MESH_DENSITY": "40",
            "FEA_DOCKER_IMAGE": "custom/dolfinx:latest",
            "FEA_SOLVER_TIMEOUT_SECONDS": "120",
            "FEA_RUNS_DIR": str(tmp_path / "runs"),
            "OPENAI_MODEL": "gpt-4.1-mini",
        }
    )

    assert settings.default_solver_mode == "auto"
    assert settings.default_mesh_density == 40
    assert settings.docker_image == "custom/dolfinx:latest"
    assert settings.solver_timeout_seconds == 120
    assert settings.runs_workspace == tmp_path / "runs"
    assert settings.openai_model == "gpt-4.1-mini"


@pytest.mark.parametrize(
    ("env", "expected_message"),
    [
        ({"FEA_DEFAULT_SOLVER_MODE": "local"}, "Invalid FEA_DEFAULT_SOLVER_MODE"),
        ({"FEA_DEFAULT_MESH_DENSITY": "8"}, "FEA_DEFAULT_MESH_DENSITY must be >= 12."),
        ({"FEA_SOLVER_TIMEOUT_SECONDS": "0"}, "FEA_SOLVER_TIMEOUT_SECONDS must be >= 1."),
        ({"FEA_DOCKER_IMAGE": "   "}, "FEA_DOCKER_IMAGE must not be empty."),
        ({"OPENAI_MODEL": "   "}, "OPENAI_MODEL must not be empty"),
    ],
)
def test_runtime_settings_from_env_rejects_invalid_values(
    env: dict[str, str],
    expected_message: str,
) -> None:
    with pytest.raises(ConfigurationError, match=expected_message):
        RuntimeSettings.from_env(env)


def test_runtime_settings_build_solver_uses_configured_backend_values(tmp_path: Path) -> None:
    settings = RuntimeSettings(
        default_solver_mode="mock",
        default_mesh_density=32,
        docker_image="custom/dolfinx:latest",
        solver_timeout_seconds=45,
        runs_workspace=tmp_path / "workspace",
        openai_model="gpt-4o-mini",
    )

    solver = settings.build_solver()

    assert solver.mode == "mock"
    assert solver.docker_image == "custom/dolfinx:latest"
    assert solver.timeout_seconds == 45
    assert solver.workspace == tmp_path / "workspace"
