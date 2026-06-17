# Cantilever Beam Hand-Calculation Check

## Purpose

Validate the current cantilever beam `mock` result against a readable hand calculation, not just an implementation-level expected JSON file.

## Command

```bash
./validation/public_formula_checks/cantilever_beam_hand_calc/run.sh
```

## Assumptions

- Euler-Bernoulli cantilever beam
- rectangular section
- small strain, linear elasticity
- isotropic steel with `E = 200 GPa`

## Reference

See [reference_solution.md](reference_solution.md).
