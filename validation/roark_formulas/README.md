# Roark-Style Plate Benchmark

## Purpose

This benchmark anchors the repository's `mock` clamped-plate estimate to a cited classical thin-plate reference for a uniformly loaded square plate with built-in edges.

## Reproducible Command

```bash
./validation/roark_formulas/run.sh
```

## What It Validates

- the analytical `mock` path for a clamped rectangular plate under uniform pressure
- the coefficient interpolation used by `fea_engine.utils.AnalyticalEstimator`

It does **not** validate the generated Docker `plate` backend as a classical plate-bending formulation.

## Reference Source

The committed reference case uses Table 35 from *Theory of Plates and Shells* by Timoshenko and Woinowsky-Krieger (`nu = 0.3`), as captured in the public scan linked in [source.md](source.md).

For the square clamped plate:

- center deflection coefficient: `0.00126`
- edge-moment coefficient used for max bending stress: `0.0513`

## Files

- [prompt.txt](prompt.txt)
- [reference_case.json](reference_case.json)
- [compare_square_plate_against_reference.py](compare_square_plate_against_reference.py)
- `output/comparison.json` after running the command
