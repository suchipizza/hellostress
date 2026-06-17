# Validation

## Validation Philosophy

This repository distinguishes between:

- committed comparisons with a reproducible command and expected result
- scaffolds for future benchmarks that are not yet evidence-backed

If a reference result, tolerance, or source is missing, the case should be marked `TODO` instead of described as validated.

## Current Validation Assets

### `validation/analytical_beam/`

This is the strongest committed validation path today. It uses the same cantilever beam assumptions as the `mock` analytical estimator:

- cantilever boundary condition
- point load at the tip
- rectangular section
- small-deflection linear-elastic assumptions

The closed-form quantities used by the current estimator are:

- `I = b h^3 / 12`
- `delta_max = F L^3 / (3 E I)`
- `sigma_max = F L (h / 2) / I`

### `validation/public_formula_checks/`

This category holds public hand-calculation or formula-derived checks. The current cantilever beam case compares the `mock` output to the same readable hand calculation documented in the teaching example.

### `validation/roark_formulas/`

This directory now contains a cited square-plate comparison for the `mock` clamped-plate estimator. It validates the analytical path, not the Docker backend, because the generated `plate` script is not a classical Kirchhoff plate-bending model.

### `validation/mesh_convergence/`

This directory now contains a Docker-backed cantilever beam convergence study with committed CSV, JSON, and plot outputs.

### `validation/solver_comparison/`

This is intentionally still an intake scaffold. It should not be described as a finished benchmark until a same-prompt cross-backend comparison command and interpretation note are committed.

## Running Validation

```bash
make validate
python3 tools/run_validation.py --list
```

## Required Evidence For New Validation Claims

- problem definition
- geometry and loading assumptions
- reference result
- tolerance
- command to reproduce the repository result
- source of analytical or benchmark truth when applicable
