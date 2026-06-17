# GitHub Launch Checklist

## Repository Description Recommendation

`Natural-language FEA copilot for reproducible linear-elastic beam and plate workflows, with validation-first examples and artifact inspection tooling.`

## Repository Topics

- `finite-element-analysis`
- `fea`
- `computational-mechanics`
- `mechanical-engineering`
- `simulation`
- `engineering`
- `python`
- `calculix`
- `abaqus`
- `ansys`
- `linear-elasticity`
- `structural-analysis`
- `engineering-education`

Only keep topics that remain defensible for the actual public scope. Solver-brand topics should be removed if no adapter or example exists for them yet.

## Social Preview Image

- commit `assets/social-preview.png`
- verify the image is legible in GitHub repository cards
- keep the text aligned with current scope: beams and plates today, not brackets unless implemented

## Release And Changelog Process

1. Update `CHANGELOG.md`.
2. Tag a version that matches package metadata.
3. Confirm README commands still work from a clean install.
4. Regenerate demo assets if CLI output materially changed.
5. Publish release notes summarizing examples, validation, and known limits.

## First Good Issues To Queue

- sourced plate benchmark
- simply supported beam example
- mesh convergence evidence
- better unsupported-geometry errors
- teaching notebook

## Launch Sequence

1. Verify CI is green.
2. Verify README quickstart from a clean clone.
3. Confirm issue templates and PR template are live.
4. Set repository description and topics.
5. Upload the social preview image in GitHub settings.
6. Open the first 5 curated good-first issues.
7. Publish a release with changelog notes.
8. Share the repo only after the examples and validation links are all working.

## No Fake Stars Policy

- do not buy stars
- do not automate fake engagement
- do not publish benchmark claims without evidence
- optimize for real forks, issues, external reproductions, and technical discussion
