import uuid
from pathlib import Path

import pytest
from pyshacl import validate
from rdflib import RDF, Graph, Literal, Namespace, URIRef
from rdflib.collection import Collection

from recomputed import NAMESPACE, normalised_base_url, record_name

ROOT = Path(__file__).resolve().parents[2]
NAMING = ROOT / "fixtures" / "naming"
SHAPES = Graph().parse(ROOT / "shapes" / "bridge.shapes.ttl", format="turtle")
MANIFEST = Graph().parse(NAMING / "manifest.ttl", format="turtle", publicID=(NAMING / "manifest.ttl").as_uri())
MF = Namespace("http://www.w3.org/2001/sw/DataAccess/tests/test-manifest#")
QT = Namespace("http://www.w3.org/2001/sw/DataAccess/tests/test-query#")
BRIDGE = Namespace("https://ns.cascadeprotocol.org/bridge/v1-draft#")


def vectors_of(kind):
    return sorted(MANIFEST.subjects(RDF.type, kind), key=str)


def inputs_of(test):
    return [
        str(member)
        for member in Collection(MANIFEST, MANIFEST.value(MANIFEST.value(test, MF.action), BRIDGE.nameInputs))
    ]


def expected_name_of(test):
    return str(MANIFEST.value(MANIFEST.value(test, MF.result), BRIDGE.expectedName))


def expected_by_name(name):
    return expected_name_of(URIRef(f"{(NAMING / 'manifest.ttl').as_uri()}#{name}"))


NAMING_VECTORS = vectors_of(BRIDGE.NamingTest)
BASE_URL_VECTORS = vectors_of(BRIDGE.BaseUrlNormalisationTest)


def vector_id(test):
    return str(test).rpartition("#")[2]


@pytest.mark.parametrize("test", NAMING_VECTORS, ids=vector_id)
def test_a_name_is_the_first_128_bits_of_sha256_over_the_namespace_and_the_inputs_with_version_8_set(test):
    assert record_name(inputs_of(test)) == expected_name_of(test)


@pytest.mark.parametrize("test", NAMING_VECTORS, ids=vector_id)
def test_a_name_is_a_version_8_uuid_of_the_rfc_9562_variant(test):
    name = uuid.UUID(expected_name_of(test).removeprefix("urn:uuid:"))
    assert (name.version, name.variant) == (8, uuid.RFC_4122)


@pytest.mark.parametrize("test", NAMING_VECTORS, ids=vector_id)
def test_the_naming_query_computes_the_name_in_a_sparql_engine_other_than_a_bridges(test):
    query_file = NAMING / str(MANIFEST.value(MANIFEST.value(test, MF.action), QT.query)).rpartition("/")[2]
    query = query_file.read_text(encoding="utf-8")
    solutions = list(Graph().query(query, initBindings={"input": Literal("|".join(inputs_of(test)))}))
    assert [str(solution.name) for solution in solutions] == [expected_name_of(test)]


@pytest.mark.parametrize("test", BASE_URL_VECTORS, ids=vector_id)
def test_a_base_url_has_its_scheme_and_host_lower_cased_and_no_trailing_slash(test):
    action, result = (
        MANIFEST.value(MANIFEST.value(test, step), BRIDGE.serverBaseUrl) for step in (MF.action, MF.result)
    )
    assert normalised_base_url(str(action)) == str(result)


def test_every_row_of_the_naming_table_has_a_vector():
    assert {vector_id(test) for test in NAMING_VECTORS} >= {
        "fhir-resource",
        "fhir-bundle-entry-urn",
        "fhir-contained",
        "ccda-root-and-extension",
        "ccda-root-only",
        "clinvar-variation-archive",
        "clinvar-clinical-assertion",
        "clinvar-interpretation-first",
        "repeated-id-first",
        "no-id",
        "no-server",
    }


def test_an_id_repeated_within_its_document_names_two_records():
    assert expected_by_name("repeated-id-first") != expected_by_name("repeated-id-second")


def test_the_same_id_on_two_servers_names_two_records():
    assert expected_by_name("fhir-resource") != expected_by_name("fhir-resource-on-another-server")


def test_a_contained_resource_is_named_from_its_containing_records_name():
    assert inputs_of(URIRef(f"{(NAMING / 'manifest.ttl').as_uri()}#fhir-contained"))[0] == expected_by_name(
        "fhir-resource"
    )


def test_the_contract_states_the_namespace_uuid(sparql_contract):
    assert NAMESPACE in sparql_contract


def test_the_naming_query_hashes_under_the_namespace_uuid():
    assert f'"{NAMESPACE}|"' in (NAMING / "name.rq").read_text(encoding="utf-8")


def test_a_naming_result_that_is_not_a_version_8_uuid_is_refused():
    manifest = Graph() + MANIFEST
    result = manifest.value(NAMING_VECTORS[0], MF.result)
    manifest.set((result, BRIDGE.expectedName, URIRef("urn:uuid:7435b3b8-2d93-5912-9d48-940c5870dc81")))
    conforms, _, text = validate(manifest, shacl_graph=SHAPES, advanced=True)
    assert not conforms and "version 8" in text
