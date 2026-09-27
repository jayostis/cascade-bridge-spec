import json
import xml.etree.ElementTree as ElementTree
from pathlib import Path
from urllib.parse import unquote

import pytest
from rdflib import RDF, RDFS, XSD, BNode, Graph, Literal, Namespace, URIRef
from rdflib.compare import isomorphic

from json_lift import Members, lifted, parsed
from recomputed import PLACEHOLDER, XSD_STRING, canonical_nquads, ni_name, normalised_base_url, record_name

ROOT = Path(__file__).resolve().parents[2]

MF = Namespace("http://www.w3.org/2001/sw/DataAccess/tests/test-manifest#")
BRIDGE = Namespace("https://ns.cascadeprotocol.org/bridge/v1-draft#")
PROV = Namespace("http://www.w3.org/ns/prov#")
PAV = Namespace("http://purl.org/pav/")
EX = Namespace("https://example.org/synthetic-adapter/v1#")


class XmlAdapter:
    directory = ROOT / "fixtures" / "synthetic-adapter"

    @staticmethod
    def accessions(document):
        root = ElementTree.parse(document).getroot()
        return [
            record.get("Accession")
            for record in ([root] if root.tag == "ExampleRecord" else root.findall("ExampleRecord"))
        ]

    @staticmethod
    def selected(document, selector):
        root = ElementTree.parse(document).getroot()
        steps = selector.split("/")[1:]
        assert steps[0] == root.tag, selector
        element = root if len(steps) == 1 else root.find("/".join(steps[1:]))
        return {"accession": element.get("Accession"), "version": element.get("Version")}


class JsonAdapter:
    directory = ROOT / "fixtures" / "synthetic-json-adapter"
    HELD = "/contained/"

    @staticmethod
    def accessions(document):
        value = parsed(document.read_bytes())
        records = dict(value).get("records")
        return [dict(record).get("accession") for record in ([value] if records is None else records)]

    @staticmethod
    def selected(document, selector):
        node = parsed(document.read_bytes())
        for token in selector.split("/")[1:]:
            token = unquote(token).replace("~1", "/").replace("~0", "~")
            node = node[int(token)] if not isinstance(node, Members) else dict(node)[token]
        return dict(node)


ADAPTERS = {"synthetic-adapter": XmlAdapter, "synthetic-json-adapter": JsonAdapter}


def manifest_of(adapter):
    manifest = adapter.directory / "fixtures" / "manifest.ttl"
    return Graph().parse(manifest, format="turtle", publicID=manifest.as_uri())


def crate_of(adapter):
    graph = json.loads((adapter.directory / "ro-crate-metadata.json").read_text(encoding="utf-8"))["@graph"]
    return next(entity for entity in graph if entity["@id"] == "./")


CONVERSIONS = [
    pytest.param(adapter, test, id=f"{name}:{str(test).rpartition('#')[2]}")
    for name, adapter in ADAPTERS.items()
    for test in sorted(manifest_of(adapter).subjects(RDF.type, BRIDGE.IsomorphicConversionTest), key=str)
]


def path_of(adapter, iri):
    return adapter.directory / str(iri).removeprefix(adapter.directory.as_uri() + "/")


def action_value(adapter, test, term):
    manifest = manifest_of(adapter)
    return manifest.value(manifest.value(test, MF.action), term)


def input_of(adapter, test):
    return path_of(adapter, action_value(adapter, test, BRIDGE.input))


def facts_of(adapter, test):
    return Graph().parse(path_of(adapter, action_value(adapter, test, BRIDGE.facts)), format="turtle")


def expected_file_of(adapter, test):
    manifest = manifest_of(adapter)
    return path_of(adapter, manifest.value(manifest.value(test, MF.result), BRIDGE.expectedGraph))


def expected_of(adapter, test):
    return Graph().parse(expected_file_of(adapter, test), format="turtle")


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


def arrival_of(graph, record):
    version = graph.value(None, PROV.specializationOf, record)
    return graph.value(None, BRIDGE.arrivedAs, version)


def selector_of(graph, record):
    return str(graph.value(arrival_of(graph, record), BRIDGE.selector))


def holder_of(adapter, selector):
    return selector.rpartition(adapter.HELD)[0] if adapter is JsonAdapter and adapter.HELD in selector else None


