import json
from pathlib import Path

import pytest
from pyshacl import validate
from rdflib import OWL, RDF, Graph

ROOT = Path(__file__).resolve().parents[2]
ADAPTER = ROOT / "fixtures" / "synthetic-adapter"
VOCABULARIES = ROOT / "fixtures" / "synthetic-vocabularies"
EXPECTED_GRAPHS = sorted((ADAPTER / "fixtures" / "expected").glob("*.ttl"))
DECLARES_A_PREDICATE = (RDF.Property, OWL.DatatypeProperty, OWL.ObjectProperty, OWL.AnnotationProperty)


def named_files():
    crate = json.loads((ADAPTER / "ro-crate-metadata.json").read_text(encoding="utf-8"))
    root = next(entity for entity in crate["@graph"] if entity["@id"] == "./")
    return root["bridge:vocabularyFile"]


def read(*files):
    graph = Graph()
    for file in files:
        graph.parse(VOCABULARIES / file, format="turtle")
    return graph


@pytest.mark.parametrize("file", named_files())
def test_every_vocabulary_file_the_synthetic_adapter_names_is_there(file):
    assert (VOCABULARIES / file).is_file()


@pytest.mark.parametrize("expected", EXPECTED_GRAPHS, ids=lambda path: path.name)
def test_every_predicate_an_expected_graph_writes_is_declared_there(expected):
    vocabulary = read(*named_files())
    declared = {term for kind in DECLARES_A_PREDICATE for term in vocabulary.subjects(RDF.type, kind)}
    written = set(Graph().parse(expected, format="turtle").predicates()) - {RDF.type}
    assert written <= declared, written - declared


@pytest.mark.parametrize("expected", EXPECTED_GRAPHS, ids=lambda path: path.name)
def test_every_expected_graph_meets_the_shapes_there(expected):
    conforms, _, text = validate(Graph().parse(expected, format="turtle"), shacl_graph=read(*named_files()))
    assert conforms, text
