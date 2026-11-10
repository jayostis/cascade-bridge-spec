import functools
import shutil
from pathlib import Path

import pytest
from pyshacl import validate
from rdflib import RDF, BNode, Graph, Literal, Namespace, URIRef

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "fixtures"
SHAPES = Graph().parse(ROOT / "shapes" / "bridge.shapes.ttl", format="turtle")
VECTORS = ["lift", "versioning", "library"]

MF = Namespace("http://www.w3.org/2001/sw/DataAccess/tests/test-manifest#")
BRIDGE = Namespace("https://ns.cascadeprotocol.org/bridge/v1-draft#")
CASCADE = Namespace("https://ns.cascadeprotocol.org/cascade#")


def manifest_of(directory):
    manifest = directory.resolve() / "manifest.ttl"
    assert manifest.is_file(), f"{manifest} is not there"
    return manifest, Graph().parse(manifest, format="turtle", publicID=manifest.as_uri())


@functools.cache
def committed(vectors):
    return manifest_of(FIXTURES / vectors)[1]


def unaccounted(directory):
    directory = directory.resolve()
    manifest, graph = manifest_of(directory)
    base = directory.as_uri() + "/"
    listed = set(graph.items(graph.value(URIRef(manifest.as_uri()), MF.entries)))
    problems = [
        f"{entry} is not in mf:entries"
        for entry in sorted(set(graph.subjects(MF.name, None)))
        if entry not in listed or (entry, RDF.type, None) not in graph
    ]
    named = set()
    for iri in sorted({o for o in graph.objects() if isinstance(o, URIRef) and str(o).startswith(base)}):
        name = str(iri).removeprefix(base)
        if "#" in name:
            continue
        named.add(name)
        if "/" in name or not (directory / name).is_file():
            problems.append(f"{iri} is named, not a file in {directory.name}")
    for path in sorted(directory.iterdir()):
        if path.name != "manifest.ttl" and path.name not in named:
            problems.append(f"{path.name} is a vector no entry names")
    return problems


def said_about(graph):
    _, _, text = validate(graph, shacl_graph=SHAPES, advanced=True)
    return text


def entry_of(graph, name):
    return next(graph.subjects(MF.name, Literal(name)))


def action_of(graph, name):
    return graph.value(entry_of(graph, name), MF.action)


def no_media_type(graph):
    graph.remove((action_of(graph, "json-null"), BRIDGE.sourceMediaType, None))


def a_media_type_neither_lift_applies_to(graph):
    graph.set((action_of(graph, "attributes"), BRIDGE.sourceMediaType, Literal("text/csv")))


def an_element_name_and_a_json_path(graph):
    graph.add((action_of(graph, "skeleton-json"), BRIDGE.elementNameOfEachRecord, Literal("Unit")))


def neither_an_element_name_nor_a_json_path(graph):
    graph.remove((action_of(graph, "skeleton"), BRIDGE.elementNameOfEachRecord, None))


LIFT_TESTS_BROKEN = [
    pytest.param(
        no_media_type,
        "names exactly one bridge:sourceMediaType, which selects the lift",
        id="a lift test naming no media type",
    ),
    pytest.param(
        a_media_type_neither_lift_applies_to,
        "names exactly one bridge:sourceMediaType, which selects the lift",
        id="a lift test naming a media type neither lift applies to",
    ),
    pytest.param(
        an_element_name_and_a_json_path,
        "names exactly one of bridge:elementNameOfEachRecord",
        id="a skeleton test naming both an element name and a JSON path",
    ),
    pytest.param(
        neither_an_element_name_nor_a_json_path,
        "names exactly one of bridge:elementNameOfEachRecord",
        id="a skeleton test naming neither",
    ),
]


def first_versioning_result(graph):
    return graph.value(next(iter(sorted(graph.subjects(RDF.type, BRIDGE.VersioningTest), key=str))), MF.result)


def a_name_that_is_not_43_base64url_characters(graph):
    version = graph.value(first_versioning_result(graph), BRIDGE.expectedVersion)
    graph.set((version, BRIDGE.expectedName, URIRef("ni:///sha-256;itXWoNc3qVdBH28_n3ixhPuOww69tNEuA0dS-GrXLB8=")))


def no_expected_version(graph):
    graph.remove((first_versioning_result(graph), BRIDGE.expectedVersion, None))


