from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def sparql_contract():
    return " ".join((Path(__file__).resolve().parents[2] / "engine" / "sparql.md").read_text(encoding="utf-8").split())
