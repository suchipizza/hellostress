from pathlib import Path


def test_solver_adapter_template_files_exist() -> None:
    root = Path(__file__).resolve().parent
    assert (root / "adapter_stub.py").exists()
    assert (root / "README.md").exists()
