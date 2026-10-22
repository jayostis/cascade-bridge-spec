import shutil
from pathlib import Path

import pytest
from pyshacl import validate
from rdflib import RDF, BNode, Graph, Literal, Namespace, URIRef

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "fixtures"
SHAPES = ROOT / "shapes" / "bridge.shapes.ttl"
VECTORS = ["lift", "versioning", "library"]

MF = Namespace("http://www.w3.org/2001/sw/DataAccess/tests/test-manifest#")
BRIDGE = Namespace("https://ns.cascadeprotocol.org/bridge/v1-draft#")
CASCADE = Namespace("https://ns.cascadeprotocol.org/cascade#")


def manifest_of(directory):
    manifest = directory.resolve() / "manifest.ttl"
    assert manifest.is_file(), f"{manifest} is not there"
    return manifest, Graph().parse(manifest, format="turtle", publicID=manifest.as_uri())


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


@pytest.mark.parametrize("vectors", VECTORS)
def test_a_vector_manifest_conforms_to_the_bridge_shapes(vectors):
    _, graph = manifest_of(FIXTURES / vectors)
    conforms, _, text = validate(graph, shacl_graph=Graph().parse(SHAPES, format="turtle"), advanced=True)
    assert conforms, text


@pytest.mark.parametrize("vectors", VECTORS)
def test_a_vector_manifest_lists_every_test_and_names_every_vector(vectors):
    assert unaccounted(FIXTURES / vectors) == []


def test_a_vector_no_entry_names_is_reported(tmp_path):
    lift = shutil.copytree(FIXTURES / "lift", tmp_path / "lift")
    (lift / "unnamed.xml").write_text("<unnamed/>", encoding="utf-8")
    assert "unnamed.xml is a vector no entry names" in unaccounted(lift)


def test_an_entry_naming_a_file_that_is_not_there_is_reported(tmp_path):
    lift = shutil.copytree(FIXTURES / "lift", tmp_path / "lift")
    (lift / "cdata.xml").unlink()
    assert any("cdata.xml is named, not a file in lift" in problem for problem in unaccounted(lift))


def said_about(graph):
    _, _, text = validate(graph, shacl_graph=Graph().parse(SHAPES, format="turtle"), advanced=True)
    return text


def action_of(graph, name):
    entry = next(graph.subjects(MF.name, Literal(name)))
    return graph.value(entry, MF.action)


def test_a_lift_test_naming_no_media_type_is_refused():
    _, graph = manifest_of(FIXTURES / "lift")
    graph.remove((action_of(graph, "json-null"), BRIDGE.sourceMediaType, None))
    assert "names exactly one bridge:sourceMediaType, which selects the lift" in said_about(graph)


def test_a_lift_test_naming_a_media_type_neither_lift_applies_to_is_refused():
    _, graph = manifest_of(FIXTURES / "lift")
    graph.set((action_of(graph, "attributes"), BRIDGE.sourceMediaType, Literal("text/csv")))
    assert "names exactly one bridge:sourceMediaType, which selects the lift" in said_about(graph)


def test_a_skeleton_test_naming_both_an_element_name_and_a_json_path_is_refused():
    _, graph = manifest_of(FIXTURES / "lift")
    graph.add((action_of(graph, "skeleton-json"), BRIDGE.elementNameOfEachRecord, Literal("Unit")))
    assert "names exactly one of bridge:elementNameOfEachRecord" in said_about(graph)


def test_a_skeleton_test_naming_neither_an_element_name_nor_a_json_path_is_refused():
    _, graph = manifest_of(FIXTURES / "lift")
    graph.remove((action_of(graph, "skeleton"), BRIDGE.elementNameOfEachRecord, None))
    assert "names exactly one of bridge:elementNameOfEachRecord" in said_about(graph)


def test_a_library_case_naming_a_failure_kind_that_is_not_one_of_the_six_is_refused():
    kinds = set(Graph().parse(ROOT / "vocab" / "bridge.ttl", format="turtle").subjects(RDF.type, BRIDGE.FailureKind))
    assert len(kinds) == 6, kinds
    _, graph = manifest_of(FIXTURES / "library")
    naming = [(subject, predicate, kind) for subject, predicate, kind in graph if kind in kinds]
    assert naming, "no library case names a failure kind"
    subject, predicate, kind = naming[0]
    graph.remove((subject, predicate, kind))
    graph.add((subject, predicate, BRIDGE.NotAFailureKind))
    said = said_about(graph)
    assert "Conforms: False" in said
    assert all(str(kind).removeprefix(str(BRIDGE)) in said for kind in kinds), said


