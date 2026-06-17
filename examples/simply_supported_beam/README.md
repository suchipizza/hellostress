# Simply Supported Beam

## Purpose

Teaching-oriented beam example for a simply supported steel beam with a midspan point load.

## Command

```bash
./examples/simply_supported_beam/run.sh
```

## Prompt

See [prompt.txt](prompt.txt).

## Expected Outputs

- [expected_metrics.json](expected_metrics.json)
- `output/result.json`

## Assumptions

- Euler-Bernoulli beam estimate in `mock` mode
- simply supported beam approximated by the parser as `roller`
- point load applied at midspan

## Validation Note

This example is committed as an analytical teaching example. It is not presented as a Docker-backed beam benchmark.
