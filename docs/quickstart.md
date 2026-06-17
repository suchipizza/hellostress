# Quickstart

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e '.[dev]'
```

Or in Codespaces / a compatible devcontainer:

```bash
python3 -m pip install -e '.[dev]'
make test
make example
```

Optional Docker backend:

```bash
docker pull dolfinx/dolfinx:v0.7.3
```

## Run The Minimal Example

```bash
./examples/minimal/run.sh
```

That script runs:

```bash
feacopilot --prompt-file examples/minimal/prompt.txt --solver-mode mock --output json
```

## Make Targets

```bash
make test
make example
make examples
make validate
```

## Run A Beam Example

```bash
./examples/beam_cantilever/run.sh
```

Simply supported analytical example:

```bash
./examples/simply_supported_beam/run.sh
```

## Run A Plate Example

```bash
./examples/plate_pressure/run.sh
```

Analytical screening workflows:

```bash
./examples/bracket_linear_elastic/run.sh
./examples/plate_with_hole/run.sh
```

## Inspect A Finished Run

```bash
feacopilot --inspect-run-dir /path/to/run
```

## Audit Or Export A Workspace

```bash
feacopilot --report-workspace-policy --workspace /path/to/runs --retention-days 14 --keep-latest 5
feacopilot --export-run-dir /path/to/run --export-output run-artifacts.zip
```

## What Works Today

- beam prompts with explicit geometry and load units
- rectangular plate prompts with pressure loads
- analytical bracket screening prompts
- analytical plate-with-hole screening prompts
- fast `mock` mode for local smoke tests
- Docker-backed generated DOLFINx execution for beams and rectangular plates
- artifact inspection, export, cleanup, and workspace policy reporting

## What Does Not Work Yet

- Docker-backed bracket geometry
- Docker-backed plate-with-hole geometry
- nonlinear or contact workflows
- certified production sign-off