@pytest.mark.parametrize("adapter", ADAPTERS.values(), ids=ADAPTERS.keys())
def test_every_conversion_of_a_synthetic_adapter_is_supplied_facts(adapter):
    tests = list(manifest_of(adapter).subjects(RDF.type, BRIDGE.IsomorphicConversionTest))
    assert tests
    assert all(action_value(adapter, test, BRIDGE.facts) is not None for test in tests)


@pytest.mark.parametrize(("adapter", "test"), CONVERSIONS)
def test_the_document_is_named_by_the_sha256_of_its_bytes_and_carries_the_facts_supplied_with_it(adapter, test):
    expected = expected_of(adapter, test)
    document = the_one(expected, PROV.Entity)
    assert str(document) == ni_name(input_of(adapter, test).read_bytes())
    supplied = Graph()
    for subject, predicate, value in facts_of(adapter, test):
        if predicate == BRIDGE.serverBaseUrl:
            value = Literal(normalised_base_url(str(value)))
        supplied.add((document if subject == BRIDGE.thisDocument else subject, predicate, value))
    written = described(expected, document)
    written.remove((document, RDF.type, PROV.Entity))
    assert isomorphic(written, described(supplied, document))


@pytest.mark.parametrize(("adapter", "test"), CONVERSIONS)
def test_the_import_carries_the_facts_supplied_with_it_and_applied_the_adapters_release(adapter, test):
    expected = expected_of(adapter, test)
    crate = crate_of(adapter)
    run = the_one(expected, PROV.Activity)
    assert expected.value(run, PROV.used) == the_one(expected, PROV.Entity)
    association = expected.value(run, PROV.qualifiedAssociation)
    plan = expected.value(association, PROV.hadPlan)
    assert (plan, RDF.type, PROV.Plan) in expected
    assert expected.value(plan, RDFS.label) == Literal(crate["identifier"])
    assert expected.value(plan, PAV.version) == Literal(crate["version"])
    assert not list(expected.predicate_objects(expected.value(association, PROV.agent)))
    supplied = Graph()
    for predicate, value in facts_of(adapter, test).predicate_objects(BRIDGE.thisImport):
        supplied.add((run, predicate, value))
    written = Graph()
    for predicate, value in expected.predicate_objects(run):
        if predicate not in (RDF.type, PROV.used, PROV.qualifiedAssociation):
            written.add((run, predicate, value))
    assert isomorphic(written, supplied)


@pytest.mark.parametrize(("adapter", "test"), CONVERSIONS)
def test_each_record_is_named_by_its_server_type_and_accession_unless_its_document_repeats_the_accession(adapter, test):
    expected = expected_of(adapter, test)
    held = adapter.accessions(input_of(adapter, test))
    server = normalised_base_url(str(facts_of(adapter, test).value(BRIDGE.thisDocument, BRIDGE.serverBaseUrl)))
    document = ni_name(input_of(adapter, test).read_bytes())
    for record in expected.subjects(RDF.type, EX.Record):
        if holder_of(adapter, selector_of(expected, record)) is not None:
            continue
        accession = str(expected.value(record, EX.accession))
        inputs = (
            [server, "ExampleRecord", accession]
            if held.count(accession) == 1
            else [document, selector_of(expected, record)]
        )
        assert str(record) == record_name(inputs)


@pytest.mark.parametrize(("adapter", "test"), CONVERSIONS)
def test_a_record_held_inside_another_is_named_by_its_holders_name_and_its_own_id(adapter, test):
    expected = expected_of(adapter, test)
    by_selector = {selector_of(expected, record): record for record in expected.subjects(RDF.type, EX.Record)}
    for selector, record in by_selector.items():
        holder = holder_of(adapter, selector)
        if holder is not None:
            own_id = adapter.selected(input_of(adapter, test), selector)["id"]
            assert str(expected.value(record, EX.accession)) == own_id
            assert str(record) == record_name([str(by_selector[holder]), own_id])


def content_of(graph, version):
    def in_version(node):
        return isinstance(node, URIRef) and (node == version or str(node).startswith(f"{version}#"))

    def term(node):
        if in_version(node):
            return ("iri", PLACEHOLDER + str(node)[len(version) :])
        if isinstance(node, URIRef):
            return ("iri", str(node))
        return ("literal", str(node), str(node.datatype or XSD_STRING))

    return {tuple(term(node) for node in triple) for triple in graph if in_version(triple[0])}


