#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

mkdir -p examples/plate_with_hole/output
feacopilot --prompt-file examples/plate_with_hole/prompt.txt --solver-mode mock --output json | tee examples/plate_with_hole/output/result.json
