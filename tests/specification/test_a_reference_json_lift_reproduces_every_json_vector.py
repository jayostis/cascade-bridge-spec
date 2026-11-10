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
            """holds `json-scalars`, `json-names`, `skeleton-json` and `skeleton-json-record-root` among its JSON vectors"""
            names = {vector.id for vector in VECTORS}
            assert {"json-scalars", "json-names", "skeleton-json", "skeleton-json-record-root"} <= names

    class TestGivenAJsonVector:
        """given a JSON vector"""

        @pytest.mark.parametrize(("document", "path", "expected"), VECTORS)
        def test_reproduces_the_expected_graph_in_the_reference_lift(self, document, path, expected):
            """reproduces the vector's expected graph in the reference lift

            A vector of the envelope skeleton is lifted with its `bridge:jsonPathOfEachRecord`; the failure lists the
            triples only one side holds.
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

        @pytest.mark.parametrize(
            "data",
            [
                pytest.param(b'\xef\xbb\xbf{"a": "1"}', id="a byte order mark"),
                pytest.param(b'{"a": "\\ud800"}', id="a lone surrogate in a string"),
                pytest.param(b'{"\\udc00": "1"}', id="a lone surrogate in a name"),
                pytest.param(b'"a string"', id="a string as the value"),
                pytest.param(b"12", id="a number as the value"),
                pytest.param(b'{"a": NaN}', id="NaN"),
                pytest.param('{"a": "é"}'.encode("latin-1"), id="text that is not UTF-8"),
            ],
        )
        def test_lifts_nothing_from_it(self, data):
            """lifts nothing from it

            No vector shows this: a lift vector states a graph, and no library case feeds a JSON document.
            """
            with pytest.raises(json_lift.NotLifted):
                json_lift.lifted(data)

    class TestGivenARecordPath:
        def test_selects_the_same_records_written_dot_name_or_bracket_name(self):
            """selects the same records written `.name` or `['name']`"""
            value = json_lift.parsed(b'{"entry": [{"a": "1"}, {"b": "2"}]}')
            assert json_lift.records_of(value, "$.entry[*]") == json_lift.records_of(value, "$['entry'][*]")
            assert len(json_lift.records_of(value, "$.entry[*]")) == 2
