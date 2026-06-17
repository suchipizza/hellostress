# Repo Map

## Top-Level Layout

- `fea_engine/`: parser, validation, service orchestration, solver integration, artifact handling, and CLI
- `examples/`: user-facing runnable workflows and teaching examples
- `validation/`: reproducible validation cases, convergence evidence, and future comparison intake
- `templates/`: scaffolds for new examples, validation cases, adapters, and exporters
- `docs/`: user, contributor, launch, and architecture documentation
- `tests/`: unit, integration, golden, visualization, and Docker smoke coverage
- `assets/`: demo media and repository preview assets
- `launch/`: release and launch drafts, plus issue drafts for follow-up work

## High-Signal Files

- `README.md`: public landing page
- `AGENTS.md`: agent-safe operating instructions
- `Makefile`: common local commands
- `tools/run_validation.py`: list or run committed validation cases
- `.github/workflows/ci.yml`: required GitHub checks for `main`
