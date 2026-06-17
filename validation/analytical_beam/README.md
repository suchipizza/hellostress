# Analytical Beam Validation

## Purpose

Committed analytical comparison for the supported cantilever beam workflow.

## Reproducible Command

```bash
./validation/analytical_beam/run.sh
```

## Reference Equations

- `I = b h^3 / 12`
- `delta_max = F L^3 / (3 E I)`
- `sigma_max = F L (h / 2) / I`

## Expected Result

See [expected_metrics.json](expected_metrics.json).

## Assumptions

- cantilever beam
- rectangular section
- single tip point load
- linear-elastic steel

## Source Of Truth

Closed-form Euler-Bernoulli beam relations, matching the implementation in `fea_engine/utils.py`.
