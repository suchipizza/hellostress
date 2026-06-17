from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class ValidationCase:
    case_id: str
    title: str
    category: str
    command: list[str]
    docker_required: bool = False
    scaffold_only: bool = False


CASES = [
    ValidationCase(
        case_id="analytical_beam",
        title="Analytical cantilever beam comparison",
        category="analytical_beam",
        command=["./validation/analytical_beam/run.sh"],
    ),
    ValidationCase(
        case_id="cantilever_hand_calc",
        title="Public formula check for cantilever hand calculation",
        category="public_formula_checks",
        command=["./validation/public_formula_checks/cantilever_beam_hand_calc/run.sh"],
    ),
    ValidationCase(
        case_id="roark_square_plate",
        title="Roark-style clamped square plate comparison",
        category="roark_formulas",
        command=["./validation/roark_formulas/run.sh"],
    ),
    ValidationCase(
        case_id="beam_mesh_convergence",
        title="Docker-backed distributed-load beam convergence sweep",
        category="mesh_convergence",
        command=["./validation/mesh_convergence/run.sh"],
        docker_required=True,
    ),
    ValidationCase(
        case_id="solver_comparison_intake",
        title="Solver comparison intake scaffold",
        category="solver_comparison",
        command=[],
        scaffold_only=True,
    ),
]


def docker_available() -> bool:
    if shutil.which("docker") is None:
        return False
    result = subprocess.run(
        ["docker", "version"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="List or run committed FEA Copilot validation cases."
    )
    parser.add_argument("--list", action="store_true", help="List known validation cases.")
    parser.add_argument("--case", help="Run one case by case_id.")
    parser.add_argument(
        "--include-docker",
        action="store_true",
        help="Attempt Docker-backed validation cases when Docker is available.",
    )
    parser.add_argument(
        "--output",
        choices=["text", "json"],
        default="text",
        help="Render text or JSON for listing mode.",
    )
    return parser


def list_cases(output: str) -> int:
    payload = [
        {
            "case_id": case.case_id,
            "title": case.title,
            "category": case.category,
            "docker_required": case.docker_required,
            "scaffold_only": case.scaffold_only,
            "command": case.command,
        }
        for case in CASES
    ]
    if output == "json":
        json.dump(payload, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        for case in payload:
            flags: list[str] = []
            if case["docker_required"]:
                flags.append("docker")
            if case["scaffold_only"]:
                flags.append("scaffold")
            suffix = f" [{' '.join(flags)}]" if flags else ""
            print(f"{case['case_id']}: {case['title']}{suffix}")
    return 0


def select_cases(case_id: str | None, include_docker: bool) -> list[ValidationCase]:
    selected = CASES
    if case_id is not None:
        selected = [case for case in CASES if case.case_id == case_id]
        if not selected:
            raise SystemExit(f"Unknown validation case: {case_id}")

    can_run_docker = include_docker and docker_available()
    runnable: list[ValidationCase] = []
    for case in selected:
        if case.scaffold_only:
            print(f"Skipping scaffold-only case: {case.case_id}", file=sys.stderr)
            continue
        if case.docker_required and not can_run_docker:
            print(f"Skipping Docker-backed case without Docker runtime: {case.case_id}", file=sys.stderr)
            continue
        runnable.append(case)
    return runnable


def run_cases(selected: list[ValidationCase]) -> int:
    for case in selected:
        print(f"Running {case.case_id}...")
        result = subprocess.run(case.command, cwd=ROOT, check=False)
        if result.returncode != 0:
            return result.returncode
    return 0


def main() -> int:
    args = build_parser().parse_args()
    if args.list:
        return list_cases(args.output)
    selected = select_cases(args.case, args.include_docker)
    return run_cases(selected)


if __name__ == "__main__":
    raise SystemExit(main())
