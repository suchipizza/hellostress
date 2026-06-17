## Summary

- what changed
- why it changed
- user or contributor impact

## Validation

- [ ] `python3 -m py_compile app.py fea_engine/*.py templates/*.py tests/*.py`
- [ ] `pytest -q`
- [ ] `./examples/smoke_test.sh`
- [ ] Docker smoke path, if relevant

## Scope Check

- [ ] docs and examples match the actual supported behavior
- [ ] new validation claims include reproducible evidence
- [ ] unrelated refactors were not mixed into this PR
