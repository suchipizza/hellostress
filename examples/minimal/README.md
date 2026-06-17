# Minimal Example

## Purpose

Smallest supported CLI example for a fresh clone.

## Command

```bash
./examples/minimal/run.sh
```

## Prompt

See [prompt.txt](prompt.txt).

## Expected Output

See [expected_output.md](expected_output.md).

## Assumptions

- linear-elastic steel beam
- cantilever boundary condition
- point load at the tip
- `mock` solver mode

## Validation Note

Matches the same analytical beam assumptions documented in [`validation/analytical_beam/`](../../validation/analytical_beam/README.md).
