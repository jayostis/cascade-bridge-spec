import functools
import json
import xml.etree.ElementTree as ElementTree
from pathlib import Path
from urllib.parse import unquote

import pytest
from rdflib import RDF, RDFS, XSD, BNode, Graph, Literal, Namespace, URIRef
from rdflib.compare import isomorphic

from json_lift import Members, lifted, parsed
from versioning import PLACEHOLDER, XSD_STRING, canonical_nquads, ni_name

ROOT = Path(__file__).resolve().parents[2]

MF = Namespace("http://www.w3.org/2001/sw/DataAccess/tests/test-manifest#")
BRIDGE = Namespace("https://ns.cascadeprotocol.org/bridge/v1-draft#")
CASCADE = Namespace("https://ns.cascadeprotocol.org/cascade#")
OA = Namespace("http://www.w3.org/ns/oa#")
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


@functools.cache
def manifest_of(adapter):
    manifest = adapter.directory / "fixtures" / "manifest.ttl"
    return Graph().parse(manifest, format="turtle", publicID=manifest.as_uri())


@functools.cache
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


@functools.cache
def facts_of(adapter, test):
    return Graph().parse(path_of(adapter, action_value(adapter, test, BRIDGE.facts)), format="turtle")


def expected_file_of(adapter, test):
    manifest = manifest_of(adapter)
    return path_of(adapter, manifest.value(manifest.value(test, MF.result), BRIDGE.expectedGraph))


@functools.cache
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
    return str(graph.value(graph.value(arrival_of(graph, record), OA.hasSelector), RDF.value))


def holder_of(adapter, selector):
    return selector.rpartition(adapter.HELD)[0] if adapter is JsonAdapter and adapter.HELD in selector else None


NAMING_VECTORS = ROOT.parent / "cascade-vocabulary" / "tests" / "vectors" / "naming"


def named_by_the_vocabulary(rule, *inputs):
    query = (NAMING_VECTORS / f"{rule}.rq").read_text(encoding="utf-8")
    rows = list(Graph().query(query, initBindings={f"input{n}": Literal(text) for n, text in enumerate(inputs, 1)}))
    assert len(rows) == 1
    return str(rows[0]["name"])


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


def mapped_by_the_synthetic_json_adapter(record):
    graph = lifted(json.dumps(record).encode("utf-8"))
    graph += graph.query((JsonAdapter.directory / "in" / "example-table.rq").read_text(encoding="utf-8")).graph
    graph.add((BRIDGE.thisDocument, BRIDGE.sha256, Literal(ni_name(json.dumps(record).encode("utf-8")))))
    graph.add((BRIDGE.thisRecord, BRIDGE.selector, Literal("")))
    return graph.query((JsonAdapter.directory / "in" / "example-record.rq").read_text(encoding="utf-8")).graph


