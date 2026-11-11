from pathlib import Path

import pytest
from rdflib import Graph, Namespace
from rdflib.compare import isomorphic, to_isomorphic
from rdflib.namespace import RDF

import json_lift

ROOT = Path(__file__).resolve().parents[2]
LIFT = ROOT / "fixtures" / "lift"
MF = Namespace("http://www.w3.org/2001/sw/DataAccess/tests/test-manifest#")
BRIDGE = Namespace("https://ns.cascadeprotocol.org/bridge/v1-draft#")

MANIFEST = Graph().parse(LIFT / "manifest.ttl", format="turtle", publicID=(LIFT / "manifest.ttl").as_uri())

LIBRARY = ROOT / "fixtures" / "library"
LIBRARY_MANIFEST = Graph().parse(
    LIBRARY / "manifest.ttl", format="turtle", publicID=(LIBRARY / "manifest.ttl").as_uri()
)
NOT_LIFTED = [
    pytest.param("json-with-a-byte-order-mark.json", id="a byte order mark"),
    pytest.param("json-with-a-lone-surrogate-in-a-string.json", id="a lone surrogate in a string"),
    pytest.param("json-with-a-lone-surrogate-in-a-name.json", id="a lone surrogate in a name"),
    pytest.param("json-holding-a-string.json", id="a string as the value"),
    pytest.param("json-holding-a-number.json", id="a number as the value"),
    pytest.param("json-holding-nan.json", id="NaN"),
    pytest.param("json-that-is-not-utf-8.json", id="text that is not UTF-8"),
]


def refused_documents():
    """The names of the files that a library case converts and expects refused as a document failure."""
    refused = set()
    for call in LIBRARY_MANIFEST.subjects(BRIDGE.failure, BRIDGE.documentFailure):
        document = LIBRARY_MANIFEST.value(call, BRIDGE.document)
        refused.add(str(LIBRARY_MANIFEST.value(document, BRIDGE.file)).rsplit("/", 1)[-1])
    return refused


def local(iri):
    return LIFT / str(iri).rsplit("/", 1)[1]


def json_vectors():
    for kind in (BRIDGE.LiftTest, BRIDGE.SkeletonTest):
        for entry in sorted(MANIFEST.subjects(RDF.type, kind)):
            action = MANIFEST.value(entry, MF.action)
            if json_lift.applies_to(str(MANIFEST.value(action, BRIDGE.sourceMediaType))):
                path = MANIFEST.value(action, BRIDGE.jsonPathOfEachRecord)
                expected = MANIFEST.value(MANIFEST.value(entry, MF.result), BRIDGE.expectedGraph)
                yield pytest.param(
                    local(MANIFEST.value(action, BRIDGE.input)),
                    None if path is None else str(path),
                    local(expected),
                    id=str(MANIFEST.value(entry, MF.name)),
                )


VECTORS = list(json_vectors())


class TestLiftingAJsonDocument:
    """Lifting a JSON document · engine/sparql.md, fixtures/lift/

    A Bridge lifts a JSON document to a graph as `engine/sparql.md` says, and must reproduce every vector: a document
    and the graph it lifts to. The reference lift is a second lift kept with these tests, written from that text alone,
    so a vector that passes here is one the text and the file agree on.
    """

    class TestGivenTheLiftManifest:
        def test_holds_json_vectors(self):
            """holds `json-scalars`, `json-names`, `skeleton-json`, `skeleton-json-bracket-path` and `skeleton-json-record-root`
            among its JSON vectors"""
            names = {vector.id for vector in VECTORS}
            assert {
                "json-scalars",
                "json-names",
                "skeleton-json",
                "skeleton-json-bracket-path",
                "skeleton-json-record-root",
            } <= names

    class TestGivenAJsonVector:
        """given a JSON vector"""

        @pytest.mark.parametrize(("document", "path", "expected"), VECTORS)
        def test_reproduces_the_expected_graph_in_the_reference_lift(self, document, path, expected):
            """reproduces the vector's expected graph in the reference lift

            A vector of the envelope skeleton is lifted with its `bridge:jsonPathOfEachRecord`; the failure lists the
            triples only one side holds. The two graphs are the same when each triple of one is a triple of the other,
            blank nodes aside, which may be named differently.
            """
            data = document.read_bytes()
            produced = json_lift.lifted(data) if path is None else json_lift.skeleton(data, path)
            wanted = Graph().parse(expected, format="nt")
            assert isomorphic(produced, wanted), (
                sorted(to_isomorphic(produced) - to_isomorphic(wanted)),
                sorted(to_isomorphic(wanted) - to_isomorphic(produced)),
            )

    class TestGivenADocumentThatIsNoJsonTextInUtf8HoldingAnObjectOrAnArray:
        """given a document that is no JSON text in UTF-8 holding an object or an array"""

        @pytest.mark.parametrize("name", NOT_LIFTED)
        def test_lifts_nothing_from_it(self, name):
            """lifts nothing from it

            Each document is a library case on the synthetic JSON adapter, refused as a document failure.
            """
            with pytest.raises(json_lift.NotLifted):
                json_lift.lifted((LIBRARY / name).read_bytes())

        @pytest.mark.parametrize("name", NOT_LIFTED)
        def test_is_a_library_case_refused_as_a_document_failure(self, name):
            """is a library case refused as a document failure"""
            assert name in refused_documents()

    class TestGivenARecordPath:
        def test_selects_the_same_records_written_dot_name_or_bracket_name(self):
            """selects the same records written `.name` or `['name']`"""
            value = json_lift.parsed(b'{"entry": [{"a": "1"}, {"b": "2"}]}')
            assert json_lift.records_of(value, "$.entry[*]") == json_lift.records_of(value, "$['entry'][*]")
            assert len(json_lift.records_of(value, "$.entry[*]")) == 2
