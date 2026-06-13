# Artifact Lifecycle Runbook

## Purpose

This runbook covers the supported operational lifecycle for completed run artifacts:

- inspect a completed run before consuming it
- export a validated bundle for handoff or retention
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

If inspection fails, treat the run as unsupported or incomplete instead of attempting best-effort recovery.

## Export Workflow

Export only after a run passes inspection:

```bash
feacopilot \
  --export-run-dir /path/to/run \
  --export-output ./run-artifacts.zip \
  --output json
```

The export archive includes `export-manifest.json`, which records:

- manifest version
- source run paths and status metadata
- relative file paths inside the archive
- per-file byte sizes
- per-file SHA-256 checksums
- total file count

Use the returned `archive_sha256` for archive-level integrity checks in downstream storage or transfer workflows.

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
- export archive creation plus manifest validation
- cleanup dry-run verification
- cleanup deletion verification

That smoke path lives in `.github/workflows/ci.yml` and should stay aligned with the documented CLI contract.
