# FEA Copilot

[![CI workflow](https://img.shields.io/badge/CI-GitHub%20Actions%20workflow%20included-0A7E8C)](.github/workflows/ci.yml)
[![Tests](https://img.shields.io/badge/tests-pytest%20suite-informational)](tests)
[![Release](https://img.shields.io/badge/release-v0.3.0-informational)](CHANGELOG.md)
[![Docs](https://img.shields.io/badge/docs-in%20repo-1F6FEB)](docs/quickstart.md)
[![License](https://img.shields.io/badge/license-Apache--2.0-success)](LICENSE)

FEA Copilot turns narrow, linear-elastic mechanical-analysis prompts into transparent, reproducible engineering workflows for first-pass beam, plate, bracket, and plate-with-hole checks.

Current executable scope: beams and rectangular plates in `mock` and Docker modes, plus analytical `mock`-mode screening workflows for brackets and plates with central holes.

![FEA Copilot demo](assets/demo.gif)

## Why This Matters Now

Mechanical engineers still spend time rebuilding the same first-pass checks from scratch: parse the problem, restate assumptions, estimate loads, wire a solver, then explain what happened. FEA Copilot packages that loop into a reproducible CLI and app workflow with explicit assumptions, persisted artifacts, and validation-oriented examples.
### 1. Eliminating the "Syntax Tax" for Engineers

Traditionally, setting up a Finite Element Analysis (FEA) simulation in a programmatic framework like FEniCS requires deep knowledge of both mechanics and pythonic solver APIs. An engineer has to manually define the mesh, boundary conditions, governing equations, and solver parameters.

- **The FEA Copilot Value:** It allows an engineer to think in natural language ("_A 2-meter steel I-beam fixed at one end with a 10kN point load at the tip_") and immediately generates the rigorous, structured specifications and ready-to-run FEniCS scripts. This compresses the time-to-first-simulation from hours to seconds.
    

### 2. Democratizing Quick Design Space Exploration

Before running a massive, computationally expensive 3D FEA simulation, engineers need quick analytical estimates to know if they are even in the right ballpark.

- **The FEA Copilot Value:** By providing "quick estimates" alongside structured specs, it acts as an instant sounding board. Designers can rapidly iterate on beam and plate geometries in early-stage design cycles without needing a dedicated simulation expert on standby for every minor change.
    

### 3. Transitioning from "Prototype" to "Enterprise-Grade Governance" (Phases 3 & 4)

While generating scripts from natural language is impressive, it is inherently risky in production environments where safety and data integrity are paramount. The completion of Phases 3 and 4 directly addresses these risks, shifting the project's value from an isolated utility to an institutional asset:

- **Artifact Inspection & Workspace Auditing:** AI-generated code cannot be trusted blindly. Having automated artifact inspection and workspace reporting ensures that the generated FEniCS code, boundary conditions, and material properties are explicit, auditable, and easily verified by a human-in-the-loop before execution.
    
- **Policy-Driven Export & Retention Workflows:** In aerospace, automotive, or civil engineering, you cannot just delete or misplace simulation data; liability and compliance require strict data lineages. Integrating automated policy exports and retention workflows means every AI-assisted design decision can be archived, tracked, and audited years down the line to match corporate or regulatory safety standards.
    

### 4. Strategic "Counter-Positioning" Against Heavy Legacy Software

Giant legacy FEA suites (like Ansys or Abaqus) are incredibly powerful but suffer from being massive, expensive, closed-source, GUI-heavy monoliths with steep learning curves.

- **The FEA Copilot Value:** This project counter-positions itself by being **narrow-scope, open, developer-centric, and text-driven**. It doesn't try to solve every complex aerodynamic problem; it solves simple beam and plate problems incredibly fast, directly in the developer's workspace. It leverages the open-source FEniCS computing platform, keeping infrastructure lightweight and deeply integrated into modern CI/CD software pipelines rather than locked inside a proprietary GUI.
## Show Me The Result

```text
$ feacopilot --prompt "Simulate a 1 m long, 0.1 m thick steel cantilever beam with a 150 N downward tip load." --solver-mode mock --output json
status: completed
geometry: beam
max_deflection: 3.000e-05 m
max_stress: 9.000e+05 Pa
artifacts: run_result.json, backend_status.json, backend_metadata.json, metrics.json
```

The `mock` path uses closed-form estimates for fast reproducible smoke tests. The Docker path runs generated DOLFINx scripts and is covered by a gated CI smoke test.

## Try It In 60 Seconds

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e '.[dev]'
./examples/minimal/run.sh
```

If you only want the raw CLI:

```bash
feacopilot \
  --prompt "Simulate a 1 m long, 0.1 m thick steel cantilever beam with a 150 N downward tip load." \
  --solver-mode mock \
  --output json
```

## Minimal Example

`examples/minimal/prompt.txt`

```text
Simulate a 1 m long, 0.1 m thick steel cantilever beam with a 150 N downward tip load.
```

Expected headline outputs:

- `status: completed`
- `geometry: beam`
- `max_deflection: 3.000e-05 m`
- `max_stress: 9.000e+05 Pa`

## Examples

Supported now:

- [Minimal CLI run](examples/minimal/README.md)
- [Cantilever beam](examples/beam_cantilever/README.md)
- [Simply supported beam](examples/simply_supported_beam/README.md)
- [Rectangular plate under pressure](examples/plate_pressure/README.md)
- [Bracket screening](examples/bracket_linear_elastic/README.md)
- [Plate-with-hole screening](examples/plate_with_hole/README.md)
- [Hand-calculation comparison](examples/hand_calc_comparison/README.md)

## Validation

Validation assets live under [`validation/`](validation):

- [Analytical beam comparison](validation/analytical_beam/README.md): matches the current Euler-Bernoulli cantilever estimate used by `mock` mode.
- [Public formula check](validation/public_formula_checks/README.md): compares the cantilever beam `mock` output against a readable hand calculation.
- [Roark-style square-plate benchmark](validation/roark_formulas/README.md): compares the `mock` clamped-plate estimate to a cited classical thin-plate table.
- [Mesh convergence study](validation/mesh_convergence/README.md): includes committed Docker-backed distributed-load cantilever beam convergence data and plots.
- [Solver comparison intake](validation/solver_comparison/README.md): clearly marked scaffold, not a finished benchmark claim.

Current validation summary:

| Case | Type | Status |
|---|---|---|
| Cantilever analytical beam | analytical | committed |
| Cantilever hand calculation | public formula check | committed |
| Square clamped plate | cited formula comparison | committed |
| Distributed-load beam convergence | Docker evidence | committed |
| Solver comparison | cross-backend intake | scaffold |

The repository does not claim external benchmark accuracy unless the comparison inputs, commands, reference source, and tolerance are committed alongside the case.

## Technical Credibility

- The parser is intentionally narrow and fails on unsupported or ambiguous prompts instead of guessing.
- The CLI and Streamlit app share the same `SimulationService`, so examples and tests exercise the same orchestration path.
- Every run writes a structured artifact bundle: `run_result.json`, `backend_status.json`, `backend_metadata.json`, logs, generated script, and metrics.
- `mock` mode is fast and deterministic for smoke tests and analytical screening workflows; Docker mode is the intended path for generated DOLFINx execution of beam and rectangular-plate cases.
- The test suite covers parsing, validation, script generation, CLI behavior, artifact inspection/export, visualization, and a gated Docker smoke path.

## Project Scope

In scope today:

- Linear-elastic beam prompts
- Linear-elastic rectangular plate prompts under pressure
- Analytical bracket screening prompts
- Analytical plate-with-hole tension screening prompts
- Mock analytical estimates for reproducible local runs
- Docker-backed generated DOLFINx execution for beams and rectangular plates
- Artifact inspection, export, retention, and workspace policy reporting

Not implemented yet:

- Docker-backed bracket geometry
- Docker-backed plate-with-hole geometry
- Nonlinear behavior
- Contact
- Plasticity
- Dynamics
- Thermal-mechanical coupling

## Assumptions And Limitations

- Results are for educational and preliminary design workflows, not certified sign-off.
- Beam prompts require a span, section size, and a load with units.
- Plate prompts require rectangular plan dimensions, thickness, and pressure with units.
- Bracket and plate-with-hole prompts currently run as analytical `mock`-mode screening workflows only.
- Host-local solver execution is intentionally unsupported; use `mock`, `docker`, or `auto`.
- The current `mock` path is an analytical estimator, not a full finite-element solve.

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e '.[dev]'
```

Optional Docker runtime:

```bash
docker pull dolfinx/dolfinx:v0.7.3
```

## Usage

Run a prompt:

```bash
feacopilot --prompt-file examples/beam_cantilever/prompt.txt --solver-mode mock --output json
```

Inspect a finished run:

```bash
feacopilot --inspect-run-dir /path/to/run
```

Audit, export, or clean up a workspace:

```bash
feacopilot --report-workspace-policy --workspace /path/to/runs --retention-days 14 --keep-latest 5
feacopilot --export-run-dir /path/to/run --export-output run-artifacts.zip
feacopilot --cleanup-runs --workspace /path/to/runs --retention-days 14 --keep-latest 5 --dry-run
```

## Docs

- [Quickstart](docs/quickstart.md)
- [Architecture](docs/architecture.md)
- [Assumptions](docs/assumptions.md)
- [Examples](docs/examples.md)
- [Validation](docs/validation.md)
- [Benchmark Contribution Loop](docs/benchmark.md)
- [Contributing Examples And Benchmarks](docs/contributing_examples.md)
- [LLM Quickstart](docs/llm-quickstart.md)
- [Repo Map](docs/repo-map.md)
- [Repository Settings](docs/repository-settings.md)
- [Teaching notebook](examples/hand_calc_comparison/hand_calc_walkthrough.ipynb)
- [GitHub Launch Checklist](docs/github_launch_checklist.md)
- [Release Checklist](docs/release_checklist.md)
- [Developer Guide](docs/developer-guide.md)
- [Artifact Lifecycle Runbook](docs/artifact-lifecycle-runbook.md)

## Contributing

Start with [CONTRIBUTING.md](CONTRIBUTING.md) and [AGENTS.md](AGENTS.md).

Fork this repo to add your own benchmark, solver adapter, or engineering example.

Good entry points:

- add a sourced validation case under `validation/`
- turn the bracket scaffold into a real adapter-backed example
- improve error messages for unsupported prompts
- add a Docker-backed mesh convergence plot with committed evidence
- extend docs around assumptions and solver limitations

The current roadmap and issue candidates live in [ROADMAP.md](ROADMAP.md).
