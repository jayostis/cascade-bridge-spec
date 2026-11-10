import re

from rdflib import Graph
from rdflib.namespace import RDF, SH

from _terms import BRIDGE, CASCADE, MF, OA
from adapter_profile_world import accounting_of, selected_by

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
            if graph.value(finding, OA.hasBody) == CASCADE.SourcePathNotAccounted:
                yield test, graph, finding


def every(crate):
    found = list(census_findings(crate))
    assert found
    return found


def the_one_naming(crate, path):
    naming = [(graph, finding) for _, graph, finding in every(crate) if str(graph.value(finding, SH.value)) == path]
    assert len(naming) == 1, path
    return naming[0]


class TestFindingsABridgeReportsForAPathNoEntryAccountsFor:
    """Findings a Bridge reports for a path no entry accounts for · fixtures/synthetic-adapter/fixtures/findings/example-0004.ttl

    The census is what a Bridge reports of a path the accounting carries no entry for: one finding per path per record,
    for the adapter's author to act on.
    """

    class TestGivenEveryCensusFindingTheSyntheticAdapterExpects:
        def test_is_for_an_input_its_manifest_names(self, crate):
            for test, _, _ in every(crate):
                named = crate.graph.value(crate.graph.value(test, MF.action), BRIDGE.input)
                assert crate.file_at(named) is not None

    class TestGivenACensusFindingAboutAnElement:
        def test_is_addressed_at_the_first_occurrence_of_that_element(self, crate):
            graph, finding = the_one_naming(crate, AN_ELEMENT)
            record, refinement = selected_by(graph, finding)
            assert refinement == "Novelty[1]"
            record_element = re.sub(r"\[\d+\]$", "", record.rsplit("/", 1)[-1])
            assert AN_ELEMENT == re.sub(r"\[\d+\]$", "", f"/{record_element}/{refinement}")

    class TestGivenACensusFindingAboutAnElementInANamespace:
        def test_names_it_as_a_selectors_step_does(self, crate):
            """names it as a selector's step does"""
            graph, finding = the_one_naming(crate, AN_ELEMENT_IN_A_NAMESPACE)
            _, refinement = selected_by(graph, finding)
            assert refinement == f"*[local-name()='Extension' and namespace-uri()='{THE_NAMESPACE}'][1]"

    class TestGivenACensusFindingAboutAnAttributeOfAChildElement:
        def test_is_refined_onto_that_child(self, crate):
            graph, finding = the_one_naming(crate, AN_ATTRIBUTE_OF_A_CHILD_ELEMENT)
            _, refinement = selected_by(graph, finding)
            assert refinement == "Label[1]"

    class TestGivenACensusFindingAboutAnAttributeOfTheRecordElement:
        def test_carries_no_refinement(self, crate):
            graph, finding = the_one_naming(crate, AN_ATTRIBUTE_OF_THE_RECORD_ELEMENT)
            _, refinement = selected_by(graph, finding)
            assert refinement is None

    class TestGivenACensusFindingAboutAnAttributeInANamespace:
        def test_names_it_by_an_at_sign_before_a_selectors_step(self, crate):
            """names it by an at sign before a selector's step"""
            graph, finding = the_one_naming(crate, AN_ATTRIBUTE_IN_A_NAMESPACE)
            before, _, step = str(graph.value(finding, SH.value)).partition("/@")
            assert before == "/ExampleRecord"
            assert step == f"*[local-name()='origin' and namespace-uri()='{THE_NAMESPACE}']"

    class TestGivenEveryCensusFinding:
        def test_is_a_backlog_item_rather_than_a_defect_in_the_document(self, crate):
            """is only information (`sh:Info`), not a defect in the document"""
            for _, graph, finding in every(crate):
                assert graph.value(finding, SH.resultSeverity) == SH.Info

    class TestGivenTheSyntheticAdaptersAccounting:
        """given the synthetic adapter's accounting"""

        def test_carries_no_entry_for_any_path_its_census_findings_name(self, crate):
            accounted = {str(path) for path in accounting_of(crate).objects(None, BRIDGE.sourcePath)}
            assert accounted
            for _, graph, finding in every(crate):
                assert str(graph.value(finding, SH.value)) not in accounted
