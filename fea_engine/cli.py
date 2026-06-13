from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Callable, Optional, Sequence, TextIO

from dotenv import load_dotenv

from .artifacts import build_bundle_summary, cleanup_run_workspace, export_artifact_bundle, load_artifact_bundle
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
        "--inspect-run-result",
        type=Path,
        help="Inspect and validate an existing run_result.json artifact bundle.",
    )
    parser.add_argument(
        "--inspect-run-dir",
        type=Path,
        help="Inspect and validate an existing run directory containing run_result.json.",
    )
    parser.add_argument(
        "--export-run-result",
        type=Path,
        help="Export an existing run_result.json artifact bundle to a zip archive.",
    )
    parser.add_argument(
        "--export-run-dir",
        type=Path,
        help="Export an existing run directory containing run_result.json to a zip archive.",
    )
    parser.add_argument(
        "--export-output",
        type=Path,
        help="Optional output zip path for artifact export workflows.",
    )
    parser.add_argument(
        "--cleanup-runs",
        action="store_true",
        help="Clean old run directories from the configured workspace.",
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        help="Workspace directory override for cleanup workflows. Defaults to FEA_RUNS_DIR or the runtime default.",
    )
    parser.add_argument(
        "--retention-days",
        type=int,
        help="Delete runs older than this many days during cleanup.",
    )
    parser.add_argument(
        "--keep-latest",
        type=int,
        default=0,
        help="Number of most recent runs to keep regardless of age during cleanup.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview cleanup deletions without removing anything.",
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
    _validate_mode_args(parser, args)

    output = stdout or sys.stdout
    errors = stderr or sys.stderr

    try:
        if args.inspect_run_result or args.inspect_run_dir:
            payload = inspect_to_payload(args.inspect_run_result, args.inspect_run_dir)
        elif args.export_run_result or args.export_run_dir:
            payload = export_to_payload(args.export_run_result, args.export_run_dir, args.export_output)
        elif args.cleanup_runs:
            settings = settings_loader() if settings_loader is not None else RuntimeSettings.from_env()
            payload = cleanup_to_payload(
                workspace=args.workspace or settings.runs_workspace,
                retention_days=args.retention_days,
                keep_latest=args.keep_latest,
                dry_run=args.dry_run,
            )
        else:
            prompt = _read_prompt(args.prompt, args.prompt_file)
            settings = settings_loader() if settings_loader is not None else RuntimeSettings.from_env()
            service = service_factory(settings) if service_factory is not None else SimulationService(settings=settings)
            result = service.run_simulation(
                prompt=prompt,
                mesh_density=args.mesh_density or settings.default_mesh_density,
                solver_mode=args.solver_mode or settings.default_solver_mode,
            )
            payload = result_to_payload(result)
    except (FEACopilotError, OSError) as exc:
        print(str(exc), file=errors)
        return 1

    if args.output == "json":
        json.dump(payload, output, indent=2)
        output.write("\n")
    elif payload.get("export_mode"):
        output.write(render_export_summary(payload))
    elif payload.get("cleanup_mode"):
        output.write(render_cleanup_summary(payload))
    elif payload.get("inspection_mode"):
        output.write(render_inspection_summary(payload))
    else:
        output.write(render_text_summary(payload))
    return 0


def _validate_mode_args(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    run_inputs = [bool(args.prompt), bool(args.prompt_file)]
    inspect_inputs = [bool(args.inspect_run_result), bool(args.inspect_run_dir)]
    export_inputs = [bool(args.export_run_result), bool(args.export_run_dir)]
    cleanup_inputs = [bool(args.cleanup_runs)]
    selected_inputs = sum(run_inputs) + sum(inspect_inputs) + sum(export_inputs) + sum(cleanup_inputs)
    if selected_inputs != 1:
        parser.error(
            "Provide exactly one primary workflow: prompt execution, inspection, export, or cleanup."
        )
    if any(inspect_inputs) or any(export_inputs) or any(cleanup_inputs):
        if args.mesh_density is not None or args.solver_mode is not None:
            parser.error("--mesh-density and --solver-mode are only valid for prompt execution.")
    if any(export_inputs) and args.cleanup_runs:
        parser.error("Export and cleanup workflows cannot be combined.")
    if any(export_inputs) and sum(export_inputs) != 1:
        parser.error("Provide exactly one of --export-run-result or --export-run-dir.")
    if any(inspect_inputs) and sum(inspect_inputs) != 1:
        parser.error("Provide exactly one of --inspect-run-result or --inspect-run-dir.")
    if args.cleanup_runs and args.retention_days is None:
        parser.error("--retention-days is required with --cleanup-runs.")
    if not args.cleanup_runs and (args.retention_days is not None or args.keep_latest != 0 or args.dry_run or args.workspace):
        parser.error("--retention-days, --keep-latest, --dry-run, and --workspace are only valid with --cleanup-runs.")
    if not any(export_inputs) and args.export_output is not None:
        parser.error("--export-output is only valid with export workflows.")


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


def inspect_to_payload(
    inspect_run_result: Optional[Path],
    inspect_run_dir: Optional[Path],
) -> dict[str, object]:
    run_result_path = inspect_run_result
    if inspect_run_dir is not None:
        run_result_path = inspect_run_dir / "run_result.json"
    if run_result_path is None:
        raise AssertionError("Inspection validation should happen in argparse.")
    bundle = load_artifact_bundle(run_result_path)
    summary = build_bundle_summary(bundle)
    summary["inspection_mode"] = True
    return summary


def export_to_payload(
    export_run_result: Optional[Path],
    export_run_dir: Optional[Path],
    export_output: Optional[Path],
) -> dict[str, object]:
    run_result_path = export_run_result
    if export_run_dir is not None:
        run_result_path = export_run_dir / "run_result.json"
    if run_result_path is None:
        raise AssertionError("Export validation should happen in argparse.")
    bundle = load_artifact_bundle(run_result_path)
    archive_path = export_artifact_bundle(run_result_path, output_path=export_output)
    return {
        "export_mode": True,
        "archive_path": str(archive_path),
        "run_result_path": str(bundle.run_result_path),
        "run_dir": bundle.run_result["artifacts"]["run_dir"],
        "backend_mode": bundle.run_result["backend_mode"],
        "status": bundle.run_result["status"],
    }


def cleanup_to_payload(
    *,
    workspace: Path,
    retention_days: Optional[int],
    keep_latest: int,
    dry_run: bool,
) -> dict[str, object]:
    if retention_days is None:
        raise AssertionError("Cleanup validation should happen in argparse.")
    result = cleanup_run_workspace(
        workspace,
        retention_days=retention_days,
        keep_latest=keep_latest,
        dry_run=dry_run,
    )
    return {
        "cleanup_mode": True,
        "workspace": str(result.workspace),
        "retention_days": result.retention_days,
        "keep_latest": result.keep_latest,
        "dry_run": result.dry_run,
        "deleted_runs": [str(path) for path in result.deleted_runs],
        "retained_runs": [str(path) for path in result.retained_runs],
        "skipped_paths": [str(path) for path in result.skipped_paths],
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


def render_inspection_summary(payload: dict[str, object]) -> str:
    compatibility = payload["compatibility"]
    diagnostics = payload["diagnostics"]
    paths = payload["paths"]
    warnings = payload["warnings"]
    lines = [
        "Inspection: valid",
        f"Schema version: {payload['schema_version']}",
        f"Compatibility supported: {compatibility['supported']}",
        f"Supported schema range: {compatibility['minimum_supported_schema_version']}..{compatibility['maximum_supported_schema_version']}",
        f"Run status: {payload['status']}",
        f"Backend mode: {payload['backend_mode']}",
        f"Backend status: {payload['backend_status']}",
        f"Metrics source: {payload['metrics_source']}",
        f"Fallback used: {payload['fallback_used']}",
        "Diagnostics:",
        f"  all_referenced_files_present: {diagnostics['all_referenced_files_present']}",
        f"  all_embedded_payloads_consistent: {diagnostics['all_embedded_payloads_consistent']}",
        f"  metrics_present: {diagnostics['metrics_present']}",
        f"  generated_file_count: {diagnostics['generated_file_count']}",
        "Paths:",
        f"  run_result: {paths['run_result_path']}",
        f"  backend_status: {paths['backend_status_path']}",
        f"  backend_metadata: {paths['backend_metadata_path']}",
        f"  run_dir: {paths['run_dir']}",
        f"  results_dir: {paths['results_dir']}",
        f"  script: {paths['script_path']}",
        f"  metrics: {paths['metrics_path']}",
        f"  stdout: {paths['stdout_path']}",
        f"  stderr: {paths['stderr_path']}",
    ]
    if warnings:
        lines.append("Warnings:")
        lines.extend(f"  - {warning}" for warning in warnings)
    else:
        lines.append("Warnings: none")
    return "\n".join(lines) + "\n"


def render_export_summary(payload: dict[str, object]) -> str:
    lines = [
        "Export: completed",
        f"Run status: {payload['status']}",
        f"Backend mode: {payload['backend_mode']}",
        f"Run result: {payload['run_result_path']}",
        f"Run dir: {payload['run_dir']}",
        f"Archive: {payload['archive_path']}",
    ]
    return "\n".join(lines) + "\n"


def render_cleanup_summary(payload: dict[str, object]) -> str:
    lines = [
        "Cleanup: completed",
        f"Workspace: {payload['workspace']}",
        f"Retention days: {payload['retention_days']}",
        f"Keep latest: {payload['keep_latest']}",
        f"Dry run: {payload['dry_run']}",
        f"Deleted runs: {len(payload['deleted_runs'])}",
        f"Retained runs: {len(payload['retained_runs'])}",
        f"Skipped paths: {len(payload['skipped_paths'])}",
    ]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
