from __future__ import annotations

from pathlib import Path
from typing import Optional


class FEACopilotError(Exception):
    """Base class for recoverable application errors."""


class PromptParseError(FEACopilotError):
    """Raised when a prompt cannot be converted into a supported simulation."""


class SpecValidationError(FEACopilotError):
    """Raised when a parsed or supplied simulation spec is invalid."""


class UnsupportedSolverModeError(FEACopilotError):
    """Raised when the requested solver mode is not supported."""


class ConfigurationError(FEACopilotError):
    """Raised when runtime configuration is invalid."""


class ArtifactValidationError(FEACopilotError):
    """Raised when a persisted run artifact bundle is invalid."""


class ArtifactWorkflowError(FEACopilotError):
    """Raised when an artifact export or retention workflow cannot be completed."""


class SolverExecutionError(FEACopilotError):
    """Raised when a supported solver backend fails to execute."""

    def __init__(
        self,
        message: str,
        *,
        backend_mode: str,
        exit_code: Optional[int] = None,
        command: Optional[list[str]] = None,
        run_dir: Optional[Path] = None,
        status_path: Optional[Path] = None,
        metadata_path: Optional[Path] = None,
        stdout_path: Optional[Path] = None,
        stderr_path: Optional[Path] = None,
        stdout_excerpt: str = "",
        stderr_excerpt: str = "",
        timed_out: bool = False,
        container_id: Optional[str] = None,
        cleanup_status: str = "",
    ) -> None:
        super().__init__(message)
        self.backend_mode = backend_mode
        self.exit_code = exit_code
        self.command = command or []
        self.run_dir = run_dir
        self.status_path = status_path
        self.metadata_path = metadata_path
        self.stdout_path = stdout_path
        self.stderr_path = stderr_path
        self.stdout_excerpt = stdout_excerpt
        self.stderr_excerpt = stderr_excerpt
        self.timed_out = timed_out
        self.container_id = container_id
        self.cleanup_status = cleanup_status


class SimulationRunError(FEACopilotError):
    """Raised when the service layer cannot complete a simulation run."""

    def __init__(
        self,
        message: str,
        *,
        backend_mode: Optional[str] = None,
        run_dir: Optional[Path] = None,
        status_path: Optional[Path] = None,
        metadata_path: Optional[Path] = None,
    ) -> None:
        super().__init__(message)
        self.backend_mode = backend_mode
        self.run_dir = run_dir
        self.status_path = status_path
        self.metadata_path = metadata_path

    @classmethod
    def from_solver_error(cls, error: SolverExecutionError) -> "SimulationRunError":
        details = [f"Solver backend '{error.backend_mode}' failed"]
        if error.timed_out:
            details.append("because it timed out.")
        elif error.exit_code is not None:
            details.append(f"with exit code {error.exit_code}.")
        else:
            details.append(".")

        if error.stderr_excerpt:
            details.append(f"stderr: {error.stderr_excerpt}")
        elif error.stdout_excerpt:
            details.append(f"stdout: {error.stdout_excerpt}")

        if error.stderr_path is not None:
            details.append(f"log: {error.stderr_path}")
        elif error.stdout_path is not None:
            details.append(f"log: {error.stdout_path}")

        if error.container_id:
            details.append(f"container: {error.container_id}")
        if error.cleanup_status:
            details.append(f"cleanup: {error.cleanup_status}")
        if error.status_path is not None:
            details.append(f"status: {error.status_path}")
        if error.metadata_path is not None:
            details.append(f"metadata: {error.metadata_path}")

        return cls(
            " ".join(details),
            backend_mode=error.backend_mode,
            run_dir=error.run_dir,
            status_path=error.status_path,
            metadata_path=error.metadata_path,
        )
