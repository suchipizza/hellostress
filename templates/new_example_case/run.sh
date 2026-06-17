#!/usr/bin/env bash
set -euo pipefail

mkdir -p output
feacopilot --prompt-file prompt.txt --solver-mode mock --output json | tee output/result.json
