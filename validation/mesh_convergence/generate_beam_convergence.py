from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt

from fea_engine import BeamSection, FenicsScriptGenerator, FenicsSolver, LoadCase
from fea_engine.models import DEFAULT_MATERIALS, GeometryType, LoadType, SimulationSpec


ROOT = Path(__file__).resolve().parents[2]
CASE_DIR = ROOT / "validation" / "mesh_convergence"
OUTPUT_DIR = CASE_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def build_spec(mesh_density: int) -> SimulationSpec:
    return SimulationSpec(
        prompt="mesh convergence cantilever beam distributed load",
        geometry=GeometryType.BEAM,
        length=1.0,
        beam_section=BeamSection(height=0.1, width=0.1),
        mesh_density=mesh_density,
        boundary_condition="fixed",
        loads=[
            LoadCase(
                load_type=LoadType.DISTRIBUTED,
                magnitude=150.0,
                direction="-y",
                units="N",
            )
        ],
        material=DEFAULT_MATERIALS["steel"],
    )


def main() -> int:
    mesh_densities = [8, 12, 16, 24, 32]
    solver = FenicsSolver(mode="docker")
    generator = FenicsScriptGenerator()
    rows: list[dict[str, float | int]] = []
    previous_deflection: float | None = None
    previous_stress: float | None = None

    for density in mesh_densities:
        spec = build_spec(density)
        artifacts = solver.run(spec, generator.render(spec))
        metrics = json.loads(artifacts.metrics_path.read_text(encoding="utf-8"))
        deflection = float(metrics["max_deflection"])
        stress = float(metrics["max_stress"])
        rows.append(
            {
                "mesh_density": density,
                "max_deflection": deflection,
                "max_stress": stress,
                "deflection_change_ratio": 0.0 if previous_deflection is None else abs(deflection - previous_deflection) / previous_deflection,
                "stress_change_ratio": 0.0 if previous_stress is None else abs(stress - previous_stress) / previous_stress,
            }
        )
        previous_deflection = deflection
        previous_stress = stress

    csv_path = OUTPUT_DIR / "beam_convergence.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        "case": "distributed-load cantilever beam docker mesh convergence",
        "mesh_densities": mesh_densities,
        "results": rows,
    }
    (OUTPUT_DIR / "beam_convergence.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    plt.figure(figsize=(8, 5))
    plt.plot(mesh_densities, [row["max_deflection"] for row in rows], marker="o", label="max deflection (m)")
    plt.plot(mesh_densities, [row["max_stress"] for row in rows], marker="s", label="max stress (Pa)")
    plt.xlabel("Mesh density")
    plt.ylabel("Metric value")
    plt.title("Distributed-load cantilever beam convergence in Docker mode")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "beam_convergence.png", dpi=180)
    plt.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
