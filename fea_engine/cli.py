from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Callable, Optional, Sequence, TextIO

from dotenv import load_dotenv

from .errors import FEACopilotError
from .presentation import spec_to_display_dict
from .service import SimulationRunResult, SimulationService
from .settings import RuntimeSettings


ServiceFactory = Callable[[RuntimeSettings], SimulationService]
SettingsLoader = Callable[[], RuntimeSettings]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="feacopilot",
        description="Run a supported FEA Copilot prompt without launching Streamlit.",
    )
    parser.add_argument("--prompt", help="Simulation prompt to execute.")
    parser.add_argument(
        "--prompt-file",
        type=Path,
        help="Path to a file containing the simulation prompt.",
    )
    parser.add_argument(
        "--mesh-density",
        type=int,
        help="Mesh density override. Defaults to FEA_DEFAULT_MESH_DENSITY or 32.",
    )
    parser.add_argument(
        "--solver-mode",
        choices=["mock", "docker", "auto"],
        help="Solver mode override. Defaults to FEA_DEFAULT_SOLVER_MODE or mock.",
    )
    parser.add_argument(
        "--output",
        choices=["text", "json"],
        default="text",
        help="Render a concise text summary or structured JSON.",
    )
    return parser


def main(
    argv: Optional[Sequence[str]] = None,
    *,
    service_factory: Optional[ServiceFactory] = None,
    settings_loader: Optional[SettingsLoader] = None,
    stdout: Optional[TextIO] = None,
    stderr: Optional[TextIO] = None,
) -> int:
    load_dotenv()
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    if bool(args.prompt) == bool(args.prompt_file):
        parser.error("Provide exactly one of --prompt or --prompt-file.")

    output = stdout or sys.stdout
    errors = stderr or sys.stderr

    try:
        prompt = _read_prompt(args.prompt, args.prompt_file)
        settings = settings_loader() if settings_loader is not None else RuntimeSettings.from_env()
        service = service_factory(settings) if service_factory is not None else SimulationService(settings=settings)
        result = service.run_simulation(
            prompt=prompt,
            mesh_density=args.mesh_density or settings.default_mesh_density,
            solver_mode=args.solver_mode or settings.default_solver_mode,
        )
    except (FEACopilotError, OSError) as exc:
        print(str(exc), file=errors)
        return 1

    payload = result_to_payload(result)
    if args.output == "json":
        json.dump(payload, output, indent=2)
        output.write("\n")
    else:
        output.write(render_text_summary(payload))
    return 0


def _read_prompt(prompt: Optional[str], prompt_file: Optional[Path]) -> str:
    if prompt is not None:
        return prompt
    if prompt_file is None:
        raise AssertionError("Prompt validation should happen in argparse.")
    return prompt_file.read_text(encoding="utf-8").strip()


def result_to_payload(result: SimulationRunResult) -> dict[str, object]:
    return {
        "status": result.status,
        "solver_mode": result.solver_mode,
        "backend_status": result.artifacts.backend_status,
        "metrics_source": result.metrics_source,
        "fallback_used": result.fallback_used,
        "warnings": result.warnings,
        "summary": result.summary,
        "metrics": result.metrics,
        "spec": spec_to_display_dict(result.spec),
        "artifacts": {
            "run_dir": str(result.artifacts.run_dir),
            "result_schema_path": str(result.result_schema_path),
            "script_path": str(result.artifacts.script_path),
            "metrics_path": str(result.artifacts.metrics_path),
            "backend_status_path": str(result.artifacts.backend_status_path),
            "backend_metadata_path": str(result.artifacts.backend_metadata_path),
        },
    }


def render_text_summary(payload: dict[str, object]) -> str:
    metrics = payload["metrics"]
    warnings = payload["warnings"]
    artifacts = payload["artifacts"]
    lines = [
        f"Status: {payload['status']}",
        f"Solver mode: {payload['solver_mode']}",
        f"Backend status: {payload['backend_status']}",
        f"Metrics source: {payload['metrics_source']}",
        f"Fallback used: {payload['fallback_used']}",
        f"Summary: {payload['summary']}",
        f"Max deflection (m): {metrics.get('max_deflection', 0.0):.6e}",
        f"Max stress (Pa): {metrics.get('max_stress', 0.0):.6e}",
        "Artifacts:",
        f"  run_dir: {artifacts['run_dir']}",
        f"  run_result: {artifacts['result_schema_path']}",
        f"  script: {artifacts['script_path']}",
        f"  metrics: {artifacts['metrics_path']}",
        f"  backend_status: {artifacts['backend_status_path']}",
        f"  backend_metadata: {artifacts['backend_metadata_path']}",
    ]
    if warnings:
        lines.append("Warnings:")
        lines.extend(f"  - {warning}" for warning in warnings)
    else:
        lines.append("Warnings: none")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
