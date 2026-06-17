# Assumptions

## Physics

- linear elasticity only
- small strain
- isotropic material properties
- no contact, plasticity, dynamics, fatigue, or thermal coupling in the currently supported workflows

## Geometry And Load Scope

- beam prompts require a span, section size, and a load with units
- rectangular plate prompts require plan dimensions, thickness, and a pressure load
- bracket and plate-with-hole prompts are supported only as analytical `mock`-mode screening workflows

## Backend Scope

- `mock` mode is deterministic and fast, intended for smoke tests, hand-calculation comparison, and analytical screening
- Docker mode is the intended path for generated DOLFINx execution of beam and rectangular-plate cases
- host-local solver execution is intentionally unsupported

## Validation Language

- a committed case is only described as validated when the command, expected result, tolerance, and reference source are all committed
- mesh-convergence plots are evidence, not proof of solver correctness on their own
- screening examples should state approximation limits explicitly rather than borrowing the language of full backend support
