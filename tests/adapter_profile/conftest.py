import dataclasses
import json
import shutil
import subprocess
from pathlib import Path

import pytest
from pyshacl import validate
from rdflib import Graph
from rdflib.namespace import RDF, SH

import _crate

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "fixtures" / "synthetic-adapter"
MUST = ROOT / "adapter" / "profile" / "must"

GAP_SCHEME_FILE = "vocab/example-gaps.ttl"
SOURCE_ACCOUNTING_FILE = "vocab/example-accounting.ttl"

A_GAP_SCHEME_OF_TWO_WHOLE_GAPS = """@prefix skos:   <http://www.w3.org/2004/02/skos/core#> .
@prefix bridge: <https://ns.cascadeprotocol.org/bridge/v1-draft#> .
@prefix ex:     <https://example.org/synthetic-adapter/v1#> .

ex:gaps a skos:ConceptScheme .

ex:no-term-for-a-free-text-note a skos:Concept ;
  skos:prefLabel "no term for a free-text note" ;
  skos:inScheme ex:gaps ;
  skos:broader bridge:noPredicate .

ex:a-status-outside-the-set-the-vocabulary-fixes a skos:Concept ;
  skos:prefLabel "a status outside the set the vocabulary fixes" ;
  skos:inScheme ex:gaps ;
  skos:broader bridge:valueNotMapped .
"""


class Package:
    def __init__(self, path, tracked=True):
        shutil.copytree(FIXTURE, path)
        self.path = path
        self.tracked = tracked
        if tracked:
            self._git("init", "-q")
            self._git("add", "-A")

    def _git(self, *args):
        subprocess.run(["git", "-C", str(self.path), *args], check=True, capture_output=True)

    def edit(self, relative, old, new, times=1):
        target = self.path / relative
        text = target.read_text(encoding="utf-8")
        found = text.count(old)
        assert found == times, f"{relative}: {old!r} occurs {found} times, {times} expected"
        target.write_text(text.replace(old, new), encoding="utf-8", newline="")
        return self

    def write(self, relative, text):
        target = self.path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8", newline="")
        if self.tracked:
            self._git("add", "-A")
        return self

    def _named_turtle(self, term, named, name):
        crate = self.path / "ro-crate-metadata.json"
        document = json.loads(crate.read_text(encoding="utf-8"))
        document["@context"][1][term] = term
        for entity in document["@graph"]:
            if entity["@id"] == "./":
                entity[term] = {"@id": named}
                if {"@id": named} not in entity["hasPart"]:
                    entity["hasPart"].append({"@id": named})
        if not any(entity["@id"] == named for entity in document["@graph"]):
            document["@graph"].append(
                {
                    "@id": named,
                    "@type": "File",
                    "name": name,
                    "encodingFormat": "text/turtle",
                    "license": {"@id": "https://spdx.org/licenses/Apache-2.0"},
                }
            )
        crate.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8", newline="")
        if self.tracked:
            self._git("add", "-A")
        return self

    def gap_scheme(self, turtle=A_GAP_SCHEME_OF_TWO_WHOLE_GAPS, named=GAP_SCHEME_FILE):
        """The package's one bridge:gapScheme, whatever it named before."""
        self.write(named, turtle)
        return self._named_turtle("bridge:gapScheme", named, "Gap scheme")

    def source_accounting(self, turtle, named=SOURCE_ACCOUNTING_FILE):
        """The package's one bridge:sourceAccounting, whatever it named before."""
        self.write(named, turtle)
        return self._named_turtle("bridge:sourceAccounting", named, "Source accounting")

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
    graph = Graph()
    graph += conforming.graph
    return dataclasses.replace(conforming, graph=graph)


@pytest.fixture(scope="session")
def shape_file_messages():
    def run(crate, shapes_file):
        _, report, _ = validate(
            crate.graph,
            shacl_graph=Graph().parse(MUST / shapes_file, format="turtle"),
            advanced=True,
        )
        return "\n".join(
            str(report.value(result, SH.resultMessage)) for result in report.subjects(RDF.type, SH.ValidationResult)
        )

    return run
