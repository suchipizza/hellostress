# New Solver Adapter Template

## Goal

Use this scaffold when adding a backend without breaking the current artifact contract.

## Adapter Checklist

- accept a rendered script and `SimulationSpec`
- write stdout and stderr logs
- write `backend_status.json`
- write `backend_metadata.json`
- write or point to `results/metrics.json`
- normalize backend failures into actionable errors

## Required Tests

- successful run path
- backend failure path
- timeout or unavailable-runtime path
- artifact-bundle integrity
