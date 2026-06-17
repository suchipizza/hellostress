from pathlib import Path


def test_example_template_includes_prompt_and_runner() -> None:
    root = Path(__file__).resolve().parent
    assert (root / "prompt.txt").exists()
    assert (root / "run.sh").exists()