class TestTheGraphABridgeWritesForADocument:
    """The graph a Bridge writes for a document · engine/stages.md, fixtures/synthetic-adapter/, fixtures/synthetic-json-adapter/

    Beside the records a mapping writes, a Bridge's graph for a document holds the document, the import that read it,
    and an arrival for each version: where in the document its record was read, and what the source said of it. Each
    conversion of the two synthetic adapters carries the graph an engine must write for it, and these hold each of
    those expected graphs to the rules of `engine/stages.md`.
    """

    class TestGivenASyntheticAdapter:
        @pytest.mark.parametrize("adapter", ADAPTERS.values(), ids=ADAPTERS.keys())
        def test_supplies_facts_with_every_conversion(self, adapter):
            tests = list(manifest_of(adapter).subjects(RDF.type, BRIDGE.IsomorphicConversionTest))
            assert tests
            assert all(action_value(adapter, test, BRIDGE.facts) is not None for test in tests)

    class TestGivenAConversionsExpectedGraph:
        """given a conversion's expected graph"""

        @pytest.mark.parametrize(("adapter", "test"), CONVERSIONS)
        def test_names_the_document_by_the_digest_of_its_bytes(self, adapter, test):
            """names the document `ni:///sha-256;` and the digest of its bytes"""
            document = the_one(expected_of(adapter, test), PROV.Entity)
            assert str(document) == ni_name(input_of(adapter, test).read_bytes())

        @pytest.mark.parametrize(("adapter", "test"), CONVERSIONS)
        def test_states_on_the_document_exactly_the_facts_supplied_about_it_a_base_url_apart(self, adapter, test):
            """states on the document exactly the facts supplied about it, a server's base URL apart

            A base URL is written normalised, as the Cascade vocabulary's naming vectors give it, so it is not
            compared.
            """
            expected = expected_of(adapter, test)
            document = the_one(expected, PROV.Entity)
            supplied = Graph()
            for subject, predicate, value in facts_of(adapter, test):
                if predicate == CASCADE.serverBaseUrl:
                    value = expected.value(document, CASCADE.serverBaseUrl)
                supplied.add((document if subject == BRIDGE.thisDocument else subject, predicate, value))
            written = described(expected, document)
            written.remove((document, RDF.type, PROV.Entity))
            assert isomorphic(written, described(supplied, document))

        @pytest.mark.parametrize(("adapter", "test"), CONVERSIONS)
        def test_links_the_import_to_the_document_it_used_and_to_the_adapters_identifier_and_version(
            self, adapter, test
        ):
            """links the import to the document it used and to the adapter's identifier and version"""
            expected = expected_of(adapter, test)
            crate = crate_of(adapter)
            run = the_one(expected, PROV.Activity)
            assert expected.value(run, PROV.used) == the_one(expected, PROV.Entity)
            plan = expected.value(expected.value(run, PROV.qualifiedAssociation), PROV.hadPlan)
            assert (plan, RDF.type, PROV.Plan) in expected
            assert expected.value(plan, RDFS.label) == Literal(crate["identifier"])
            assert expected.value(plan, PAV.version) == Literal(crate["version"])

        @pytest.mark.parametrize(("adapter", "test"), CONVERSIONS)
        def test_leaves_the_name_and_version_of_the_bridge_that_ran_unstated(self, adapter, test):
            """leaves the name and version of the Bridge that ran unstated

            An engine writes its own name and version there, and a conversion's comparison leaves them out.
            """
            expected = expected_of(adapter, test)
            association = expected.value(the_one(expected, PROV.Activity), PROV.qualifiedAssociation)
            assert not list(expected.predicate_objects(expected.value(association, PROV.agent)))

        @pytest.mark.parametrize(("adapter", "test"), CONVERSIONS)
        def test_states_on_the_import_exactly_the_facts_supplied_about_it(self, adapter, test):
            expected = expected_of(adapter, test)
            run = the_one(expected, PROV.Activity)
            supplied = Graph()
            for predicate, value in facts_of(adapter, test).predicate_objects(BRIDGE.thisImport):
                supplied.add((run, predicate, value))
            written = Graph()
            for predicate, value in expected.predicate_objects(run):
                if predicate not in (RDF.type, PROV.used, PROV.qualifiedAssociation):
                    written.add((run, predicate, value))
            assert isomorphic(written, supplied)

        @pytest.mark.skipif(
            not NAMING_VECTORS.is_dir(),
            reason=f"no cascade-vocabulary checkout beside this repository (looked for {NAMING_VECTORS})",
        )
        @pytest.mark.parametrize(("adapter", "test"), CONVERSIONS)
        def test_names_each_record_by_the_naming_rule_of_the_cascade_vocabulary_its_mapping_chooses(
            self, adapter, test
        ):
            """names each record by the naming rule of the Cascade vocabulary its mapping chooses

            A record held inside another is named by `ContainedRecordNamingRule`; one whose accession its document
            holds once, by `RecordFromServerNamingRule`; any other, by `RecordFromDocumentNamingRule`. Run with the vocabulary's own
            query text, from the cascade-vocabulary checkout beside this repository.
            """
            expected = expected_of(adapter, test)
            document = the_one(expected, PROV.Entity)
            held = adapter.accessions(input_of(adapter, test))
            by_selector = {selector_of(expected, record): record for record in expected.subjects(RDF.type, EX.Record)}
            for selector, record in by_selector.items():
                accession = str(expected.value(record, EX.accession))
                holder = holder_of(adapter, selector)
                if holder is not None:
                    container = adapter.selected(input_of(adapter, test), holder)
                    scope = container.get("version") or container.get("lastUpdated") or ""
                    name = named_by_the_vocabulary(
                        "ContainedRecordNamingRule", str(by_selector[holder]), scope, accession
                    )
                elif held.count(accession) == 1:
                    server = str(expected.value(document, CASCADE.serverBaseUrl))
                    name = named_by_the_vocabulary("RecordFromServerNamingRule", server, "ExampleRecord", accession)
                else:
                    name = named_by_the_vocabulary("RecordFromDocumentNamingRule", str(document), selector)
                assert str(record) == name

        @pytest.mark.parametrize(("adapter", "test"), CONVERSIONS)
        def test_names_each_version_by_the_digest_of_its_content_nested_nodes_included(self, adapter, test):
            """names each version by the digest of its content, nested nodes included"""
            assert not misnamed_versions(expected_of(adapter, test))

        @pytest.mark.parametrize(("adapter", "test"), CONVERSIONS)
        def test_points_each_arrival_at_its_record_in_the_document_at_the_document_and_at_the_import(
            self, adapter, test
        ):
            """points each arrival at its record in the document, at the document and at the import"""
            expected = expected_of(adapter, test)
            document = the_one(expected, PROV.Entity)
            run = the_one(expected, PROV.Activity)
            for record in expected.subjects(RDF.type, EX.Record):
                selector = selector_of(expected, record)
                node = adapter.selected(input_of(adapter, test), selector)
                if holder_of(adapter, selector) is None:
                    assert node["accession"] == str(expected.value(record, EX.accession))
                arrival = arrival_of(expected, record)
                assert expected.value(arrival, PROV.wasDerivedFrom) == document
                assert expected.value(arrival, PROV.wasGeneratedBy) == run

        @pytest.mark.parametrize(("adapter", "test"), CONVERSIONS)
        def test_carries_on_each_arrival_the_version_the_source_gave_its_record_and_none_for_a_held_record(
            self, adapter, test
        ):
            """carries on each arrival the version the source gave its record, and none for a record held inside another"""
            expected = expected_of(adapter, test)
            for record in expected.subjects(RDF.type, EX.Record):
                selector = selector_of(expected, record)
                arrival = arrival_of(expected, record)
                if holder_of(adapter, selector) is None:
                    node = adapter.selected(input_of(adapter, test), selector)
                    assert expected.value(arrival, PAV.version) == Literal(node["version"])
                else:
                    assert expected.value(arrival, PAV.version) is None

        @pytest.mark.parametrize(("adapter", "test"), CONVERSIONS)
        def test_states_when_the_source_last_updated_a_record_in_the_sources_own_characters(self, adapter, test):
            """states when the source last updated a record in the source's own characters, as a date or a date-time"""
            expected = expected_of(adapter, test)
            written = expected_file_of(adapter, test).read_text(encoding="utf-8")
            for record in expected.subjects(RDF.type, EX.Record):
                updated = adapter.selected(input_of(adapter, test), selector_of(expected, record)).get("lastUpdated")
                if updated is not None:
                    stated = "dateTime" if "T" in updated else "date"
                    assert expected.value(arrival_of(expected, record), PAV.lastUpdateOn).datatype == XSD[stated]
                    assert f'pav:lastUpdateOn "{updated}"^^xsd:{stated}' in written

    class TestWhenTheSyntheticJsonAdaptersMappingRunsOnARecord:
        """when the synthetic JSON adapter's mapping runs on a record"""

        @pytest.mark.parametrize(
            ("updated", "datatype"),
            [
                pytest.param("2026-08-01", XSD.date, id="a date"),
                pytest.param("2026-08-01T09:30:00.000+01:00", XSD.dateTime, id="a date-time"),
            ],
        )
        def test_types_a_last_update_as_the_date_or_the_date_time_the_record_states(self, updated, datatype):
            """types a last update as the date or the date-time the record states

            The adapter's `example-table.rq` and `example-record.rq`, run by rdflib over the reference lift of one
            record.
            """
            record = {"accession": "EX000199", "version": 1, "lastUpdated": updated}
            mapped = mapped_by_the_synthetic_json_adapter(record)
            assert set(mapped.objects(None, PAV.lastUpdateOn)) == {Literal(updated, datatype=datatype)}

    class TestGivenTheSyntheticJsonAdaptersExpectedGraphs:
        """given the synthetic JSON adapter's expected graphs"""

        def test_states_a_last_update_as_a_date_in_one_arrival_and_as_a_date_time_in_another(self):
            stated = {
                value.datatype
                for adapter, test in (param.values for param in CONVERSIONS)
                if adapter is JsonAdapter
                for value in expected_of(JsonAdapter, test).objects(None, PAV.lastUpdateOn)
            }
            assert stated == {XSD.date, XSD.dateTime}

        def test_holds_a_record_inside_another_and_a_record_that_is_its_documents_value(self):
            """holds a record inside another and a record that is its document's value"""
            selectors = {
                selector_of(expected_of(JsonAdapter, test), record)
                for adapter, test in (param.values for param in CONVERSIONS)
                if adapter is JsonAdapter
                for record in expected_of(JsonAdapter, test).subjects(RDF.type, EX.Record)
            }
            assert "/records/0/contained/0" in selectors
            assert "" in selectors


class TestChecksOfTheCheckOnAVersionsName:
    """Checks of the check on a version's name · tests/specification/test_the_synthetic_adapters_graphs_are_the_records_layer.py"""

    class TestMisnamedVersions:
        """`misnamed_versions()`"""

        def test_finds_no_misnamed_version_in_a_graph_whose_versions_hold_nested_nodes(self):
            """finds no misnamed version in `nested-nodes.versioned.nt`, whose versions hold nested nodes"""
            versioned = ROOT / "fixtures" / "versioning" / "nested-nodes.versioned.nt"
            assert not misnamed_versions(Graph().parse(versioned, format="nt"))
