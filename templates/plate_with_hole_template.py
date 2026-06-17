PLATE_WITH_HOLE_TEMPLATE = """from pathlib import Path
import json

results_dir = Path("/workspace/results")
results_dir.mkdir(exist_ok=True)

raise RuntimeError(
    "Plate-with-hole workflows are currently available in analytical mock mode only. "
    "The Docker backend does not yet implement plate cutout geometry."
)
"""
