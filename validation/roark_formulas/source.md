# Source

Reference used for this case:

- Timoshenko and Woinowsky-Krieger, *Theory of Plates and Shells*, Table 35, `nu = 0.3`
- Public scan used for implementation review: <https://files.engineering.com/files/e40f123f-053e-4747-8ce2-c7f6b302bfa1/Tab_35_from_Timoshenko_Plates.pdf>

The benchmark uses the square-plate row from the scanned table:

- `w_max = 0.00126 * q * a^4 / D`
- `M_x = M_y = -0.0513 * q * a^2` at the centerline location reported by the table

The surface bending stress estimate in this repository converts the largest moment coefficient with `sigma = 6M / t^2`.
