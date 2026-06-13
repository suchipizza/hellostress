# User Guide

## Overview

FEA Copilot converts a narrow set of natural-language beam and plate prompts into quick structural simulations. In Phase 1, the supported scope is intentionally limited to:

- Beam prompts that clearly specify length, section thickness or height, and load with units.
- Plate prompts that clearly specify rectangular plan dimensions, thickness, and pressure with units.

## Quick Start

1. Create and activate a virtual environment.
2. Install runtime dependencies with `pip install -r requirements.txt`.
3. Launch the app with `streamlit run app.py`.
4. Start with one of the built-in example prompts.

## Supported Prompt Patterns

- Beam: `1 m long steel cantilever beam 0.1 m thick with a 150 N downward tip load`
- Plate: `0.5 m by 0.3 m aluminum plate 5 mm thick under 50 kPa pressure`

## Current Constraints

- Plate simulations currently support pressure loads only.
- Beam width defaults to beam height when width is omitted.
- Mock mode provides analytical estimates, not a certified FEA sign-off.
- Supported solver backends are `mock`, `docker`, and `auto`.
- Host-local solver execution is intentionally not supported.
- If a prompt is ambiguous or missing units, the app now fails explicitly instead of guessing.

## Troubleshooting

- `Prompt must mention either a beam or a plate`: add the geometry explicitly.
- `Could not determine the load magnitude and units`: include units such as `N`, `kN`, `kPa`, or `MPa`.
- `Could not determine beam thickness/height`: include a section size such as `50 mm thick`.
