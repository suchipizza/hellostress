from pathlib import Path


def test_validation_template_includes_manifest() -> None:
    root = Path(__file__).resolve().parent
    assert (root / "case_manifest.json").exists()
    assert (root / "reference_solution.md").exists()
