# Plate With Hole

## Status

Supported in analytical `mock` mode as a plate-with-hole tension screening workflow.

## Command

```bash
./examples/plate_with_hole/run.sh
```

## Prompt

See [prompt.txt](prompt.txt).

## Expected Output

The command should complete in `mock` mode and write `output/result.json`. See [expected_metrics.json](expected_metrics.json).

## Assumptions

- far-field axial tension is expressed with pressure units
- peak stress uses a Kirsch-style wide-plate concentration factor of about `3.0`
- deflection is a first-pass membrane-strain estimate, not a cutout-resolved plate solve

## Validation Note

TODO: add a cited finite-width plate-with-hole benchmark and a real backend cutout geometry implementation before advertising Docker support.
