from __future__ import annotations

from pathlib import Path

from fea_engine import FenicsScriptGenerator


def _read_golden(name: str) -> str:
    return (Path(__file__).parent / "golden" / name).read_text(encoding="utf-8").strip()


def test_beam_script_matches_golden(sample_beam_spec) -> None:
    rendered = FenicsScriptGenerator().render(sample_beam_spec).strip()

    assert rendered == _read_golden("beam_simulation.py")


def test_plate_script_matches_golden(sample_plate_spec) -> None:
    rendered = FenicsScriptGenerator().render(sample_plate_spec).strip()

    assert rendered == _read_golden("plate_simulation.py")
