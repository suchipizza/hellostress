# Bracket Linear Elastic

## Status

Supported in analytical `mock` mode as a first-pass cantilever-strip bracket screening workflow.

## Command

```bash
./examples/bracket_linear_elastic/run.sh
```

## Prompt

See [prompt.txt](prompt.txt).

## Expected Output

The command should complete in `mock` mode and write `output/result.json`. See [expected_metrics.json](expected_metrics.json).

## Assumptions

- bracket is approximated as a cantilever strip from the fixed root to the loaded hole
- rectangular section uses the parsed width and thickness
- this is an analytical screening workflow, not a Docker-backed bracket solve

## Validation Note

TODO: add a committed bracket benchmark and a real backend geometry implementation before advertising Docker support.
