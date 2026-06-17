#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

mkdir -p examples/simply_supported_beam/output
feacopilot --prompt-file examples/simply_supported_beam/prompt.txt --solver-mode mock --output json | tee examples/simply_supported_beam/output/result.json
