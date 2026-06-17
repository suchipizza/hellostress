#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

mkdir -p validation/analytical_beam/output
feacopilot --prompt-file validation/analytical_beam/prompt.txt --solver-mode mock --output json | tee validation/analytical_beam/output/result.json
