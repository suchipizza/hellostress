#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

./examples/minimal/run.sh >/dev/null
./examples/beam_cantilever/run.sh >/dev/null
./examples/simply_supported_beam/run.sh >/dev/null
./examples/plate_pressure/run.sh >/dev/null
./examples/hand_calc_comparison/run.sh >/dev/null
./examples/plate_with_hole/run.sh >/dev/null
./examples/bracket_linear_elastic/run.sh >/dev/null
