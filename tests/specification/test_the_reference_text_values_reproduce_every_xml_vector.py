from collections import Counter
from pathlib import Path

import pytest
from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import RDF

import json_lift
import xml_text

ROOT = Path(__file__).resolve().parents[2]
LIFT = ROOT / "fixtures" / "lift"
MF = Namespace("http://www.w3.org/2001/sw/DataAccess/tests/test-manifest#")
BRIDGE = Namespace("https://ns.cascadeprotocol.org/bridge/v1-draft#")
TEXT_CONTENT = URIRef("https://dom.spec.whatwg.org/#dom-node-textcontent")
ROOT_TYPE = URIRef("http://sparql.xyz/facade-x/ns/root")

MANIFEST = Graph().parse(LIFT / "manifest.ttl", format="turtle", publicID=(LIFT / "manifest.ttl").as_uri())


def local(iri):
    return LIFT / str(iri).rsplit("/", 1)[1]


def xml_vectors():
    for entry in sorted(MANIFEST.subjects(RDF.type, BRIDGE.LiftTest)):
        action = MANIFEST.value(entry, MF.action)
        if not json_lift.applies_to(str(MANIFEST.value(action, BRIDGE.sourceMediaType))):
            expected = MANIFEST.value(MANIFEST.value(entry, MF.result), BRIDGE.expectedGraph)
            yield pytest.param(
                local(MANIFEST.value(action, BRIDGE.input)),
                frozenset(str(name) for name in MANIFEST.objects(action, BRIDGE.elementNameBreakingText)),
                local(expected),
                id=str(MANIFEST.value(entry, MF.name)),
            )


VECTORS = list(xml_vectors())


def type_of(element):
    namespace, _, name = element.tag[1:].partition("}") if element.tag.startswith("{") else ("", "", element.tag)
    named = str(json_lift.named(name))
    return URIRef(namespace + named[len(json_lift.DATA) :]) if namespace else URIRef(named)


def written(graph, predicate):
    return Counter(
        (next(kind for kind in graph.objects(subject, RDF.type) if kind != ROOT_TYPE), str(value))
        for subject, value in graph.subject_objects(predicate)
    )


def test_the_lift_manifest_names_the_elements_breaking_text_in_the_vectors_of_text_with_element_breaks():
    breaking = {vector.id for vector in VECTORS if vector.values[1]}
    assert {
        "text-with-element-breaks-table",
        "text-with-element-breaks-paragraphs",
        "text-with-element-breaks-inline",
    } <= breaking


@pytest.mark.parametrize(("document", "breaking", "expected"), VECTORS)
def test_the_reference_text_values_are_the_vectors(document, breaking, expected):
    held = [element for element in xml_text.elements(document.read_bytes()) if xml_text.holds_text(element)]
    graph = Graph().parse(expected, format="nt")
    assert written(graph, TEXT_CONTENT) == Counter((type_of(e), xml_text.text_content(e)) for e in held)
    assert written(graph, BRIDGE.textWithElementBreaks) == Counter(
        (type_of(e), xml_text.text_with_element_breaks(e, breaking)) for e in held if breaking
    )
