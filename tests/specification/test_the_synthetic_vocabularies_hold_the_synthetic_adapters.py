import json
from pathlib import Path

import pytest
from pyshacl import validate
from rdflib import OWL, RDF, SH, Graph

ROOT = Path(__file__).resolve().parents[2]
ADAPTERS = [ROOT / "fixtures" / "synthetic-adapter", ROOT / "fixtures" / "synthetic-json-adapter"]
VOCABULARIES = ROOT / "fixtures" / "synthetic-vocabularies"
BRIDGE_VOCABULARY = ROOT / "vocab" / "bridge.ttl"
FACTS_SHAPES = ROOT / "shapes" / "facts.shapes.ttl"
DECLARES_A_PREDICATE = (RDF.Property, OWL.DatatypeProperty, OWL.ObjectProperty, OWL.AnnotationProperty)


def files_named_by(adapter):
    crate = json.loads((adapter / "ro-crate-metadata.json").read_text(encoding="utf-8"))
    root = next(entity for entity in crate["@graph"] if entity["@id"] == "./")
    return root["bridge:vocabularyFile"]


def named_files():
    return sorted({file for adapter in ADAPTERS for file in files_named_by(adapter)})


EXPECTED_GRAPHS = [
    pytest.param(path, files_named_by(adapter), id=path.name)
    for adapter in ADAPTERS
    for path in sorted((adapter / "fixtures" / "expected").glob("*.ttl"))
]


def read(*files):
    graph = Graph()
    for file in files:
        graph.parse(VOCABULARIES / file, format="turtle")
    return graph


class TestAVocabularyCheckoutToRunTheSyntheticAdaptersWith:
    """A vocabulary checkout to run the synthetic adapters with · fixtures/synthetic-vocabularies/

    An adapter names the files of the Cascade vocabulary it writes with, and an engine is handed a checkout that holds
    them. The synthetic vocabularies are that checkout for the synthetic adapters: an invented ontology file and its
    shapes, enough for the adapters' expected graphs to be checked against.
    """

    class TestGivenAVocabularyFileTheSyntheticAdaptersName:
        @pytest.mark.parametrize("file", named_files())
        def test_is_a_file_of_the_synthetic_vocabularies(self, file):
            assert (VOCABULARIES / file).is_file()

    class TestGivenAnExpectedGraphOfASyntheticAdapter:
        @pytest.mark.parametrize(("expected", "files"), EXPECTED_GRAPHS)
        def test_writes_only_predicates_that_those_files_or_the_bridge_vocabulary_declare_or_a_caller_supplies(
            self, expected, files
        ):
            """writes only predicates that those files or the Bridge vocabulary declare, or that `shapes/facts.shapes.ttl` lets a caller supply"""
            vocabulary = read(*files) + Graph().parse(BRIDGE_VOCABULARY, format="turtle")
            declared = {term for kind in DECLARES_A_PREDICATE for term in vocabulary.subjects(RDF.type, kind)}
            declared |= set(Graph().parse(FACTS_SHAPES, format="turtle").objects(None, SH.path))
            written = set(Graph().parse(expected, format="turtle").predicates()) - {RDF.type}
            assert written <= declared, written - declared

        @pytest.mark.parametrize(("expected", "files"), EXPECTED_GRAPHS)
        def test_conforms_to_the_shapes_among_those_files(self, expected, files):
            conforms, _, text = validate(Graph().parse(expected, format="turtle"), shacl_graph=read(*files))
            assert conforms, text
