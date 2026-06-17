# Contributing Examples

## Example Directory Checklist

Each example directory should contain:

- `README.md`
- `prompt.txt`
- `run.sh`
- `expected_metrics.json`, `expected_output.md`, or another explicit output artifact
- assumptions
- validation note or `TODO`

## Validation Case Checklist

Each validation directory should contain:

- problem statement
- reproducible command
- reference result
- tolerance
- source attribution if the reference is external
- note about whether the case is committed evidence or scaffold only

## Good First Issues

- extend the simply supported beam example with a Docker-backed comparison once the backend honors the support condition explicitly
- add a second sourced rectangular-plate benchmark at a different aspect ratio
- add a mesh-convergence interpretation note explaining when the stress metric stabilizes enough for review
- expand the teaching notebook with figures loaded from saved artifact files
- improve bracket and plate-with-hole scaffolds with tighter contributor implementation notes
- add docs for material and boundary-condition assumptions

## Example Review Heuristics

- would a new contributor know how to run this from a clean clone?
- are the assumptions stated in engineering language?
- is the expected output explicit enough to catch regressions?
- does the example avoid implying unsupported scope?
