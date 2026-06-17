# Hand Calculation

For the prompt in `prompt.txt`, the current `mock` estimator uses:

- `F = 150 N`
- `L = 1.0 m`
- `b = 0.1 m`
- `h = 0.1 m`
- `E = 200e9 Pa`

Second moment of area:

`I = b h^3 / 12 = 0.1 * 0.1^3 / 12 = 8.333333e-06 m^4`

Tip deflection:

`delta_max = F L^3 / (3 E I) = 150 * 1^3 / (3 * 200e9 * 8.333333e-06) = 3.0e-05 m`

Maximum bending stress:

`sigma_max = F L (h / 2) / I = 150 * 1 * 0.05 / 8.333333e-06 = 9.0e05 Pa`

Those values match the expected metrics committed in this directory.