def misnamed_versions(graph):
    return {
        str(version)
        for version in set(graph.subjects(PROV.specializationOf, None))
        if str(version) != ni_name(canonical_nquads(content_of(graph, version)).encode("utf-8"))
    }


def test_a_version_holding_nested_nodes_is_named_by_its_content_theirs_included():
    versioned = ROOT / "fixtures" / "versioning" / "nested-nodes.versioned.nt"
    assert not misnamed_versions(Graph().parse(versioned, format="nt"))


@pytest.mark.parametrize(("adapter", "test"), CONVERSIONS)
def test_each_version_is_named_by_the_sha256_of_its_content(adapter, test):
    assert not misnamed_versions(expected_of(adapter, test))


@pytest.mark.parametrize(("adapter", "test"), CONVERSIONS)
def test_each_arrival_selects_its_record_in_the_document_and_carries_the_version_the_source_gave_it(adapter, test):
    expected = expected_of(adapter, test)
    document = the_one(expected, PROV.Entity)
    run = the_one(expected, PROV.Activity)
    for record in expected.subjects(RDF.type, EX.Record):
        arrival = arrival_of(expected, record)
        selector = selector_of(expected, record)
        node = adapter.selected(input_of(adapter, test), selector)
        if holder_of(adapter, selector) is None:
            assert node["accession"] == str(expected.value(record, EX.accession))
            assert expected.value(arrival, PAV.version) == Literal(node["version"])
        else:
            assert expected.value(arrival, PAV.version) is None
        assert expected.value(arrival, PROV.wasDerivedFrom) == document
        assert expected.value(arrival, PROV.wasGeneratedBy) == run


@pytest.mark.parametrize(("adapter", "test"), CONVERSIONS)
def test_an_arrival_says_when_the_source_last_updated_its_record_in_the_sources_own_text(adapter, test):
    expected = expected_of(adapter, test)
    written = expected_file_of(adapter, test).read_text(encoding="utf-8")
    for record in expected.subjects(RDF.type, EX.Record):
        updated = adapter.selected(input_of(adapter, test), selector_of(expected, record)).get("lastUpdated")
        if updated is not None:
            stated = "dateTime" if "T" in updated else "date"
            assert expected.value(arrival_of(expected, record), PAV.lastUpdateOn).datatype == XSD[stated]
            assert f'pav:lastUpdateOn "{updated}"^^xsd:{stated}' in written


def mapped_by_the_synthetic_json_adapter(record):
    graph = lifted(json.dumps(record).encode("utf-8"))
    graph += graph.query((JsonAdapter.directory / "in" / "example-table.rq").read_text(encoding="utf-8")).graph
    graph.add((BRIDGE.thisDocument, BRIDGE.sha256, Literal(ni_name(json.dumps(record).encode("utf-8")))))
    graph.add((BRIDGE.thisRecord, BRIDGE.selector, Literal("")))
    return graph.query((JsonAdapter.directory / "in" / "example-record.rq").read_text(encoding="utf-8")).graph


@pytest.mark.parametrize(
    ("updated", "datatype"), [("2026-08-01", XSD.date), ("2026-08-01T09:30:00.000+01:00", XSD.dateTime)]
)
def test_the_synthetic_json_mapping_types_a_last_update_as_the_date_or_date_time_its_source_states(updated, datatype):
    mapped = mapped_by_the_synthetic_json_adapter({"accession": "EX000199", "version": 1, "lastUpdated": updated})
    assert set(mapped.objects(None, PAV.lastUpdateOn)) == {Literal(updated, datatype=datatype)}


def test_a_synthetic_json_arrival_states_a_last_update_as_a_date_and_another_as_a_date_time():
    stated = {
        value.datatype
        for adapter, test in (param.values for param in CONVERSIONS)
        if adapter is JsonAdapter
        for value in expected_of(JsonAdapter, test).objects(None, PAV.lastUpdateOn)
    }
    assert stated == {XSD.date, XSD.dateTime}


def test_the_synthetic_json_adapter_holds_a_record_inside_another_and_a_record_that_is_its_documents_value():
    selectors = {
        selector_of(expected_of(JsonAdapter, test), record)
        for adapter, test in (param.values for param in CONVERSIONS)
        if adapter is JsonAdapter
        for record in expected_of(JsonAdapter, test).subjects(RDF.type, EX.Record)
    }
    assert "/records/0/contained/0" in selectors
    assert "" in selectors
