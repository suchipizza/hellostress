#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

mkdir -p examples/beam_cantilever/output
feacopilot --prompt-file examples/beam_cantilever/prompt.txt --solver-mode mock --output json | tee examples/beam_cantilever/output/result.json
