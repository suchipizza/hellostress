#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

mkdir -p examples/hand_calc_comparison/output
feacopilot --prompt-file examples/hand_calc_comparison/prompt.txt --solver-mode mock --output json | tee examples/hand_calc_comparison/output/result.json