VERSIONING_TESTS_BROKEN = [
    pytest.param(
        a_name_that_is_not_43_base64url_characters,
        "43 unpadded base64url characters",
        id="a version name that is not 43 base64url characters",
    ),
    pytest.param(no_expected_version, "bridge:expectedVersion for each version", id="no expected version"),
]


THE_VOCABULARYS_NAMING_VECTORS = """@prefix rdfs:    <http://www.w3.org/2000/01/rdf-schema#> .
@prefix mf:      <http://www.w3.org/2001/sw/DataAccess/tests/test-manifest#> .
@prefix qt:      <http://www.w3.org/2001/sw/DataAccess/tests/test-query#> .
@prefix bridge:  <https://ns.cascadeprotocol.org/bridge/v1-draft#> .
@prefix cascade: <https://ns.cascadeprotocol.org/cascade#> .

<> a mf:Manifest ;
  rdfs:label "naming vectors" ;
  mf:entries ( <#record-from-server> <#matcher-judgment> <#version> <#view-entry> <#base-url-case> <#base-url-userinfo> ) .

<#record-from-server> a bridge:NamingTest ;
  mf:name "record-from-server" ;
  rdfs:comment "A FHIR resource read from a server: the normalised base URL the client used, the resource type, the id." ;
  bridge:namingRule cascade:RecordFromServerNamingRule ;
  mf:action [ qt:query <RecordFromServerNamingRule.rq> ; bridge:nameInputs ( "https://fhir.example.org/api/FHIR/R4" "AllergyIntolerance" "eQ3xk2RtVb7Lm9Pw1aZy8A3" ) ] ;
  mf:result [ bridge:expectedName <urn:uuid:81ad3fab-98f1-890c-8abe-e93c84afd9e0> ] .

<#matcher-judgment> a bridge:NamingTest ;
  mf:name "matcher-judgment" ;
  rdfs:comment "A matcher judgment: the maker, the matcher rule, the justification, then the members and the versions used, each list written as its count and its items in code point order; listed here unsorted." ;
  bridge:namingRule cascade:MatcherJudgmentNamingRule ;
  mf:action [ bridge:nameInputs ( "https://ns.cascadeprotocol.org/cascade#CascadeMatcher" "https://ns.cascadeprotocol.org/cascade#SameCodeRule" "https://ns.cascadeprotocol.org/cascade#SameCode" ("urn:uuid:f83d6a9d-1d0e-84bd-826c-e3f00989c291" "urn:uuid:7435b3b8-2d93-8912-9d48-940c5870dc81") ("ni:///sha-256;eplyjFwBziuuDGwAXYG-OsnSc_l9nZRWlgn28AA-riY" "ni:///sha-256;Q2zb2hq5EC43OWgfnQ-uPPQDVO6_EFXtdyhjpb_8PnQ") ) ] ;
  mf:result [ bridge:expectedName <urn:uuid:b8cae3a2-1a7d-8821-8625-133247dfbbd0> ] .

<#version> a bridge:NamingTest ;
  mf:name "version" ;
  rdfs:comment "A version: the SHA-256 of the RDFC-1.0 canonical N-Quads of its triples, its subject urn:cascade:this-version, prov:specializationOf its record among them." ;
  bridge:namingRule cascade:VersionNamingRule ;
  mf:action [ bridge:input <content/version.nt> ] ;
  mf:result [ bridge:expectedName <ni:///sha-256;79qujwwA5pwIANwZGiRTK0GbMw0kE6P9xu3Rl0qg6ZE> ; bridge:canonicalContent <content/version.nq> ] .

<#view-entry> a bridge:NamingTest ;
  mf:name "view-entry" ;
  rdfs:comment "A view entry: the view's path in the pod, #, and the lower-case hex SHA-256 of its least member's IRI." ;
  bridge:namingRule cascade:ViewEntryNamingRule ;
  mf:action [ qt:query <ViewEntryNamingRule.rq> ; bridge:nameInputs ( "clinical/allergies.ttl" "urn:uuid:7435b3b8-2d93-8912-9d48-940c5870dc81" ) ] ;
  mf:result [ bridge:expectedName "clinical/allergies.ttl#f7e2d271f881267884f33508186278e064bb6b3621c3b568949bacd3a96a3584" ] .

<#base-url-case> a bridge:BaseUrlNormalisationTest ;
  mf:name "base-url-case" ;
  rdfs:comment "The scheme and host in lower case; the path as written." ;
  mf:action [ cascade:serverBaseUrl "HTTPS://FHIR.Example.ORG/api/FHIR/R4" ] ;
  mf:result [ cascade:serverBaseUrl "https://fhir.example.org/api/FHIR/R4" ] .

<#base-url-userinfo> a bridge:BaseUrlRefusalTest ;
  mf:name "base-url-userinfo" ;
  rdfs:comment "A base URL carrying userinfo is refused: a credential is never a name input." ;
  mf:action [ cascade:serverBaseUrl "https://user@fhir.example.org/r4" ] .
"""


