# Cantilever Beam

## Purpose

Reference beam example with a larger load and explicit expected metrics.

## Command

```bash
./examples/beam_cantilever/run.sh
```

## Prompt

See [prompt.txt](prompt.txt).

## Expected Outputs

- [expected_metrics.json](expected_metrics.json)
- `output/result.json`

## Assumptions

- rectangular steel beam
- cantilever boundary condition
- tip point load
- `mock` mode for deterministic local results

## Validation Note

This case is consistent with the same beam formulas described in [`validation/analytical_beam/`](../../validation/analytical_beam/README.md).
