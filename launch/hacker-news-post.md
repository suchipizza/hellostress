# Hacker News Draft

Title: Show HN: FEA Copilot — reproducible linear-elastic FEA workflows from natural-language prompts

Body:

Built this as a narrow open-source tool for first-pass beam and plate checks.

It turns supported prompts into a structured spec, generated solver script, metrics, and committed validation artifacts instead of stopping at a chat answer.

The interesting part for me is the repo surface: examples, analytical checks, a hand-calculation comparison, mesh-convergence evidence, and explicit unsupported-scope handling.

Current scope is intentionally conservative: beam and rectangular-plate workflows, plus analytical screening examples for brackets and plates with holes.