def the_vocabularys_naming_vectors():
    return Graph().parse(data=THE_VOCABULARYS_NAMING_VECTORS, format="turtle", publicID="https://example.org/naming/")


def parts(graph, name):
    entry = entry_of(graph, name)
    return entry, graph.value(entry, MF.action), graph.value(entry, MF.result)


def no_naming_rule(graph):
    graph.remove((entry_of(graph, "record-from-server"), BRIDGE.namingRule, None))


def a_result_on_a_base_url_refusal_test(graph):
    result = BNode()
    graph.add((entry_of(graph, "base-url-userinfo"), MF.result, result))
    graph.add((result, CASCADE.serverBaseUrl, Literal("https://fhir.example.org/r4")))


def an_input_beside_a_query(graph):
    _, action, _ = parts(graph, "record-from-server")
    graph.remove((action, BRIDGE.nameInputs, None))
    graph.add((action, BRIDGE.input, URIRef("urn:x:content.nt")))


def a_name_input_that_is_not_a_plain_string(graph):
    _, action, _ = parts(graph, "record-from-server")
    graph.set((graph.value(action, BRIDGE.nameInputs), RDF.first, Literal(1)))


def an_empty_list_of_name_inputs(graph):
    _, action, _ = parts(graph, "view-entry")
    graph.set((action, BRIDGE.nameInputs, RDF.nil))


def a_nested_list_of_name_inputs_beside_a_query(graph):
    _, action, _ = parts(graph, "record-from-server")
    head = graph.value(action, BRIDGE.nameInputs)
    nested = BNode()
    graph.add((nested, RDF.first, Literal("x")))
    graph.add((nested, RDF.rest, RDF.nil))
    graph.set((head, RDF.first, nested))


def a_blank_node_as_the_expected_name(graph):
    _, _, result = parts(graph, "record-from-server")
    graph.set((result, BRIDGE.expectedName, BNode()))


def an_integer_as_the_expected_name(graph):
    _, _, result = parts(graph, "record-from-server")
    graph.set((result, BRIDGE.expectedName, Literal(7)))


def canonical_content_beside_no_input(graph):
    _, _, result = parts(graph, "record-from-server")
    graph.add((result, BRIDGE.canonicalContent, URIRef("urn:x:content.nq")))


NAMING_TESTS_BROKEN = [
    pytest.param(no_naming_rule, "names exactly one bridge:namingRule", id="no naming rule"),
    pytest.param(a_result_on_a_base_url_refusal_test, "carries no mf:result", id="a result on a base URL refusal test"),
    pytest.param(an_input_beside_a_query, "never a bridge:input beside a qt:query", id="an input beside a query"),
    pytest.param(
        a_name_input_that_is_not_a_plain_string,
        "is a plain string, or a list of plain strings",
        id="a name input that is not a plain string",
    ),
    pytest.param(an_empty_list_of_name_inputs, "lists at least one input", id="an empty list of name inputs"),
    pytest.param(
        a_nested_list_of_name_inputs_beside_a_query,
        "a nested list of inputs only without a qt:query",
        id="a nested list of name inputs beside a query",
    ),
    pytest.param(a_blank_node_as_the_expected_name, "an IRI or a plain string", id="a blank node as the expected name"),
    pytest.param(an_integer_as_the_expected_name, "an IRI or a plain string", id="an integer as the expected name"),
    pytest.param(
        canonical_content_beside_no_input, "only beside a bridge:input", id="canonical content beside no input"
    ),
]

VOCABULARY_MANIFEST = ROOT.parent / "cascade-vocabulary" / "tests" / "vectors" / "naming" / "manifest.ttl"


