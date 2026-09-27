import json
import xml.etree.ElementTree as ElementTree
from pathlib import Path

import pytest
from rdflib import RDF, RDFS, BNode, Graph, Literal, Namespace, URIRef
from rdflib.compare import isomorphic
from recomputed import PLACEHOLDER, XSD_STRING, canonical_nquads, ni_name, normalised_base_url, record_name

ROOT = Path(__file__).resolve().parents[2]
ADAPTER = ROOT / "fixtures" / "synthetic-adapter"
MANIFEST_FILE = ADAPTER / "fixtures" / "manifest.ttl"
MANIFEST = Graph().parse(MANIFEST_FILE, format="turtle", publicID=MANIFEST_FILE.as_uri())
CRATE = next(
    entity for entity in json.loads((ADAPTER / "ro-crate-metadata.json").read_text())["@graph"] if entity["@id"] == "./"
)

MF = Namespace("http://www.w3.org/2001/sw/DataAccess/tests/test-manifest#")
BRIDGE = Namespace("https://ns.cascadeprotocol.org/bridge/v1-draft#")
PROV = Namespace("http://www.w3.org/ns/prov#")
PAV = Namespace("http://purl.org/pav/")
EX = Namespace("https://example.org/synthetic-adapter/v1#")

CONVERSIONS = sorted(MANIFEST.subjects(RDF.type, BRIDGE.IsomorphicConversionTest), key=str)


def path_of(iri):
    return ADAPTER / str(iri).removeprefix(ADAPTER.as_uri() + "/")


def action_of(test):
    return MANIFEST.value(test, MF.action)


def input_of(test):
    return path_of(MANIFEST.value(action_of(test), BRIDGE.input))


def facts_of(test):
    return Graph().parse(path_of(MANIFEST.value(action_of(test), BRIDGE.facts)), format="turtle")


def expected_of(test):
    return Graph().parse(
        path_of(MANIFEST.value(MANIFEST.value(test, MF.result), BRIDGE.expectedGraph)), format="turtle"
    )


def described(graph, node, into=None):
    """Every triple whose subject is the node, and the description of each blank node it names."""
    into = Graph() if into is None else into
    for predicate, value in graph.predicate_objects(node):
        into.add((node, predicate, value))
        if isinstance(value, BNode):
            described(graph, value, into)
    return into


def the_one(graph, rdf_type):
    found = list(graph.subjects(RDF.type, rdf_type))
    assert len(found) == 1, f"{len(found)} of {rdf_type}"
    return found[0]


def records_of(document):
    root = ElementTree.parse(document).getroot()
    return [root] if root.tag == "ExampleRecord" else root.findall("ExampleRecord")


def selected(document, selector):
    root = ElementTree.parse(document).getroot()
    steps = selector.split("/")[1:]
    assert steps[0] == root.tag, selector
    return root if len(steps) == 1 else root.find("/".join(steps[1:]))


def arrival_of(graph, record):
    version = graph.value(None, PROV.specializationOf, record)
    return graph.value(None, BRIDGE.arrivedAs, version)


def test_every_conversion_of_the_synthetic_adapter_is_supplied_facts():
    assert CONVERSIONS
    assert all(MANIFEST.value(action_of(test), BRIDGE.facts) is not None for test in CONVERSIONS)


@pytest.mark.parametrize("test", CONVERSIONS, ids=lambda test: str(test).rpartition("#")[2])
def test_the_document_is_named_by_the_sha256_of_its_bytes_and_carries_the_facts_supplied_with_it(test):
    expected = expected_of(test)
    document = the_one(expected, PROV.Entity)
    assert str(document) == ni_name(input_of(test).read_bytes())
    supplied = Graph()
    for subject, predicate, value in facts_of(test):
        if predicate == BRIDGE.serverBaseUrl:
            value = Literal(normalised_base_url(str(value)))
        supplied.add((document if subject == BRIDGE.thisDocument else subject, predicate, value))
    written = described(expected, document)
    written.remove((document, RDF.type, PROV.Entity))
    assert isomorphic(written, described(supplied, document))


@pytest.mark.parametrize("test", CONVERSIONS, ids=lambda test: str(test).rpartition("#")[2])
def test_the_import_carries_the_facts_supplied_with_it_and_applied_the_adapters_release(test):
    expected = expected_of(test)
    run = the_one(expected, PROV.Activity)
    assert expected.value(run, PROV.used) == the_one(expected, PROV.Entity)
    association = expected.value(run, PROV.qualifiedAssociation)
    plan = expected.value(association, PROV.hadPlan)
    assert (plan, RDF.type, PROV.Plan) in expected
    assert expected.value(plan, RDFS.label) == Literal(CRATE["identifier"])
    assert expected.value(plan, PAV.version) == Literal(CRATE["version"])
    assert not list(expected.predicate_objects(expected.value(association, PROV.agent)))
    supplied = Graph()
    for predicate, value in facts_of(test).predicate_objects(BRIDGE.thisImport):
        supplied.add((run, predicate, value))
    written = Graph()
    for predicate, value in expected.predicate_objects(run):
        if predicate not in (RDF.type, PROV.used, PROV.qualifiedAssociation):
            written.add((run, predicate, value))
    assert isomorphic(written, supplied)


@pytest.mark.parametrize("test", CONVERSIONS, ids=lambda test: str(test).rpartition("#")[2])
def test_each_record_is_named_by_its_server_type_and_accession_unless_its_document_repeats_the_accession(test):
    expected = expected_of(test)
    held = [record.get("Accession") for record in records_of(input_of(test))]
    server = normalised_base_url(str(facts_of(test).value(BRIDGE.thisDocument, BRIDGE.serverBaseUrl)))
    document = ni_name(input_of(test).read_bytes())
    records = list(expected.subjects(RDF.type, EX.Record))
    assert records
    for record in records:
        accession = str(expected.value(record, EX.accession))
        selector = str(expected.value(arrival_of(expected, record), BRIDGE.selector))
        inputs = [server, "ExampleRecord", accession] if held.count(accession) == 1 else [document, selector]
        assert str(record) == record_name(inputs)


@pytest.mark.parametrize("test", CONVERSIONS, ids=lambda test: str(test).rpartition("#")[2])
def test_each_version_is_named_by_the_sha256_of_its_content(test):
    expected = expected_of(test)

    def term(node):
        if node == version:
            return ("iri", PLACEHOLDER)
        if isinstance(node, URIRef):
            return ("iri", str(node))
        return ("literal", str(node), str(node.datatype or XSD_STRING))

    versions = set(expected.subjects(PROV.specializationOf, None))
    assert versions
    for version in versions:
        content = {tuple(term(node) for node in triple) for triple in expected.triples((version, None, None))}
        assert str(version) == ni_name(canonical_nquads(content).encode("utf-8"))


@pytest.mark.parametrize("test", CONVERSIONS, ids=lambda test: str(test).rpartition("#")[2])
def test_each_arrival_selects_its_record_in_the_document_and_carries_the_version_the_source_gave_it(test):
    expected = expected_of(test)
    document = the_one(expected, PROV.Entity)
    run = the_one(expected, PROV.Activity)
    for record in expected.subjects(RDF.type, EX.Record):
        arrival = arrival_of(expected, record)
        element = selected(input_of(test), str(expected.value(arrival, BRIDGE.selector)))
        assert element.get("Accession") == str(expected.value(record, EX.accession))
        assert expected.value(arrival, PAV.version) == Literal(element.get("Version"))
        assert expected.value(arrival, PROV.wasDerivedFrom) == document
        assert expected.value(arrival, PROV.wasGeneratedBy) == run
