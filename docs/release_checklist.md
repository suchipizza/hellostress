# Release Checklist

## Before Tagging `v0.1.0`

- `make test`
- `make examples`
- `make validate`
- confirm the README, examples, and validation docs still match actual supported scope
- confirm PR `#3` has a qualifying approval and passed required checks
- confirm `main` is protected by the active ruleset

## Release Artifacts

- GitHub release notes from [launch/release-v0.1.0.md](../launch/release-v0.1.0.md)
- changelog entry in [CHANGELOG.md](../CHANGELOG.md)
- demo asset references in [README.md](../README.md)

## After Publishing

- verify social preview and repo topics
- update `OPEN_SOURCE_READINESS_REPORT.md` with the release date
- announce using the drafts in `launch/`
