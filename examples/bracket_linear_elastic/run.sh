#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

mkdir -p examples/bracket_linear_elastic/output
feacopilot --prompt-file examples/bracket_linear_elastic/prompt.txt --solver-mode mock --output json | tee examples/bracket_linear_elastic/output/result.json
