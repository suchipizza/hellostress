#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

mkdir -p examples/minimal/output
feacopilot --prompt-file examples/minimal/prompt.txt --solver-mode mock --output json | tee examples/minimal/output/result.json
