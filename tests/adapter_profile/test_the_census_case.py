import re

from rdflib import Graph
from rdflib.namespace import RDF, SH

from _terms import BRIDGE, MF, OA


def census_findings(crate):
    for test in crate.entries:
        result = crate.graph.value(test, MF.result)
        expected = None if result is None else crate.graph.value(result, BRIDGE.expectedFindings)
        beside = None if expected is None else crate.file_at(expected)
        if beside is None:
            continue
        graph = Graph().parse(beside, format="turtle")
        for finding in graph.subjects(RDF.type, OA.Annotation):
            if graph.value(finding, OA.hasBody) == BRIDGE.pathNotAccounted:
                yield test, graph, finding


def the_one(crate):
    found = list(census_findings(crate))
    assert len(found) == 1
    return found[0]


def selected_by(graph, finding):
    selector = graph.value(graph.value(finding, OA.hasTarget), OA.hasSelector)
    refinement = graph.value(selector, OA.refinedBy)
    return str(graph.value(selector, RDF.value)), str(graph.value(refinement, RDF.value))


def test_the_synthetic_adapter_expects_one_census_finding_for_the_input_its_manifest_names(crate):
    test, _, _ = the_one(crate)
    named = crate.graph.value(crate.graph.value(test, MF.action), BRIDGE.input)
    assert crate.file_at(named) is not None


def test_the_census_finding_is_addressed_at_the_first_occurrence_of_the_path_it_names(crate):
    _, graph, finding = the_one(crate)
    record, refinement = selected_by(graph, finding)
    assert re.search(r"\[\d+\]$", refinement)
    record_element = record.rsplit("/", 1)[-1]
    assert str(graph.value(finding, SH.value)) == re.sub(r"\[\d+\]", "", f"/{record_element}/{refinement}")


def test_the_census_finding_is_a_backlog_item_rather_than_a_defect_in_the_document(crate):
    _, graph, finding = the_one(crate)
    assert graph.value(finding, SH.resultSeverity) == SH.Info


def test_the_synthetic_adapters_accounting_carries_no_entry_for_the_path_its_census_finding_names(crate):
    _, graph, finding = the_one(crate)
    named = crate.graph.value(crate.root, BRIDGE.sourceAccounting)
    assert named is not None
    accounting = Graph().parse(crate.file_at(named), format="turtle")
    accounted = {str(path) for path in accounting.objects(None, BRIDGE.sourcePath)}
    assert accounted
    assert str(graph.value(finding, SH.value)) not in accounted
