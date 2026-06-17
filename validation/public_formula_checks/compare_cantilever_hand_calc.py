from __future__ import annotations

import json
import subprocess
from pathlib import Path


CASE_DIR = Path(__file__).resolve().parent / "cantilever_beam_hand_calc"
OUTPUT_DIR = CASE_DIR / "output"
PROMPT_PATH = CASE_DIR / "prompt.txt"
EXPECTED_PATH = CASE_DIR / "expected_metrics.json"


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    result = subprocess.run(
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
    payload = json.loads(result.stdout)
    (OUTPUT_DIR / "result.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    expected = json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))
    observed_deflection = float(payload["metrics"]["max_deflection"])
    observed_stress = float(payload["metrics"]["max_stress"])
    deflection_error = abs(observed_deflection - expected["expected_deflection_m"]) / expected["expected_deflection_m"]
    stress_error = abs(observed_stress - expected["expected_stress_pa"]) / expected["expected_stress_pa"]
    comparison = {
        "status": "completed",
        "reference": expected,
        "observed": {
            "max_deflection": observed_deflection,
            "max_stress": observed_stress,
        },
        "relative_error": {
            "max_deflection": deflection_error,
            "max_stress": stress_error,
        },
        "within_tolerance": {
            "max_deflection": deflection_error <= expected["tolerance_relative"],
            "max_stress": stress_error <= expected["tolerance_relative"],
        },
    }
    (OUTPUT_DIR / "comparison.json").write_text(json.dumps(comparison, indent=2), encoding="utf-8")

    if not all(comparison["within_tolerance"].values()):
        raise SystemExit("Hand-calculation validation exceeded tolerance.")


if __name__ == "__main__":
    main()
