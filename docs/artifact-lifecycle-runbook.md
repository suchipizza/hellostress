# Artifact Lifecycle Runbook

## Purpose

This runbook covers the supported operational lifecycle for completed run artifacts:

- inspect a completed run before consuming it
- audit a workspace to understand which runs are export-ready or need review
- export a validated bundle for handoff or retention
- bulk export policy-approved runs from a workspace
- clean up old runs from a local workspace with predictable retention rules

The goal is to keep the artifact contract machine-friendly without widening simulation scope.

## Artifact Set

A completed run directory is expected to contain at least:

- `run_result.json`
- `backend_status.json`
- `backend_metadata.json`
- `simulation.py`
- `results/metrics.json`
- solver stdout and stderr logs

`run_result.json` is the primary entry point. It carries the current `schema_version`, embeds backend summaries, and references the other files by path.

## Inspection Workflow

Use inspection before debugging, exporting, or automating against a run:

```bash
feacopilot --inspect-run-dir /path/to/run
feacopilot --inspect-run-result /path/to/run/run_result.json --output json
```

Inspection verifies:

- schema compatibility against the supported read range
- presence of referenced files
- consistency between embedded payloads and referenced backend artifact files
- basic generated-file and metrics diagnostics
- triage severity, issue codes, backend log context, and suggested next actions

Inspection JSON also exposes three policy decisions for automation:

- `quality_gate`: passes when triage contains no error-severity issues
- `export`: blocks packaging when the quality gate fails unless an explicit override is supplied
- `promotion`: only allows clean bundles with no triage issues

If inspection fails, treat the run as unsupported or incomplete instead of attempting best-effort recovery.

If inspection succeeds but reports triage issues, treat the bundle as readable but degraded. The JSON inspection payload is intended to support automation such as:

- blocking export of incomplete bundles
- routing timed-out or failed runs to backend troubleshooting
- flagging fallback-derived metrics for manual review

## Workspace Audit Workflow

Use the workspace report when you need a read-only view of run readiness across a local workspace:

```bash
feacopilot \
  --report-workspace-policy \
  --workspace /path/to/runs \
  --retention-days 14 \
  --keep-latest 5 \
  --output json
```

The report evaluates each direct child run directory against the same inspection-derived policy surface used for single-run decisions.

Report JSON is intended for automation and includes:

- per-run readiness fields such as `export_ready`, `promotion_ready`, `manual_review_required`, and `retention_candidate`
- aggregate counts such as `export_ready_count`, `promotion_ready_count`, `manual_review_count`, `retention_candidate_count`, `invalid_run_count`, and `skipped_path_count`
- invalid-run and skipped-path naming so scripts do not need to scrape text output

Use the text output for a compact operator summary and a short list of flagged runs.

## Export Workflow

Export only after a run passes inspection:

```bash
feacopilot \
  --export-run-dir /path/to/run \
  --export-output ./run-artifacts.zip \
  --output json
```

If inspection reports a failed quality gate, export is blocked by default:

```bash
feacopilot --export-run-dir /path/to/run
```

Use the override only when you intentionally want to preserve a degraded-but-still-readable bundle for handoff or forensic retention:

```bash
feacopilot --export-run-dir /path/to/run --allow-degraded-export
```

The export archive includes `export-manifest.json`, which records:

- manifest version
- source run paths and status metadata
- relative file paths inside the archive
- per-file byte sizes
- per-file SHA-256 checksums
- total file count

Use the returned `archive_sha256` for archive-level integrity checks in downstream storage or transfer workflows.

## Workspace Bulk Export Workflow

Use workspace export after reviewing the audit output when you want to package every export-ready run into a single destination directory:

```bash
feacopilot \
  --export-workspace-runs \
  --workspace /path/to/runs \
  --export-output-dir ./workspace-exports \
  --output json
```

Default behavior:

- exports valid runs whose export policy passes
- blocks invalid runs and policy-blocked degraded runs
- skips direct child paths that are not run directories
- reports per-run outcomes as `exported`, `blocked`, `skipped`, or `failed`

If you intentionally want degraded-but-readable bundles included, use the same explicit override as single-run export:

```bash
feacopilot \
  --export-workspace-runs \
  --workspace /path/to/runs \
  --export-output-dir ./workspace-exports \
  --allow-degraded-export \
  --output json
```

Use the override sparingly. It allows export attempts for policy-blocked but still readable bundles; invalid or incomplete bundles can still fail during archive creation and will be reported as `failed`.

The bulk export JSON payload includes:

- aggregate counts for exported, blocked, skipped, failed, and override-driven exports
- per-run archive paths and archive SHA-256 values for successful exports
- per-run reasons and issue codes for blocked or failed runs

## Cleanup Workflow

Use cleanup against the configured workspace or an explicit directory:

```bash
feacopilot \
  --cleanup-runs \
  --workspace /path/to/runs \
  --retention-days 14 \
  --keep-latest 5 \
  --dry-run \
  --output json
```

Operational guidance:

- start with `--dry-run` when adjusting policy
- use `--keep-latest` to protect a small number of recent runs regardless of age
- only direct child run directories containing `run_result.json` are candidates for deletion
- missing or malformed run directories are reported as skipped rather than deleted

JSON cleanup output is intended for automation and includes:

- summary counts for discovered, deleted, retained, and skipped paths
- deleted run names
- retained run names
- skipped path names

## CI Coverage

GitHub Actions covers the artifact lifecycle on every change to `main` and on pull requests:

- prompt execution in `mock` mode
- inspection of the emitted `run_result.json`
- workspace policy reporting on the generated run workspace
- export archive creation plus manifest validation
- workspace bulk export into an output directory
- cleanup dry-run verification
- cleanup deletion verification

That smoke path lives in `.github/workflows/ci.yml` and should stay aligned with the documented CLI contract.
