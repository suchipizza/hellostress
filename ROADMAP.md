# Roadmap

## Current Priorities

- keep the beam and rectangular-plate workflows stable and reproducible
- expand validation coverage before expanding solver scope
- make extension points for new geometries and adapters easier to contribute safely
- prepare the repository for a public open-source launch with credible examples and issue intake

## Planned Workstreams

### Validation

- extend the sourced rectangular-plate reference set beyond the square clamped case
- add interpretation guidance for the committed Docker-backed mesh convergence data set
- add solver-comparison intake for the same beam case across backends

### Examples

- turn the bracket scaffold into a real supported workflow
- add a Docker-backed follow-through for the simply supported beam teaching example
- add a pressure-vessel or thermal-expansion benchmark only when a validated reference is committed

### Tooling

- improve CLI error messages for unsupported prompt geometry
- add docs checks or lightweight link validation in CI
- add optional devcontainer or Codespaces setup for faster onboarding

## Good First Issues

- Add `examples/simply_supported_beam/` with `prompt.txt`, `run.sh`, README, and expected outputs.
- Add a sourced validation case under `validation/roark_formulas/` for a rectangular plate example with a committed tolerance.
- Add a script that generates a mesh-convergence CSV and plot for the cantilever beam Docker path.
- Improve the unsupported-geometry error so bracket prompts fail with a more actionable extension hint.
- Add a teaching notebook that walks through the hand-calculation beam comparison already documented in the repo.
- Add a contributor checklist for screenshot or terminal-demo regeneration in `assets/`.
- Add a workspace-policy example that demonstrates export-ready versus blocked artifact bundles.
- Add a `docs/assumptions.md` page that centralizes material, load, and solver assumptions from scattered docs.
- Add tests for additional beam boundary-condition phrasing that should still map to `fixed` or `roller`.
- Add a solver-adapter template test fixture that validates expected artifact keys for a new backend.
- Add a `plate_under_pressure` validation case with committed expected metrics derived from the current analytical estimator.
- Add a lightweight docs lint step that fails CI on missing local markdown links.
