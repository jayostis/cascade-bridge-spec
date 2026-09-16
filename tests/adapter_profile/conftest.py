import dataclasses
import shutil
import subprocess
from pathlib import Path

import _crate
import pytest
from pyshacl import validate
from rdflib import Graph
from rdflib.namespace import RDF, SH

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "fixtures" / "synthetic-adapter"
MUST = ROOT / "adapter" / "profile" / "must"


class Package:
    """A copy of the fixture package, whose files a test may change."""

    def __init__(self, path, tracked=True):
        shutil.copytree(FIXTURE, path)
        self.path = path
        self.tracked = tracked
        if tracked:
            self._git("init", "-q")
            self._git("add", "-A")

    def _git(self, *args):
        subprocess.run(
            ["git", "-C", str(self.path), *args], check=True, capture_output=True
        )

    def edit(self, relative, old, new):
        target = self.path / relative
        text = target.read_text(encoding="utf-8")
        assert text.count(old) == 1, f"{relative}: {old!r} occurs {text.count(old)} times"
        target.write_text(text.replace(old, new), encoding="utf-8", newline="")
        return self

    def write(self, relative, text):
        (self.path / relative).write_text(text, encoding="utf-8", newline="")
        if self.tracked:
            self._git("add", "-A")
        return self

    @property
    def crate(self):
        return _crate.load(self.path)


@pytest.fixture
def package(tmp_path):
    return Package(tmp_path / "package")


@pytest.fixture
def loose(tmp_path):
    return Package(tmp_path / "package", tracked=False)


@pytest.fixture(scope="session")
def conforming(tmp_path_factory):
    return Package(tmp_path_factory.mktemp("conforming") / "package").crate


@pytest.fixture
def crate(conforming):
    """The fixture package's crate, parsed once, with a graph a test may change."""
    graph = Graph()
    graph += conforming.graph
    return dataclasses.replace(conforming, graph=graph)


@pytest.fixture(scope="session")
def native():
    """What a shape file under adapter/profile/must/ reports for a crate."""

    def run(crate, shapes_file):
        _, report, _ = validate(
            crate.graph,
            shacl_graph=Graph().parse(MUST / shapes_file, format="turtle"),
            advanced=True,
        )
        return "\n".join(
            str(report.value(result, SH.resultMessage))
            for result in report.subjects(RDF.type, SH.ValidationResult)
        )

    return run
