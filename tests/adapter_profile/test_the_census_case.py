import re

from rdflib import Graph
from rdflib.namespace import RDF, SH

from _terms import BRIDGE, MF, OA

THE_NAMESPACE = "https://example.org/synthetic-adapter/ext/v1"

AN_ELEMENT = "/ExampleRecord/Novelty"
AN_ATTRIBUTE_OF_A_CHILD_ELEMENT = "/ExampleRecord/Label/@lang"
AN_ATTRIBUTE_OF_THE_RECORD_ELEMENT = "/ExampleRecord/@Curated"
AN_ELEMENT_IN_A_NAMESPACE = f"/ExampleRecord/*[local-name()='Extension' and namespace-uri()='{THE_NAMESPACE}']"
AN_ATTRIBUTE_IN_A_NAMESPACE = f"/ExampleRecord/@*[local-name()='origin' and namespace-uri()='{THE_NAMESPACE}']"


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


def every(crate):
    found = list(census_findings(crate))
    assert found
    return found


def selected_by(graph, finding):
    selector = graph.value(graph.value(finding, OA.hasTarget), OA.hasSelector)
    refined = graph.value(selector, OA.refinedBy)
    record = str(graph.value(selector, RDF.value))
    return record, None if refined is None else str(graph.value(refined, RDF.value))


def the_one_naming(crate, path):
    naming = [(graph, finding) for _, graph, finding in every(crate) if str(graph.value(finding, SH.value)) == path]
    assert len(naming) == 1, path
    return naming[0]


def test_every_census_finding_the_synthetic_adapter_expects_is_for_an_input_its_manifest_names(crate):
    for test, _, _ in every(crate):
        named = crate.graph.value(crate.graph.value(test, MF.action), BRIDGE.input)
        assert crate.file_at(named) is not None


def test_a_census_finding_about_an_element_is_addressed_at_the_first_occurrence_of_that_element(crate):
    graph, finding = the_one_naming(crate, AN_ELEMENT)
    record, refinement = selected_by(graph, finding)
    assert refinement == "Novelty[1]"
    record_element = re.sub(r"\[\d+\]$", "", record.rsplit("/", 1)[-1])
    assert AN_ELEMENT == re.sub(r"\[\d+\]$", "", f"/{record_element}/{refinement}")


def test_a_census_finding_about_an_element_in_a_namespace_names_it_as_a_selectors_step_does(crate):
    graph, finding = the_one_naming(crate, AN_ELEMENT_IN_A_NAMESPACE)
    _, refinement = selected_by(graph, finding)
    assert refinement == f"*[local-name()='Extension' and namespace-uri()='{THE_NAMESPACE}'][1]"


def test_a_census_finding_about_an_attribute_of_a_child_element_is_refined_onto_that_child(crate):
    graph, finding = the_one_naming(crate, AN_ATTRIBUTE_OF_A_CHILD_ELEMENT)
    _, refinement = selected_by(graph, finding)
    assert refinement == "Label[1]"


def test_a_census_finding_about_an_attribute_of_the_record_element_carries_no_refinement(crate):
    graph, finding = the_one_naming(crate, AN_ATTRIBUTE_OF_THE_RECORD_ELEMENT)
    _, refinement = selected_by(graph, finding)
    assert refinement is None


def test_a_census_finding_names_an_attribute_in_a_namespace_by_an_at_sign_before_a_selectors_step(crate):
    graph, finding = the_one_naming(crate, AN_ATTRIBUTE_IN_A_NAMESPACE)
    before, _, step = str(graph.value(finding, SH.value)).partition("/@")
    assert before == "/ExampleRecord"
    assert step == f"*[local-name()='origin' and namespace-uri()='{THE_NAMESPACE}']"


def test_every_census_finding_is_a_backlog_item_rather_than_a_defect_in_the_document(crate):
    for _, graph, finding in every(crate):
        assert graph.value(finding, SH.resultSeverity) == SH.Info


def test_the_synthetic_adapters_accounting_carries_no_entry_for_any_path_its_census_findings_name(crate):
    named = crate.graph.value(crate.root, BRIDGE.sourceAccounting)
    assert named is not None
    accounting = Graph().parse(crate.file_at(named), format="turtle")
    accounted = {str(path) for path in accounting.objects(None, BRIDGE.sourcePath)}
    assert accounted
    for _, graph, finding in every(crate):
        assert str(graph.value(finding, SH.value)) not in accounted
