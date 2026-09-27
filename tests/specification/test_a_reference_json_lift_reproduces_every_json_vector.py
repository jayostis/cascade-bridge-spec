from pathlib import Path

import pytest
from rdflib import Graph, Namespace, URIRef
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


def test_the_lift_manifest_holds_json_lift_and_skeleton_vectors():
    names = {vector.id for vector in VECTORS}
    assert {"json-scalars", "json-names", "skeleton-json", "skeleton-json-record-root"} <= names


@pytest.mark.parametrize(("document", "path", "expected"), VECTORS)
def test_the_reference_lift_reproduces_the_vector(document, path, expected):
    data = document.read_bytes()
    produced = json_lift.lifted(data) if path is None else json_lift.skeleton(data, path)
    wanted = Graph().parse(expected, format="nt")
    assert isomorphic(produced, wanted), (
        sorted(to_isomorphic(produced) - to_isomorphic(wanted)),
        sorted(to_isomorphic(wanted) - to_isomorphic(produced)),
    )


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
def test_a_document_that_is_not_a_json_text_in_utf8_holding_an_object_or_an_array_is_not_lifted(data):
    with pytest.raises(json_lift.NotLifted):
        json_lift.lifted(data)


def test_a_name_selector_is_the_same_record_path_written_either_way():
    value = json_lift.parsed(b'{"entry": [{"a": "1"}, {"b": "2"}]}')
    assert json_lift.records_of(value, "$.entry[*]") == json_lift.records_of(value, "$['entry'][*]")
    assert len(json_lift.records_of(value, "$.entry[*]")) == 2


def test_the_record_path_dollar_is_the_documents_value():
    value = json_lift.parsed(b'{"resourceType": "Example"}')
    assert json_lift.records_of(value, "$") == [value]


@pytest.mark.parametrize("path", ["$..entry", "$.entry[0]", "$.entry[?@.a]", "entry", "$.entry[0:2]"])
def test_a_record_path_outside_the_subset_is_refused(path):
    with pytest.raises(ValueError):
        json_lift.segments_of(path)


@pytest.mark.parametrize(
    ("media_type", "json"),
    [
        ("application/json", True),
        ("application/fhir+json", True),
        ("application/xml", False),
        ("text/xml", False),
        ("application/example+xml", False),
    ],
)
def test_the_media_type_selects_the_lift(media_type, json):
    assert json_lift.applies_to(media_type) is json


def test_the_contract_names_the_media_types_each_lift_applies_to(sparql_contract):
    assert (
        "the XML lift to `application/xml`, `text/xml` and a media type with the `+xml` suffix, the JSON lift to "
        "`application/json` and a media type with the `+json` suffix" in sparql_contract
    )


def test_a_member_named_as_an_element_is_appended_to_the_data_namespace():
    assert json_lift.named("given name") == URIRef("http://sparql.xyz/facade-x/data/given%20name")