class TestManifestsThatListTheVectors:
    """Manifests that list the vectors · fixtures/*/manifest.ttl, shapes/bridge.shapes.ttl

    Each folder of vectors has a manifest that names every test in it, the files the test reads and what it expects,
    and the Cascade vocabulary's naming vectors have one in the same form. The Bridge shapes say what each kind of test
    must state, so an entry that would leave an engine guessing is refused with a sentence saying what is wrong.
    """

    class TestGivenAFolderOfVectors:
        @pytest.mark.parametrize("vectors", VECTORS)
        def test_conforms_to_the_bridge_shapes(self, vectors):
            """conforms to the Bridge shapes"""
            conforms, _, text = validate(committed(vectors), shacl_graph=SHAPES, advanced=True)
            assert conforms, text

        @pytest.mark.parametrize("vectors", VECTORS)
        def test_leaves_no_test_unlisted_and_no_file_unnamed_or_missing(self, vectors):
            """leaves no test unlisted and no file unnamed or missing

            Every entry with an `mf:name` is typed and in `mf:entries`; every file the manifest names is in the folder;
            every file in the folder is named.
            """
            assert unaccounted(FIXTURES / vectors) == []

    class TestGivenALiftOrSkeletonTestBrokenInOneWay:
        @pytest.mark.parametrize(("breaking", "words"), LIFT_TESTS_BROKEN)
        def test_reports_the_sentence_that_says_what_the_test_must_name(self, breaking, words):
            graph = Graph() + committed("lift")
            breaking(graph)
            assert words in said_about(graph)

    class TestGivenAVersioningTestBrokenInOneWay:
        @pytest.mark.parametrize(("breaking", "words"), VERSIONING_TESTS_BROKEN)
        def test_reports_the_sentence_that_says_what_the_test_must_state(self, breaking, words):
            graph = Graph() + committed("versioning")
            breaking(graph)
            assert words in said_about(graph)

    class TestGivenANamingTest:
        """given a naming test, as the vocabulary's naming manifest writes one"""

        def test_conforms_to_the_bridge_shapes(self):
            """conforms to the Bridge shapes"""
            conforms, _, text = validate(the_vocabularys_naming_vectors(), shacl_graph=SHAPES, advanced=True)
            assert conforms, text

        @pytest.mark.parametrize(("breaking", "words"), NAMING_TESTS_BROKEN)
        def test_reports_when_broken_in_one_way_the_sentence_that_says_what_is_wrong(self, breaking, words):
            """reports, broken in one way, the sentence that says what is wrong"""
            graph = the_vocabularys_naming_vectors()
            breaking(graph)
            assert words in said_about(graph)

    class TestGivenTheCascadeVocabularyCheckoutBesideThisRepository:
        """given the cascade-vocabulary checkout beside this repository"""

        @pytest.mark.skipif(
            not VOCABULARY_MANIFEST.is_file(),
            reason=f"no cascade-vocabulary checkout beside this repository (looked for {VOCABULARY_MANIFEST})",
        )
        def test_conforms_to_the_bridge_shapes_in_its_naming_manifest(self):
            """conforms to the Bridge shapes in its naming manifest"""
            graph = Graph().parse(VOCABULARY_MANIFEST, format="turtle", publicID=VOCABULARY_MANIFEST.as_uri())
            conforms, _, text = validate(graph, shacl_graph=SHAPES, advanced=True)
            assert conforms, text


class TestChecksOfTheCheckOnAManifestsFiles:
    """Checks of the check on a manifest's files · tests/specification/test_vector_manifests.py"""

    class TestUnaccounted:
        """`unaccounted()`"""

        def test_reports_a_file_that_no_entry_names(self, tmp_path):
            lift = shutil.copytree(FIXTURES / "lift", tmp_path / "lift")
            (lift / "unnamed.xml").write_text("<unnamed/>", encoding="utf-8")
            assert "unnamed.xml is a vector no entry names" in unaccounted(lift)

        def test_reports_an_entry_naming_a_file_that_is_not_there(self, tmp_path):
            lift = shutil.copytree(FIXTURES / "lift", tmp_path / "lift")
            (lift / "cdata.xml").unlink()
            assert any("cdata.xml is named, not a file in lift" in problem for problem in unaccounted(lift))
