from pathlib import Path


def test_exporter_template_files_exist() -> None:
    root = Path(__file__).resolve().parent
    assert (root / "exporter_stub.py").exists()
    assert (root / "README.md").exists()
