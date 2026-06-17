# Hand-Calculation Comparison

## Purpose

Show the current cantilever beam `mock` result alongside the closed-form equations it comes from.

## Command

```bash
./examples/hand_calc_comparison/run.sh
```

## Prompt

See [prompt.txt](prompt.txt).

## Expected Outputs

- [expected_metrics.json](expected_metrics.json)
- [hand_calc.md](hand_calc.md)
- [hand_calc_walkthrough.ipynb](hand_calc_walkthrough.ipynb)

## Assumptions

- Euler-Bernoulli cantilever beam
- rectangular section
- small strain, linear elasticity
- steel with `E = 200 GPa`

## Validation Note

This example is a readable counterpart to [`validation/analytical_beam/`](../../validation/analytical_beam/README.md).
