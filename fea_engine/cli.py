from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Callable, Optional, Sequence, TextIO

from dotenv import load_dotenv

from .artifacts import (
    audit_run_workspace,
    build_bundle_summary,
    build_cleanup_summary,
    build_workspace_export_summary,
    build_workspace_policy_summary,
    cleanup_run_workspace,
    export_run_workspace,
    export_artifact_bundle,
    load_artifact_bundle,
)
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
        "--export-workspace-runs",
        action="store_true",
        help="Export all workspace runs that pass export policy into an output directory.",
    )
    parser.add_argument(
        "--export-output-dir",
        type=Path,
        help="Output directory for workspace bulk export archives.",
    )
    parser.add_argument(
        "--allow-degraded-export",
        action="store_true",
        help="Override export policy and package a bundle even when the inspection quality gate fails.",
    )
    parser.add_argument(
        "--cleanup-runs",
        action="store_true",
        help="Clean old run directories from the configured workspace.",
    )
    parser.add_argument(
        "--report-workspace-policy",
        action="store_true",
        help="Audit run directories in a workspace and report policy readiness without modifying anything.",
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        help="Workspace directory override for workspace audit and cleanup workflows. Defaults to FEA_RUNS_DIR or the runtime default.",
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
            payload = export_to_payload(
                args.export_run_result,
                args.export_run_dir,
                args.export_output,
                allow_degraded_export=args.allow_degraded_export,
            )
        elif args.export_workspace_runs:
            settings = settings_loader() if settings_loader is not None else RuntimeSettings.from_env()
            payload = export_workspace_to_payload(
                workspace=args.workspace or settings.runs_workspace,
                output_dir=args.export_output_dir,
                allow_degraded_export=args.allow_degraded_export,
            )
        elif args.cleanup_runs:
            settings = settings_loader() if settings_loader is not None else RuntimeSettings.from_env()
            payload = cleanup_to_payload(
                workspace=args.workspace or settings.runs_workspace,
                retention_days=args.retention_days,
                keep_latest=args.keep_latest,
                dry_run=args.dry_run,
            )
        elif args.report_workspace_policy:
            settings = settings_loader() if settings_loader is not None else RuntimeSettings.from_env()
            payload = workspace_policy_to_payload(
                workspace=args.workspace or settings.runs_workspace,
                retention_days=args.retention_days,
                keep_latest=args.keep_latest,
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
    elif payload.get("workspace_export_mode"):
        output.write(render_workspace_export_summary(payload))
    elif payload.get("cleanup_mode"):
        output.write(render_cleanup_summary(payload))
    elif payload.get("workspace_policy_mode"):
        output.write(render_workspace_policy_summary(payload))
    elif payload.get("inspection_mode"):
        output.write(render_inspection_summary(payload))
    else:
        output.write(render_text_summary(payload))
    return 0


def _validate_mode_args(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    run_inputs = [bool(args.prompt), bool(args.prompt_file)]
    inspect_inputs = [bool(args.inspect_run_result), bool(args.inspect_run_dir)]
    export_inputs = [bool(args.export_run_result), bool(args.export_run_dir)]
    workspace_export_inputs = [bool(args.export_workspace_runs)]
    cleanup_inputs = [bool(args.cleanup_runs)]
    report_inputs = [bool(args.report_workspace_policy)]
    workspace_mode_selected = any(cleanup_inputs) or any(report_inputs) or any(workspace_export_inputs)
    selected_inputs = (
        sum(run_inputs)
        + sum(inspect_inputs)
        + sum(export_inputs)
        + sum(workspace_export_inputs)
        + sum(cleanup_inputs)
        + sum(report_inputs)
    )
    if selected_inputs != 1:
        parser.error(
            "Provide exactly one primary workflow: prompt execution, inspection, export, workspace export, workspace audit, or cleanup."
        )
    if any(inspect_inputs) or any(export_inputs) or workspace_mode_selected:
        if args.mesh_density is not None or args.solver_mode is not None:
            parser.error("--mesh-density and --solver-mode are only valid for prompt execution.")
    if any(export_inputs) and args.cleanup_runs:
        parser.error("Export and cleanup workflows cannot be combined.")
    if any(export_inputs) and args.report_workspace_policy:
        parser.error("Export and workspace audit workflows cannot be combined.")
    if any(export_inputs) and args.export_workspace_runs:
        parser.error("Single-run export and workspace export workflows cannot be combined.")
    if any(export_inputs) and sum(export_inputs) != 1:
        parser.error("Provide exactly one of --export-run-result or --export-run-dir.")
    if any(inspect_inputs) and sum(inspect_inputs) != 1:
        parser.error("Provide exactly one of --inspect-run-result or --inspect-run-dir.")
    if args.cleanup_runs and args.retention_days is None:
        parser.error("--retention-days is required with --cleanup-runs.")
    if args.report_workspace_policy and args.retention_days is None:
        parser.error("--retention-days is required with --report-workspace-policy.")
    if args.export_workspace_runs and args.export_output_dir is None:
        parser.error("--export-output-dir is required with --export-workspace-runs.")
    if not workspace_mode_selected and (args.retention_days is not None or args.keep_latest != 0 or args.workspace):
        parser.error("--retention-days, --keep-latest, and --workspace are only valid with workspace audit or cleanup.")
    if args.export_workspace_runs and args.retention_days is not None:
        parser.error("--retention-days is not used with --export-workspace-runs.")
    if args.export_workspace_runs and args.keep_latest != 0:
        parser.error("--keep-latest is not used with --export-workspace-runs.")
    if not args.cleanup_runs and args.dry_run:
        parser.error("--dry-run is only valid with --cleanup-runs.")
    if not any(export_inputs) and args.export_output is not None:
        parser.error("--export-output is only valid with export workflows.")
    if not args.export_workspace_runs and args.export_output_dir is not None:
        parser.error("--export-output-dir is only valid with --export-workspace-runs.")
    if not (any(export_inputs) or args.export_workspace_runs) and args.allow_degraded_export:
        parser.error("--allow-degraded-export is only valid with export workflows.")


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
    *,
    allow_degraded_export: bool,
) -> dict[str, object]:
    run_result_path = export_run_result
    if export_run_dir is not None:
        run_result_path = export_run_dir / "run_result.json"
    if run_result_path is None:
        raise AssertionError("Export validation should happen in argparse.")
    bundle = load_artifact_bundle(run_result_path)
    export_result = export_artifact_bundle(
        run_result_path,
        output_path=export_output,
        allow_degraded=allow_degraded_export,
    )
    return {
        "export_mode": True,
        "archive_path": str(export_result.archive_path),
        "archive_sha256": export_result.archive_sha256,
        "manifest_name": export_result.manifest_name,
        "manifest": export_result.manifest,
        "policy": export_result.policy,
        "policy_override_used": export_result.policy_override_used,
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
    payload = {
        "cleanup_mode": True,
    }
    payload.update(build_cleanup_summary(result))
    return payload


def export_workspace_to_payload(
    *,
    workspace: Path,
    output_dir: Optional[Path],
    allow_degraded_export: bool,
) -> dict[str, object]:
    if output_dir is None:
        raise AssertionError("Workspace export validation should happen in argparse.")
    result = export_run_workspace(
        workspace,
        output_dir=output_dir,
        allow_degraded=allow_degraded_export,
    )
    payload = {
        "workspace_export_mode": True,
    }
    payload.update(build_workspace_export_summary(result))
    return payload


def workspace_policy_to_payload(
    *,
    workspace: Path,
    retention_days: Optional[int],
    keep_latest: int,
) -> dict[str, object]:
    if retention_days is None:
        raise AssertionError("Workspace policy validation should happen in argparse.")
    result = audit_run_workspace(
        workspace,
        retention_days=retention_days,
        keep_latest=keep_latest,
    )
    payload = {
        "workspace_policy_mode": True,
    }
    payload.update(build_workspace_policy_summary(result))
    return payload


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
    triage = payload["triage"]
    policy = payload["policy"]
    backend_context = triage["backend_context"]
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
        f"Triage severity: {triage['severity']}",
        "Policy:",
        f"  quality_gate_passed: {policy['quality_gate']['passed']}",
        f"  export_allowed: {policy['export']['allowed']}",
        f"  promotion_allowed: {policy['promotion']['allowed']}",
        "Diagnostics:",
        f"  all_referenced_files_present: {diagnostics['all_referenced_files_present']}",
        f"  all_embedded_payloads_consistent: {diagnostics['all_embedded_payloads_consistent']}",
        f"  metrics_present: {diagnostics['metrics_present']}",
        f"  generated_file_count: {diagnostics['generated_file_count']}",
        "Backend context:",
        f"  exit_code: {backend_context['exit_code']}",
        f"  timed_out: {backend_context['timed_out']}",
        f"  container_status: {backend_context['container_status']}",
        f"  cleanup_status: {backend_context['cleanup_status']}",
        f"  stdout_excerpt: {backend_context['stdout_excerpt'] or '(empty)'}",
        f"  stderr_excerpt: {backend_context['stderr_excerpt'] or '(empty)'}",
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
    if triage["issues"]:
        lines.append("Issues:")
        lines.extend(
            f"  - [{issue['severity']}] {issue['code']}: {issue['message']}"
            + (f" Path: {issue['path']}" if issue.get("path") else "")
            for issue in triage["issues"]
        )
    else:
        lines.append("Issues: none")
    if triage["suggested_actions"]:
        lines.append("Suggested actions:")
        lines.extend(f"  - {action}" for action in triage["suggested_actions"])
    if warnings:
        lines.append("Warnings:")
        lines.extend(f"  - {warning}" for warning in warnings)
    else:
        lines.append("Warnings: none")
    return "\n".join(lines) + "\n"


def render_export_summary(payload: dict[str, object]) -> str:
    policy = payload["policy"]
    lines = [
        "Export: completed",
        f"Run status: {payload['status']}",
        f"Backend mode: {payload['backend_mode']}",
        f"Quality gate passed: {policy['quality_gate']['passed']}",
        f"Export policy override used: {payload['policy_override_used']}",
        f"Run result: {payload['run_result_path']}",
        f"Run dir: {payload['run_dir']}",
        f"Archive: {payload['archive_path']}",
        f"Archive sha256: {payload['archive_sha256']}",
        f"Manifest: {payload['manifest_name']}",
        f"Manifest file count: {payload['manifest']['file_count']}",
    ]
    return "\n".join(lines) + "\n"


def render_cleanup_summary(payload: dict[str, object]) -> str:
    summary = payload["summary"]
    lines = [
        "Cleanup: completed",
        f"Workspace: {payload['workspace']}",
        f"Retention days: {payload['retention_days']}",
        f"Keep latest: {payload['keep_latest']}",
        f"Dry run: {payload['dry_run']}",
        f"Discovered runs: {summary['discovered_count']}",
        f"Deleted runs: {summary['deleted_count']}",
        f"Retained runs: {summary['retained_count']}",
        f"Skipped paths: {summary['skipped_count']}",
    ]
    return "\n".join(lines) + "\n"


def render_workspace_export_summary(payload: dict[str, object]) -> str:
    summary = payload["summary"]
    exported_lines = [
        f"  - {record['run_name']}: {record['archive_path']}"
        + (" override-used" if record["policy_override_used"] else "")
        for record in payload["runs"]
        if record["outcome"] == "exported"
    ]
    blocked_lines = [
        f"  - {record['run_name']}: {record['reason']}"
        for record in payload["runs"]
        if record["outcome"] in {"blocked", "failed"}
    ]
    lines = [
        "Workspace export: completed",
        f"Workspace: {payload['workspace']}",
        f"Output dir: {payload['output_dir']}",
        f"Allow degraded export: {payload['allow_degraded_export']}",
        f"Discovered paths: {summary['discovered_count']}",
        f"Exported runs: {summary['exported_count']}",
        f"Blocked runs: {summary['blocked_count']}",
        f"Skipped paths: {summary['skipped_count']}",
        f"Failed runs: {summary['failed_count']}",
        f"Override exports: {summary['override_export_count']}",
    ]
    if exported_lines:
        lines.append("Exported archives:")
        lines.extend(exported_lines)
    else:
        lines.append("Exported archives: none")
    if blocked_lines:
        lines.append("Blocked or failed:")
        lines.extend(blocked_lines)
    if payload["skipped_path_names"]:
        lines.append(f"Skipped path names: {', '.join(payload['skipped_path_names'])}")
    return "\n".join(lines) + "\n"


def render_workspace_policy_summary(payload: dict[str, object]) -> str:
    summary = payload["summary"]
    flagged_lines: list[str] = []
    for record in payload["runs"]:
        reasons: list[str] = []
        if not record["valid"]:
            reasons.append("invalid")
        elif record["manual_review_required"]:
            reasons.append(f"manual-review:{record['triage_severity']}")
        if record["retention_candidate"]:
            reasons.append("retention-candidate")
        if reasons:
            issue_codes = ",".join(record["issue_codes"])
            detail = f" issue_codes={issue_codes}" if issue_codes else ""
            flagged_lines.append(f"  - {record['run_name']}: {', '.join(reasons)}{detail}")

    lines = [
        "Workspace policy report: completed",
        f"Workspace: {payload['workspace']}",
        f"Retention days: {payload['retention_days']}",
        f"Keep latest: {payload['keep_latest']}",
        f"Discovered paths: {summary['discovered_count']}",
        f"Valid runs: {summary['valid_run_count']}",
        f"Invalid runs: {summary['invalid_run_count']}",
        f"Skipped paths: {summary['skipped_path_count']}",
        f"Export ready: {summary['export_ready_count']}",
        f"Promotion ready: {summary['promotion_ready_count']}",
        f"Manual review required: {summary['manual_review_count']}",
        f"Retention candidates: {summary['retention_candidate_count']}",
    ]
    if flagged_lines:
        lines.append("Flagged runs:")
        lines.extend(flagged_lines)
    else:
        lines.append("Flagged runs: none")
    if payload["skipped_path_names"]:
        lines.append(f"Skipped path names: {', '.join(payload['skipped_path_names'])}")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
