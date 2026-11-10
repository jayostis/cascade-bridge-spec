from pathlib import Path

import pytest
from rdflib import RDF, BNode, Graph, Literal, Namespace, URIRef
from rdflib.compare import isomorphic

from versioning import PLACEHOLDER, canonical_nquads, ni_name, parsed_ntriples, versions

ROOT = Path(__file__).resolve().parents[2]
VERSIONING = ROOT / "fixtures" / "versioning"
MANIFEST_IRI = (VERSIONING / "manifest.ttl").as_uri()
MANIFEST = Graph().parse(VERSIONING / "manifest.ttl", format="turtle", publicID=MANIFEST_IRI)
MF = Namespace("http://www.w3.org/2001/sw/DataAccess/tests/test-manifest#")
BRIDGE = Namespace("https://ns.cascadeprotocol.org/bridge/v1-draft#")
VECTORS = sorted(MANIFEST.subjects(RDF.type, BRIDGE.VersioningTest), key=str)


def as_rdflib(triples):
    def term(node):
        if node[0] == "iri":
            return URIRef(node[1])
        if node[0] == "blank":
            return BNode(node[1])
        return Literal(node[1], datatype=URIRef(node[2]))

    graph = Graph()
    for triple in triples:
        graph.add(tuple(map(term, triple)))
    return graph


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


class TestNamingTheVersionsOfAMappedGraph:
    """Naming the versions of a mapped graph · engine/stages.md, fixtures/versioning/

    A mapping writes each version of a record under an IRI of its own choosing; a Bridge renames the version to the
    SHA-256 of its canonical content, so the same content always gets the same name, and keeps one version of each
    record. A versioning vector is a mapped graph, the canonical content of each version, and the graph a Bridge
    writes from it; a second implementation kept with these tests shows each vector follows the rule.
    """

    class TestGivenAVersioningVector:
        @pytest.mark.parametrize("test", VECTORS, ids=vector_id)
        def test_states_the_canonical_content_of_each_version(self, test):
            """states as each version's canonical content its statements in the mapped graph, the placeholder in place of its IRI"""
            named, _ = versions(mapped(test))
            assert sorted(named.values()) == sorted(expected_versions(test).values())

        @pytest.mark.parametrize("test", VECTORS, ids=vector_id)
        def test_names_each_version_by_the_digest_of_its_canonical_content(self, test):
            """names each version `ni:///sha-256;` and the digest of its canonical content"""
            for name, nquads in expected_versions(test).items():
                assert ni_name(nquads.encode("utf-8")) == name

        @pytest.mark.parametrize("test", VECTORS, ids=vector_id)
        def test_keeps_each_canonical_content_sorted_one_statement_to_a_line(self, test):
            """keeps each canonical content sorted, one statement to a line

            Each literal is written as the mapping wrote it, with the datatype and the digits it had, never as a store
            gives it back; so `"2.00"` stays `"2.00"`. The lines are in the order that sorting their text gives.
            """
            for nquads in expected_versions(test).values():
                assert canonical_nquads(parsed_ntriples(nquads)) == nquads

        @pytest.mark.parametrize("test", VECTORS, ids=vector_id)
        def test_expects_the_mapped_graph_with_every_kept_version_and_its_nested_nodes_renamed(self, test):
            """expects the mapped graph with every kept version and its nested nodes renamed

            Where a mapping wrote two versions of one record, the graph holds the one a Bridge keeps and nothing of
            the other.
            """
            _, graph = versions(mapped(test))
            expected = parsed_ntriples(text_of(MANIFEST.value(result_of(test), BRIDGE.expectedGraph)))
            assert isomorphic(as_rdflib(graph), as_rdflib(expected))

        @pytest.mark.parametrize("test", VECTORS, ids=vector_id)
        def test_leaves_no_placeholder_in_the_expected_graph(self, test):
            assert PLACEHOLDER not in text_of(MANIFEST.value(result_of(test), BRIDGE.expectedGraph))

    class TestGivenTwoVectorsThatDifferInOneWay:
        def test_names_the_versions_of_the_same_content_converted_twice_alike(self):
            """names the versions of `allergy` and of `allergy-again`, the same content converted twice, alike"""
            assert names_of("allergy") == names_of("allergy-again")

        def test_names_the_versions_of_the_same_content_on_another_record_otherwise(self):
            """names the versions of `allergy-on-another-record`, the same content on another record, otherwise than `allergy`"""
            assert names_of("allergy").isdisjoint(names_of("allergy-on-another-record"))

        def test_names_a_literal_as_the_mapping_wrote_it_otherwise_than_as_a_store_gives_it_back(self):
            """names `typed-literals` otherwise than `typed-literals-round-tripped`, whose `"2.00"` a store gave back as `"2"`"""
            assert names_of("typed-literals").isdisjoint(names_of("typed-literals-round-tripped"))
            assert '"2.00"^^<http://www.w3.org/2001/XMLSchema#decimal>' in (
                VERSIONING / "typed-literals.nq"
            ).read_bytes().decode("utf-8")

        def test_names_two_versions_for_the_two_records_one_source_record_gives(self):
            """names two versions in `two-versions`, one for each record its one source record gives"""
            assert len(names_of("two-versions")) == 2


class TestChecksOfTheReferenceVersioning:
    """Checks of the reference versioning · tests/specification/versioning.py"""

    class TestVersions:
        """`versions()`"""

        def test_raises_for_a_version_that_holds_a_blank_node(self):
            """raises `ValueError` for a version that holds a blank node"""
            with pytest.raises(ValueError):
                versions(
                    parsed_ntriples(
                        "<urn:example:version> <http://www.w3.org/ns/prov#specializationOf> <urn:example:record> .\n"
                        "<urn:example:version> <http://example.org/p> _:b .\n"
                    )
                )
