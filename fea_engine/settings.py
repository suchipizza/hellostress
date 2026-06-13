from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional

from .errors import ConfigurationError


SUPPORTED_SOLVER_MODES = ("auto", "docker", "mock")
DEFAULT_DOCKER_IMAGE = "dolfinx/dolfinx:v0.7.3"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"


@dataclass(frozen=True)
class RuntimeSettings:
    default_solver_mode: str = "mock"
    default_mesh_density: int = 32
    docker_image: str = DEFAULT_DOCKER_IMAGE
    solver_timeout_seconds: int = 60
    runs_workspace: Path = Path(tempfile.gettempdir()) / "fea_runs"
    openai_model: str = DEFAULT_OPENAI_MODEL

    @classmethod
    def from_env(cls, environ: Optional[Mapping[str, str]] = None) -> "RuntimeSettings":
        env = environ or os.environ
        default_solver_mode = env.get("FEA_DEFAULT_SOLVER_MODE", "mock").strip().lower()
        if default_solver_mode not in SUPPORTED_SOLVER_MODES:
            supported = ", ".join(SUPPORTED_SOLVER_MODES)
            raise ConfigurationError(
                "Invalid FEA_DEFAULT_SOLVER_MODE "
                f"'{default_solver_mode}'. Supported values: {supported}."
            )

        default_mesh_density = cls._read_int(
            env,
            "FEA_DEFAULT_MESH_DENSITY",
            default=32,
            minimum=12,
            maximum=80,
        )
        solver_timeout_seconds = cls._read_int(
            env,
            "FEA_SOLVER_TIMEOUT_SECONDS",
            default=60,
            minimum=1,
        )
        docker_image = env.get("FEA_DOCKER_IMAGE", DEFAULT_DOCKER_IMAGE).strip()
        if not docker_image:
            raise ConfigurationError("FEA_DOCKER_IMAGE must not be empty.")

        workspace_value = env.get("FEA_RUNS_DIR", "").strip()
        runs_workspace = Path(workspace_value).expanduser() if workspace_value else cls.runs_workspace

        openai_model = env.get("OPENAI_MODEL", DEFAULT_OPENAI_MODEL).strip()
        if not openai_model:
            raise ConfigurationError("OPENAI_MODEL must not be empty when provided.")

        return cls(
            default_solver_mode=default_solver_mode,
            default_mesh_density=default_mesh_density,
            docker_image=docker_image,
            solver_timeout_seconds=solver_timeout_seconds,
            runs_workspace=runs_workspace,
            openai_model=openai_model,
        )

    def build_solver(self, requested_mode: Optional[str] = None):
        from .solver import FenicsSolver

        solver_mode = requested_mode or self.default_solver_mode
        return FenicsSolver(
            mode=solver_mode,
            docker_image=self.docker_image,
            timeout_seconds=self.solver_timeout_seconds,
            workspace=self.runs_workspace,
        )

    @staticmethod
    def _read_int(
        env: Mapping[str, str],
        key: str,
        *,
        default: int,
        minimum: int,
        maximum: Optional[int] = None,
    ) -> int:
        raw = env.get(key)
        if raw is None or not raw.strip():
            return default
        try:
            value = int(raw)
        except ValueError as exc:
            raise ConfigurationError(f"{key} must be an integer.") from exc
        if value < minimum:
            raise ConfigurationError(f"{key} must be >= {minimum}.")
        if maximum is not None and value > maximum:
            raise ConfigurationError(f"{key} must be <= {maximum}.")
        return value


__all__ = [
    "DEFAULT_DOCKER_IMAGE",
    "DEFAULT_OPENAI_MODEL",
    "RuntimeSettings",
    "SUPPORTED_SOLVER_MODES",
]
