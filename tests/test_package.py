"""Tests for the public surface of the ``reframe`` package."""

import tomllib
from pathlib import Path

import reframe

PYPROJECT_PATH = Path(__file__).resolve().parent.parent / "pyproject.toml"


def _read_project_version() -> str:
    with PYPROJECT_PATH.open("rb") as handle:
        data = tomllib.load(handle)
    return str(data["project"]["version"])


def test_version_constant() -> None:
    assert reframe.__version__ == "0.1.0.dev0"


def test_version_matches_pyproject() -> None:
    assert _read_project_version() == reframe.__version__
