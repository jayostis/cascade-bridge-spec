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


def held_and_graph(document, expected):
    held = [element for element in xml_text.elements(document.read_bytes()) if xml_text.holds_text(element)]
    return held, Graph().parse(expected, format="nt")


class TestTextValuesTheXmlLiftWritesOnAnElement:
    """Text values the XML lift writes on an element · engine/sparql.md, fixtures/lift/

    Beside its children, the XML lift writes two readings of an element's text: its text content, every character under
    it joined, and its text with element breaks, a line for each run of text between the elements an adapter names as
    breaking text. Reference text values, written from `engine/sparql.md` alone, show that the text and the vectors
    agree.
    """

    class TestGivenTheLiftManifest:
        def test_names_elements_breaking_text(self):
            """names elements breaking text for `text-with-element-breaks-table`, `text-with-element-breaks-paragraphs` and
            `text-with-element-breaks-inline`"""
            breaking = {vector.id for vector in VECTORS if vector.values[1]}
            assert {
                "text-with-element-breaks-table",
                "text-with-element-breaks-paragraphs",
                "text-with-element-breaks-inline",
            } <= breaking

    class TestGivenAnXmlVector:
        """given an XML vector"""

        @pytest.mark.parametrize(("document", "breaking", "expected"), VECTORS)
        def test_states_on_each_element_holding_text_the_text_content_the_reference_gives_it(
            self, document, breaking, expected
        ):
            """states on each element holding text the text content the reference gives it

            Counted by the element's type and the text, since a blank node has no name to match by.
            """
            held, graph = held_and_graph(document, expected)
            assert written(graph, TEXT_CONTENT) == Counter((type_of(e), xml_text.text_content(e)) for e in held)

        @pytest.mark.parametrize(("document", "breaking", "expected"), VECTORS)
        def test_states_the_text_with_element_breaks_the_reference_gives_and_none_where_no_element_is_named(
            self, document, breaking, expected
        ):
            held, graph = held_and_graph(document, expected)
            assert written(graph, BRIDGE.textWithElementBreaks) == Counter(
                (type_of(e), xml_text.text_with_element_breaks(e, breaking)) for e in held if breaking
            )
