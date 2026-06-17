# LLM Quickstart

## What An LLM Or Coding Agent Should Read First

1. [README.md](../README.md)
2. [AGENTS.md](../AGENTS.md)
3. [docs/quickstart.md](quickstart.md)
4. [docs/repo-map.md](repo-map.md)
5. [docs/assumptions.md](assumptions.md)

## Safe First Commands

```bash
python3 -m pip install -e '.[dev]'
make test
make example
make validate
```

## Rules

- do not invent supported physics beyond what the docs and tests state
- do not claim Docker support for bracket or plate-with-hole geometries
- keep new benchmark claims tied to committed reference values and tolerances
- preserve the artifact bundle contract unless tests and docs are updated together
