# Benchmark Contribution Loop

## Open Linear Elasticity Benchmark

This repository is intended to accumulate small, transparent benchmark cases that are easy to rerun and inspect. Each contributed benchmark should make one problem easier to compare across prompts, solvers, or implementations.

Canonical case candidates:

- cantilever beam
- simply supported beam
- plate with hole
- L-bracket
- pressure-vessel section
- thermal expansion case
- mesh convergence case
- solver comparison case

## Every Benchmark Submission Must Include

- problem definition
- assumptions
- reference result
- mesh or discretization details
- reproducible command
- expected tolerance
- source of the analytical or benchmark reference when applicable

## Repository Locations

- user-facing examples belong in `examples/`
- validation and benchmark evidence belongs in `validation/`
- reusable contributor scaffolds belong in `templates/new_benchmark_case/`

Current committed benchmark-style assets:

- `validation/roark_formulas/`: sourced clamped square-plate analytical comparison
- `validation/mesh_convergence/`: Docker-backed cantilever beam convergence sweep

## Review Bar

- no benchmark claim without committed evidence
- no “close enough” narrative without a stated tolerance
- no opaque screenshots as the only artifact
- no benchmark that requires private data or unavailable tooling
