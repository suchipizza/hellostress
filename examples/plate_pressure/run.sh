#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

mkdir -p examples/plate_pressure/output
feacopilot --prompt-file examples/plate_pressure/prompt.txt --solver-mode mock --output json | tee examples/plate_pressure/output/result.json
