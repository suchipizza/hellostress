# Examples

## Supported Examples

### `examples/minimal/`

Fastest end-to-end CLI example. Uses the same cantilever beam prompt as the README and writes JSON output in `mock` mode.

### `examples/beam_cantilever/`

Longer beam example with an explicit expected metrics artifact and validation link back to the analytical beam case.

### `examples/simply_supported_beam/`

Supported analytical beam example using the parser's `roller` boundary condition.

### `examples/hand_calc_comparison/`

Reuses the cantilever beam prompt and documents the hand-calculation equations behind the `mock` result.
This directory also includes a teaching notebook at `hand_calc_walkthrough.ipynb`.

### `examples/plate_pressure/`

Supported rectangular-plate pressure example with committed expected metrics.

### `examples/bracket_linear_elastic/`

Supported analytical screening workflow for an L-bracket in `mock` mode.

### `examples/plate_with_hole/`

Supported analytical screening workflow for a plate with a central hole under axial tension in `mock` mode.

## Mock-Only Geometries

Bracket and plate-with-hole examples are supported in analytical `mock` mode, but the Docker backend does not yet implement those geometries.

## How To Add A New Example

- copy a nearby example directory or start from `templates/new_example_case/`
- include `README.md`, `prompt.txt`, `run.sh`, and an expected-output artifact
- keep the command reproducible from an editable install
- add a validation note or a clear `TODO` explaining what evidence is still missing

See [docs/contributing_examples.md](contributing_examples.md) for the full checklist.
