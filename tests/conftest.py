from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fea_engine import BeamSection, LoadCase, PlateDimensions, PromptParser, SimulationSpec
from fea_engine.models import DEFAULT_MATERIALS, GeometryType, LoadType


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-docker-smoke",
        action="store_true",
        default=False,
        help="run docker-backed integration smoke tests",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "integration: exercises the real Docker-backed execution path",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if config.getoption("--run-docker-smoke") or os.environ.get("RUN_DOCKER_SMOKE") == "1":
        return

    skip_integration = pytest.mark.skip(
        reason="docker smoke tests disabled; use --run-docker-smoke or RUN_DOCKER_SMOKE=1"
    )
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_integration)


@pytest.fixture
def parser() -> PromptParser:
    return PromptParser()


@pytest.fixture
def sample_beam_spec() -> SimulationSpec:
    return SimulationSpec(
        prompt="beam fixture",
        geometry=GeometryType.BEAM,
        length=1.0,
        beam_section=BeamSection(height=0.1, width=0.1),
        boundary_condition="fixed",
        loads=[
            LoadCase(
                load_type=LoadType.POINT,
                magnitude=150.0,
                direction="-y",
                location=1.0,
                units="N",
            )
        ],
        material=DEFAULT_MATERIALS["steel"],
    )


@pytest.fixture
def sample_plate_spec() -> SimulationSpec:
    return SimulationSpec(
        prompt="plate fixture",
        geometry=GeometryType.PLATE,
        length=0.5,
        plate_dimensions=PlateDimensions(width=0.3, thickness=0.005),
        boundary_condition="roller",
        loads=[
            LoadCase(
                load_type=LoadType.PRESSURE,
                magnitude=50000.0,
                direction="-z",
                units="Pa",
            )
        ],
        material=DEFAULT_MATERIALS["aluminum"],
    )
