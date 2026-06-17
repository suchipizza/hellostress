# Rectangular Plate Under Pressure

## Purpose

Supported plate example using the current rectangular-plate pressure workflow.

## Command

```bash
./examples/plate_pressure/run.sh
```

## Prompt

See [prompt.txt](prompt.txt).

## Expected Outputs

- [expected_metrics.json](expected_metrics.json)
- `output/result.json`

## Assumptions

- rectangular aluminum plate
- uniform pressure load
- `mock` mode for deterministic local output
- clamped-plate coefficient interpolation for `nu ~= 0.3`

## Validation Note

This is a reproducible supported example. For the cited square-plate reference used to anchor the clamped analytical path, see [`validation/roark_formulas/`](../../validation/roark_formulas/README.md).
