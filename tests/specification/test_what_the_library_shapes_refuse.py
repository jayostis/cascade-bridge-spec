import functools
from pathlib import Path

import pytest
from pyshacl import validate
from rdflib import RDF, BNode, Graph, Literal, Namespace, URIRef

ROOT = Path(__file__).resolve().parents[2]
LIBRARY = ROOT / "fixtures" / "library" / "manifest.ttl"
SHAPES = Graph().parse(ROOT / "shapes" / "bridge.shapes.ttl", format="turtle")

MF = Namespace("http://www.w3.org/2001/sw/DataAccess/tests/test-manifest#")
BRIDGE = Namespace("https://ns.cascadeprotocol.org/bridge/v1-draft#")


@functools.cache
def committed():
    return Graph().parse(LIBRARY, format="turtle", publicID=LIBRARY.as_uri())


def library():
    return Graph() + committed()


def said_about(graph):
    conforms, _, text = validate(graph, shacl_graph=SHAPES, advanced=True)
    return conforms, text


def calls_of(graph, name):
    case = next(graph.subjects(MF.name, Literal(name)))
    return list(graph.items(graph.value(case, MF.action)))


def ask_before_any_load(graph):
    calls = calls_of(graph, "ask-answers-the-detect-query")
    head = graph.value(next(graph.subjects(MF.name, Literal("ask-answers-the-detect-query"))), MF.action)
    graph.set((head, RDF.first, calls[1]))


def missing_file_with_another_kind(graph):
    call = calls_of(graph, "a-mapping-missing-from-the-adapter-map-then-supplied")[0]
    graph.set((call, BRIDGE.failure, BRIDGE.adapterFailure))


def missing_file_kind_naming_no_file(graph):
    call = calls_of(graph, "a-mapping-missing-from-the-adapter-map-then-supplied")[0]
    graph.remove((call, BRIDGE.missingFile, None))


def convert_expecting_nothing(graph):
    call = calls_of(graph, "convert-with-no-vocabulary")[1]
    graph.remove((call, BRIDGE.expectedGraph, None))


def convert_in_another_format(graph):
    call = calls_of(graph, "convert-with-no-vocabulary")[1]
    graph.set((call, BRIDGE.graphFormat, Literal("rdfxml")))


def a_map_with_an_unknown_term(graph):
    call = calls_of(graph, "a-file-missing-from-the-map-under-test")[0]
    graph.add((graph.value(call, BRIDGE.adapterFiles), BRIDGE.withheld, Literal("fixtures/")))


def a_map_whose_iri_is_no_directory(graph):
    call = calls_of(graph, "a-file-missing-from-the-map-under-test")[0]
    graph.set((graph.value(call, BRIDGE.adapterFiles), BRIDGE.iri, URIRef("https://example.org/adapter")))


def a_call_of_no_type(graph):
    call = calls_of(graph, "test-with-no-vocabulary")[0]
    graph.remove((call, RDF.type, None))


def a_failing_convert_expecting_findings(graph):
    call = calls_of(graph, "facts-that-do-not-parse")[1]
    graph.add((call, BRIDGE.expectedFindings, URIRef("https://example.org/findings.ttl")))


def an_ask_expecting_an_answer_and_a_failure(graph):
    call = calls_of(graph, "ask-answers-the-detect-query")[1]
    graph.add((call, BRIDGE.failure, BRIDGE.documentFailure))


def a_document_given_no_iri(graph):
    call = calls_of(graph, "ask-answers-the-detect-query")[2]
    graph.remove((graph.value(call, BRIDGE.document), BRIDGE.iri, None))


def a_manifest_listing_no_entries(graph):
    graph.remove((URIRef(LIBRARY.as_uri()), MF.entries, None))


def a_result_on_the_case(graph):
    case = next(graph.subjects(MF.name, Literal("test-with-no-vocabulary")))
    graph.add((case, MF.result, BNode()))


REFUSED = {
    "an ask before any load": (ask_before_any_load, "comes after a bridge:LoadCall"),
    "a missing file with another kind": (missing_file_with_another_kind, "fails with bridge:fileMissingFailure"),
    "the missing-file kind naming no file": (missing_file_kind_naming_no_file, "names the bridge:missingFile"),
    "a convert expecting nothing": (
        convert_expecting_nothing,
        "exactly one of bridge:expectedGraph and bridge:failure",
    ),
    "a convert in another format": (convert_in_another_format, "turtle or ntriples"),
    "a map with an unknown term": (a_map_with_an_unknown_term, "carries only a bridge:iri, a bridge:directory"),
    "a map whose IRI is no directory": (a_map_whose_iri_is_no_directory, "ending in /, that each key resolves"),
    "a call of no type": (a_call_of_no_type, "typed with exactly one of bridge:DescribeCall"),
    "a failing convert expecting findings": (a_failing_convert_expecting_findings, "names no bridge:expectedFindings"),
    "an ask expecting an answer and a failure": (
        an_ask_expecting_an_answer_and_a_failure,
        "exactly one of bridge:expectedAnswer and bridge:failure",
    ),
    "a document given no IRI": (a_document_given_no_iri, "carries exactly one bridge:iri"),
    "a result on the case": (a_result_on_the_case, "has no mf:result"),
    "a manifest listing no entries": (a_manifest_listing_no_entries, "exactly one mf:entries list"),
}


class TestLibraryCasesAnEngineIsRunThrough:
    """Library cases an engine is run through · fixtures/library/manifest.ttl, shapes/bridge.shapes.ttl

    An engine's library is what a program calls: describe, load, ask, convert and test, bytes in and bytes out. A
    library case lists calls in order and what each must return or fail with, and the Bridge shapes refuse a case that
    could not be judged, with a sentence saying why.
    """

    class TestGivenACaseOfTheLibraryManifestBrokenInOneWay:
        @pytest.mark.parametrize("case", REFUSED)
        def test_reports_the_sentence_that_says_why_the_case_cannot_be_judged(self, case):
            breaking, message = REFUSED[case]
            graph = library()
            breaking(graph)
            conforms, text = said_about(graph)
            assert not conforms
            assert message in text, text

    class TestGivenACallThatNamesAFailureKind:
        def test_lists_every_failure_kind_the_bridge_vocabulary_declares_when_a_call_names_another(self):
            """lists every failure kind the Bridge vocabulary declares when a call names another"""
            kinds = set(
                Graph().parse(ROOT / "vocab" / "bridge.ttl", format="turtle").subjects(RDF.type, BRIDGE.FailureKind)
            )
            assert kinds, "the Bridge vocabulary declares no bridge:FailureKind"
            graph = library()
            naming = [(subject, predicate, kind) for subject, predicate, kind in graph if kind in kinds]
            assert naming, "no library case names a failure kind"
            subject, predicate, kind = naming[0]
            graph.remove((subject, predicate, kind))
            graph.add((subject, predicate, BRIDGE.NotAFailureKind))
            _, said = said_about(graph)
            assert "Conforms: False" in said
            assert all(str(kind).removeprefix(str(BRIDGE)) in said for kind in kinds), said
