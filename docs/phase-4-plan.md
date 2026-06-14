# Phase 4 Plan

## Objective

Phase 4 focuses on operationalizing the artifact contract introduced in Phase 2 and exposed in Phase 3 so automation can trust, inspect, and validate completed runs.

Phase 4 turned those per-run guarantees into workspace-level operations that feel MVP-complete for a single-user or small-team workflow.

## Scope

The target is a more machine-friendly and supportable run artifact surface without expanding simulation geometry scope:

- explicit artifact schema versioning
- reusable artifact loading and validation utilities
- CLI inspection for completed runs
- operator-oriented inspection triage for degraded runs
- policy enforcement for export and promotion decisions
- workspace-level policy reporting and audit automation
- bulk operational workflows driven by policy state
- updated docs for artifact consumers and operators

## Status

Completed on `main`:

- P4-01. Version the Artifact Contract
- P4-02. Artifact Validation Utilities
- P4-03. CLI Inspection
- P4-04. Documentation Closeout
- P4-05. Inspection Triage
- P4-06. Policy Enforcement
- P4-07. Workspace Policy Report
- P4-08. Bulk Workflow Actions
- P4-09. MVP Operational Closeout

Phase 4 is complete on `main`.

## Ticket Sequence

### P4-01. Version the Artifact Contract

- Add explicit schema versions to `backend_status.json`, `backend_metadata.json`, and `run_result.json`.
- Treat schema versioning as part of the supported backend contract.

Acceptance:

- Newly written backend artifacts include an explicit schema version.
- Tests cover schema version presence for mock and Docker-backed runs.

### P4-02. Artifact Validation Utilities

- Add a reusable module that loads and validates completed run artifacts.
- Fail clearly when required files or required top-level fields are missing.

Acceptance:

- A caller can validate a `run_result.json` and its referenced backend artifacts without re-running the simulation.
- Validation errors are typed and readable.

### P4-03. CLI Inspection

- Extend the `feacopilot` CLI to inspect an existing run artifact bundle.
- Support both machine-readable and concise human-readable inspection output.

Acceptance:

- Contributors can inspect a completed run from the command line.
- Inspection reports resolved paths, schema versions, run status, backend status, and warnings.

### P4-04. Documentation Closeout

- Mark Phase 3 complete.
- Document the versioned artifact contract and the inspection workflow.

Acceptance:

- README and developer docs explain the artifact schema versioning and inspection path.
- Repo status text reflects Phase 3 complete and Phase 4 in progress.

### P4-05. Inspection Triage

- Extend inspection output so valid-but-degraded bundles report actionable issues, backend context, and suggested remediation.
- Keep the persisted artifact files stable; this is an inspection/reporting enhancement, not a new artifact schema.

Acceptance:

- Inspection JSON exposes issue severity, issue codes, backend log context, and suggested actions.
- Inspection text output surfaces the same triage summary for operators without requiring JSON parsing.
- Tests cover degraded bundles such as missing metrics, fallback use, and incomplete Docker cleanup.

### P4-06. Policy Enforcement

- Add a machine-readable quality gate on top of inspection triage.
- Block export by default when the quality gate fails, while allowing an explicit operator override for degraded-but-exportable bundles.
- Expose promotion readiness separately so downstream automation can require a fully clean bundle.

Acceptance:

- Inspection JSON exposes quality-gate, export, and promotion policy decisions.
- Export fails clearly on policy-blocked bundles unless an explicit override is provided.
- Tests cover blocked export, overridden degraded export, and clean bundle policy pass behavior.

### P4-07. Workspace Policy Report

- Add a workspace-level audit command that scans direct child run directories and evaluates each run against the inspection triage and policy gates.
- Emit both per-run records and aggregate counts so automation can reason about the workspace without shell scraping.
- Keep the report read-only; this ticket is for visibility and machine-readable status, not mutation.

Acceptance:

- A CLI command can scan a workspace and report per-run status for export readiness, promotion readiness, manual review requirement, and retention candidacy.
- JSON output includes aggregate counts such as `export_ready_count`, `promotion_ready_count`, `manual_review_count`, `retention_candidate_count`, `invalid_run_count`, and `skipped_path_count`.
- Text output gives a concise operator summary plus a short list of flagged runs.
- Tests cover mixed workspaces with clean runs, degraded runs, invalid runs, and old retention candidates.

### P4-08. Bulk Workflow Actions

- Add optional bulk actions driven by the workspace policy report rather than ad hoc file picking.
- Start with the narrowest high-value path: exporting policy-approved runs from a workspace into a chosen output directory.
- Keep destructive behavior gated and explicit; no silent deletion or promotion mutation in this ticket.

Acceptance:

- Contributors can export all export-ready runs from a workspace with a single command.
- The command skips policy-blocked runs by default and reports which runs were exported, blocked, skipped, or failed.
- JSON output includes per-run action results suitable for automation.
- Tests cover mixed workspaces and explicit override behavior for degraded exports when requested.

### P4-09. MVP Operational Closeout

- Close the loop on the artifact lifecycle as an MVP product surface: run, inspect, audit, export, and clean up.
- Update docs and CI coverage so the supported operational story is explicit and reproducible.
- Keep scope narrow; this is not a deployment platform or multi-user scheduling layer.

Acceptance:

- README and runbook document the full supported operator flow for single-run and workspace-level workflows.
- GitHub Actions cover at least one workspace-level policy report path in addition to the existing single-run lifecycle smoke.
- Phase 4 status text can credibly describe the product as MVP-ready for its current narrow simulation scope.

## Out of Scope

- new geometry families
- remote artifact storage
- multi-user job orchestration
- deployment infrastructure beyond the current local and Docker-backed workflow
