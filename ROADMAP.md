# Roadmap

## v0.1 — Open-source launch readiness

- landing-page README
- minimal example and example smoke coverage
- validation runner and current benchmark evidence
- contribution docs, issue templates, and agent guidance
- CI, launch drafts, and devcontainer onboarding

## v0.2 — Benchmark suite

- extend the rectangular-plate reference set beyond the square clamped case
- add solver-comparison cases on the same supported beam prompt
- deepen mesh-convergence interpretation and comparison notes
- add at least one more cited validation case with a committed tolerance

## v0.3 — Education layer

- expand the hand-calculation notebook and teaching docs
- add a terminology and assumptions glossary
- add more beginner-friendly boundary-condition and loading examples

## v0.4 — Solver and exporter ecosystem

- make bracket support backend-real instead of screening-only
- make plate-with-hole support backend-real instead of screening-only
- add adapter validation fixtures and exporter smoke coverage

## Good First Issues

- Add a sourced rectangular-plate validation case under `validation/roark_formulas/`.
- Add interpretation guidance for the committed Docker mesh-convergence data set.
- Add a same-prompt solver comparison intake case under `validation/solver_comparison/`.
- Improve unsupported-geometry error messages with clearer extension hints.
- Add a contributor checklist for regenerating screenshot and terminal-demo assets.
- Add a workspace-policy example that demonstrates export-ready versus blocked bundles.
- Add tests for more beam boundary-condition phrasing that should still map to `fixed` or `roller`.
- Add a solver-adapter template fixture that validates expected artifact keys for a new backend.
- Add a glossary page for assumptions and common FEA terminology.
- Add a beginner-friendly notebook that explains the simply supported beam example.
- Add a rectangular plate pressure validation case derived from a committed public reference.
- Add exporter scaffolding tests once a first exporter is introduced.