THE_VOCABULARYS_NAMING_VECTORS = """@prefix rdfs:    <http://www.w3.org/2000/01/rdf-schema#> .
@prefix mf:      <http://www.w3.org/2001/sw/DataAccess/tests/test-manifest#> .
@prefix qt:      <http://www.w3.org/2001/sw/DataAccess/tests/test-query#> .
@prefix bridge:  <https://ns.cascadeprotocol.org/bridge/v1-draft#> .
@prefix cascade: <https://ns.cascadeprotocol.org/cascade#> .

<> a mf:Manifest ;
  mf:entries ( <#record-from-server> <#claim> <#version> <#view-entry> <#base-url-case> <#base-url-userinfo> ) .

<#record-from-server> a bridge:NamingTest ;
  mf:name "record-from-server" ;
  bridge:namingRule cascade:RecordFromServerNamingRule ;
  mf:action [ qt:query <RecordFromServerNamingRule.rq> ; bridge:nameInputs ( "https://fhir.example.org/r4" "Patient" "1" ) ] ;
  mf:result [ bridge:expectedName <urn:uuid:81ad3fab-98f1-890c-8abe-e93c84afd9e0> ] .

<#claim> a bridge:NamingTest ;
  mf:name "claim" ;
  bridge:namingRule cascade:ClaimNamingRule ;
  mf:action [ bridge:nameInputs ( "maker" "rule" "justification" ( "m2" "m1" ) ( "u1" ) ) ] ;
  mf:result [ bridge:expectedName <urn:uuid:35ee949a-9a6f-8cbb-81ef-378e145711f0> ] .

<#version> a bridge:NamingTest ;
  mf:name "version" ;
  bridge:namingRule cascade:VersionNamingRule ;
  mf:action [ bridge:input <content/version.nt> ] ;
  mf:result [ bridge:expectedName <ni:///sha-256;79qujwwA5pwIANwZGiRTK0GbMw0kE6P9xu3Rl0qg6ZE> ;
              bridge:canonicalContent <content/version.nq> ] .

<#view-entry> a bridge:NamingTest ;
  mf:name "view-entry" ;
  bridge:namingRule cascade:ViewEntryNamingRule ;
  mf:action [ qt:query <ViewEntryNamingRule.rq> ; bridge:nameInputs ( "clinical/allergies.ttl" "urn:uuid:1" ) ] ;
  mf:result [ bridge:expectedName "clinical/allergies.ttl#f7e2d271" ] .

<#base-url-case> a bridge:BaseUrlNormalisationTest ;
  mf:name "base-url-case" ;
  mf:action [ cascade:serverBaseUrl "HTTPS://FHIR.Example.ORG/r4/" ] ;
  mf:result [ cascade:serverBaseUrl "https://fhir.example.org/r4" ] .

<#base-url-userinfo> a bridge:BaseUrlRefusalTest ;
  mf:name "base-url-userinfo" ;
  mf:action [ cascade:serverBaseUrl "https://user@fhir.example.org/r4" ] .
"""


def the_vocabularys_naming_vectors():
    return Graph().parse(data=THE_VOCABULARYS_NAMING_VECTORS, format="turtle", publicID="https://example.org/naming/")


def entry_of(graph, name):
    return next(graph.subjects(MF.name, Literal(name)))


def test_the_manifest_form_of_the_vocabularys_naming_vectors_conforms_to_the_bridge_shapes():
    conforms, _, text = validate(
        the_vocabularys_naming_vectors(), shacl_graph=Graph().parse(SHAPES, format="turtle"), advanced=True
    )
    assert conforms, text


def test_a_naming_test_naming_no_naming_rule_is_refused():
    graph = the_vocabularys_naming_vectors()
    graph.remove((entry_of(graph, "record-from-server"), BRIDGE.namingRule, None))
    assert "names exactly one bridge:namingRule" in said_about(graph)


def test_a_base_url_refusal_test_carrying_a_result_is_refused():
    graph = the_vocabularys_naming_vectors()
    result = BNode()
    graph.add((entry_of(graph, "base-url-userinfo"), MF.result, result))
    graph.add((result, CASCADE.serverBaseUrl, Literal("https://fhir.example.org/r4")))
    assert "carries no mf:result" in said_about(graph)
