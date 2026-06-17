# Mesh Convergence

## Purpose

This case commits a Docker-backed mesh-convergence sweep for the cantilever beam workflow so reviewers can inspect how the generated DOLFINx solution changes as mesh density increases.

## Reproducible Command

```bash
./validation/mesh_convergence/run.sh
```

## Inputs

- geometry: cantilever beam
- material: steel
- load: `150 N` downward distributed load
- mesh densities: `8`, `12`, `16`, `24`, `32`

## Outputs

- `output/beam_convergence.csv`
- `output/beam_convergence.json`
- `output/beam_convergence.png`

## Notes

- This is a backend behavior study, not a handbook validation case.
- The convergence metrics come from the generated Docker `beam` script, not the `mock` analytical estimator.
- The distributed-load cantilever variant is used because it yields a cleaner displacement trend than the point-load case in the current backend.
