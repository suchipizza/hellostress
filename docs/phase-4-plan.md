# Phase 4 Plan

## Objective

Phase 4 focuses on operationalizing the artifact contract introduced in Phase 2 and exposed in Phase 3 so automation can trust, inspect, and validate completed runs.

## Scope

The target is a more machine-friendly and supportable run artifact surface without expanding simulation geometry scope:

- explicit artifact schema versioning
- reusable artifact loading and validation utilities
- CLI inspection for completed runs
- operator-oriented inspection triage for degraded runs
- updated docs for artifact consumers and operators

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

## Out of Scope

- new geometry families
- remote artifact storage
- multi-user job orchestration
- deployment infrastructure beyond the current local and Docker-backed workflow
