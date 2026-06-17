from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CASE_DIR = ROOT / "validation" / "roark_formulas"
REFERENCE_PATH = CASE_DIR / "reference_case.json"
PROMPT_PATH = CASE_DIR / "prompt.txt"
OUTPUT_DIR = CASE_DIR / "output"
RESULT_PATH = OUTPUT_DIR / "result.json"
COMPARISON_PATH = OUTPUT_DIR / "comparison.json"


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with REFERENCE_PATH.open("r", encoding="utf-8") as handle:
        reference = json.load(handle)

    completed = subprocess.run(
        [
            "feacopilot",
            "--prompt-file",
            str(PROMPT_PATH),
            "--solver-mode",
            "mock",
            "--output",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    RESULT_PATH.write_text(completed.stdout, encoding="utf-8")
    payload = json.loads(completed.stdout)
    metrics = payload["metrics"]

    deflection_error = abs(metrics["max_deflection"] - reference["expected_deflection_m"]) / reference["expected_deflection_m"]
    stress_error = abs(metrics["max_stress"] - reference["expected_stress_pa"]) / reference["expected_stress_pa"]

    comparison = {
        "source": reference["source"],
        "status": payload["status"],
        "solver_mode": payload["solver_mode"],
        "reference": {
            "expected_deflection_m": reference["expected_deflection_m"],
            "expected_stress_pa": reference["expected_stress_pa"],
            "tolerance_relative": reference["tolerance_relative"],
        },
        "observed": metrics,
        "relative_error": {
            "max_deflection": deflection_error,
            "max_stress": stress_error,
        },
        "within_tolerance": {
            "max_deflection": deflection_error <= reference["tolerance_relative"],
            "max_stress": stress_error <= reference["tolerance_relative"],
        },
    }
    COMPARISON_PATH.write_text(json.dumps(comparison, indent=2), encoding="utf-8")
    print(json.dumps(comparison, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
