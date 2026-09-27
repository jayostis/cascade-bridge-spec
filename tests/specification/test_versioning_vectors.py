from pathlib import Path

import pytest
from pyshacl import validate
from rdflib import RDF, Graph, Namespace, URIRef

from recomputed import PLACEHOLDER, canonical_nquads, ni_name, parsed_ntriples, versions

ROOT = Path(__file__).resolve().parents[2]
VERSIONING = ROOT / "fixtures" / "versioning"
SHAPES = Graph().parse(ROOT / "shapes" / "bridge.shapes.ttl", format="turtle")
MANIFEST_IRI = (VERSIONING / "manifest.ttl").as_uri()
MANIFEST = Graph().parse(VERSIONING / "manifest.ttl", format="turtle", publicID=MANIFEST_IRI)
MF = Namespace("http://www.w3.org/2001/sw/DataAccess/tests/test-manifest#")
BRIDGE = Namespace("https://ns.cascadeprotocol.org/bridge/v1-draft#")
VECTORS = sorted(MANIFEST.subjects(RDF.type, BRIDGE.VersioningTest), key=str)


def vector_id(test):
    return str(test).rpartition("#")[2]


def file_of(iri):
    return VERSIONING / str(iri).rpartition("/")[2]


def text_of(iri):
    return file_of(iri).read_bytes().decode("utf-8")


def mapped(test):
    return parsed_ntriples(text_of(MANIFEST.value(MANIFEST.value(test, MF.action), BRIDGE.input)))


def result_of(test):
    return MANIFEST.value(test, MF.result)


def expected_versions(test):
    return {
        str(MANIFEST.value(version, BRIDGE.expectedName)): text_of(MANIFEST.value(version, BRIDGE.canonicalContent))
        for version in MANIFEST.objects(result_of(test), BRIDGE.expectedVersion)
    }


def names_of(name):
    return set(expected_versions(URIRef(f"{MANIFEST_IRI}#{name}")))


@pytest.mark.parametrize("test", VECTORS, ids=vector_id)
def test_a_versions_canonical_content_is_its_triples_with_the_placeholder_in_its_place(test):
    named, _ = versions(mapped(test))
    assert sorted(named.values()) == sorted(expected_versions(test).values())


@pytest.mark.parametrize("test", VECTORS, ids=vector_id)
def test_a_versions_name_is_the_ni_sha256_of_its_canonical_content(test):
    for name, nquads in expected_versions(test).items():
        assert ni_name(nquads.encode("utf-8")) == name


@pytest.mark.parametrize("test", VECTORS, ids=vector_id)
def test_the_canonical_content_is_already_in_canonical_form(test):
    for nquads in expected_versions(test).values():
        assert canonical_nquads(parsed_ntriples(nquads)) == nquads


@pytest.mark.parametrize("test", VECTORS, ids=vector_id)
def test_the_output_is_the_mapped_graph_with_every_version_and_nested_node_named(test):
    _, graph = versions(mapped(test))
    assert graph == parsed_ntriples(text_of(MANIFEST.value(result_of(test), BRIDGE.expectedGraph)))


@pytest.mark.parametrize("test", VECTORS, ids=vector_id)
def test_no_placeholder_is_left_in_the_output(test):
    assert PLACEHOLDER not in text_of(MANIFEST.value(result_of(test), BRIDGE.expectedGraph))


def test_the_same_content_twice_is_one_version():
    assert names_of("allergy") == names_of("allergy-again")


def test_the_same_content_on_two_records_is_two_versions():
    assert names_of("allergy").isdisjoint(names_of("allergy-on-another-record"))


def test_a_literal_is_hashed_as_the_mapping_wrote_it_not_as_a_store_gives_it_back():
    assert names_of("typed-literals").isdisjoint(names_of("typed-literals-round-tripped"))
    assert '"2.00"^^<http://www.w3.org/2001/XMLSchema#decimal>' in (
        VERSIONING / "typed-literals.nq"
    ).read_bytes().decode("utf-8")


def test_each_record_of_a_source_record_gets_its_own_version():
    assert len(names_of("two-versions")) == 2


def test_a_version_holding_a_blank_node_is_beyond_the_rule():
    with pytest.raises(ValueError):
        parsed_ntriples('_:b <http://example.org/p> "o" .\n')


def test_a_version_name_that_is_not_an_ni_sha256_name_is_refused():
    manifest = Graph() + MANIFEST
    version = manifest.value(result_of(VECTORS[0]), BRIDGE.expectedVersion)
    manifest.set((version, BRIDGE.expectedName, URIRef("ni:///sha-256;itXWoNc3qVdBH28_n3ixhPuOww69tNEuA0dS-GrXLB8=")))
    conforms, _, text = validate(manifest, shacl_graph=SHAPES, advanced=True)
    assert not conforms and "43 unpadded base64url characters" in text


def test_a_versioning_test_without_an_expected_version_is_refused():
    manifest = Graph() + MANIFEST
    manifest.remove((result_of(VECTORS[0]), BRIDGE.expectedVersion, None))
    conforms, _, text = validate(manifest, shacl_graph=SHAPES, advanced=True)
    assert not conforms and "bridge:expectedVersion for each version" in text
