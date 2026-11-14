import pytest
from rdflib import BNode, Literal
from rdflib.namespace import RDF, XSD

import shapes
from _terms import BRIDGE, MF
from adapter_profile_world import AT_MOST_ONE_CONCERN, THE_CONCERNS


def result_of_a_conversion_test(crate):
    test = next(crate.graph.subjects(RDF.type, BRIDGE.IsomorphicConversionTest))
    return crate.graph.value(test, MF.result)


def action_of_a_conversion_test(crate):
    test = next(crate.graph.subjects(RDF.type, BRIDGE.IsomorphicConversionTest))
    return crate.graph.value(test, MF.action)


def an_identity_relation_test(crate):
    return next(crate.graph.subjects(RDF.type, BRIDGE.IdentityRelationTest))


class TestTheCrateAndItsTestManifestAsOneGraph:
    """The crate and its test manifest as one graph · adapter/profile/must/shapes.py, shapes/bridge.shapes.ttl

    The test manifest lists an adapter's cases: conversions of an input into an expected graph and expected findings,
    and identity relation tests over several conversions. The shapes are checked over the crate and the manifest
    together, since each names things in the other.
    """

    class TestGivenACrateAndManifestThatConform:
        def test_reports_nothing_for_a_crate_and_manifest_that_conform(self, crate):
            assert not list(shapes.violations(crate))

    class TestGivenATestTaggedWithItsConcern:
        @pytest.mark.parametrize("concern", THE_CONCERNS)
        def test_reports_nothing_for_a_test_tagged_with_one_of_the_five_concerns(self, crate, concern):
            crate.graph.add((an_identity_relation_test(crate), BRIDGE.concern, BRIDGE[concern.removeprefix("bridge:")]))
            assert not list(shapes.violations(crate))

        @pytest.mark.parametrize(
            "concerns",
            [["concernCode"], ["concernCodes", "concernDates"]],
            ids=["outside the scheme of the five", "two concerns"],
        )
        def test_reports_a_test_whose_concern_is_not_exactly_one_of_the_five(self, crate, concerns):
            for concern in concerns:
                crate.graph.add((an_identity_relation_test(crate), BRIDGE.concern, BRIDGE[concern]))
            assert AT_MOST_ONE_CONCERN in "\n".join(shapes.violations(crate))

    class TestGivenACrateOrManifestAtFaultInOneWay:
        def test_reports_a_manifest_that_does_not_point_back_at_the_adapter(self, crate):
            crate.graph.remove((crate.manifest_iri, BRIDGE.adapter, None))
            assert "whose bridge:adapter is this adapter" in "\n".join(shapes.violations(crate))

        def test_reports_a_conversion_result_that_names_no_expected_graph(self, crate):
            crate.graph.remove((result_of_a_conversion_test(crate), BRIDGE.expectedGraph, None))
            assert "bridge:expectedGraph" in "\n".join(shapes.violations(crate))

        def test_reports_a_conversion_result_that_names_no_expected_findings(self, crate):
            crate.graph.remove((result_of_a_conversion_test(crate), BRIDGE.expectedFindings, None))
            assert "bridge:expectedFindings" in "\n".join(shapes.violations(crate))

        def test_reports_facts_named_by_a_literal_rather_than_a_file_of_the_crate(self, crate):
            action = action_of_a_conversion_test(crate)
            crate.graph.remove((action, BRIDGE.facts, None))
            crate.graph.add((action, BRIDGE.facts, Literal("facts/example-registry.ttl")))
            assert "bridge:facts" in "\n".join(shapes.violations(crate))

        @pytest.mark.parametrize(
            "path",
            [Literal("/ExampleRecord/Novelty", lang="en"), Literal("/ExampleRecord/Novelty", datatype=XSD.anyURI)],
            ids=["a language-tagged string", "an xsd:anyURI"],
        )
        def test_reports_a_tested_unaccounted_path_that_is_no_plain_string(self, crate, path):
            crate.graph.add((an_identity_relation_test(crate), BRIDGE.testsUnaccountedSourcePath, path))
            assert "bridge:testsUnaccountedSourcePath, an xsd:string" in "\n".join(shapes.violations(crate))

        def test_reports_an_identity_relation_test_carrying_one_conversion(self, crate):
            action = crate.graph.value(an_identity_relation_test(crate), MF.action)
            crate.graph.remove((action, BRIDGE.conversion, next(crate.graph.objects(action, BRIDGE.conversion))))
            assert "exactly two bridge:conversion" in "\n".join(shapes.violations(crate))

        def test_reports_an_identity_relation_test_whose_result_is_no_boolean(self, crate):
            result = crate.graph.value(an_identity_relation_test(crate), MF.result)
            crate.graph.set((result, BRIDGE.sameRecord, Literal("yes")))
            assert "bridge:sameRecord, an xsd:boolean" in "\n".join(shapes.violations(crate))

        def test_reports_a_conversion_naming_an_envelope_the_adapter_does_not_list(self, crate):
            action = crate.graph.value(an_identity_relation_test(crate), MF.action)
            conversion = next(crate.graph.objects(action, BRIDGE.conversion))
            crate.graph.set((conversion, BRIDGE.envelope, crate.root))
            assert "one the manifest's adapter lists" in "\n".join(shapes.violations(crate))

        def test_reports_a_negative_records_processed_count(self, crate):
            test = next(crate.graph.subjects(RDF.type, BRIDGE.DatasetCompletionTest))
            result = crate.graph.value(test, MF.result)
            if result is None:
                result = BNode()
                crate.graph.add((test, MF.result, result))
            crate.graph.set((result, BRIDGE.recordsProcessedCount, Literal(-1)))
            assert "bridge:recordsProcessedCount" in "\n".join(shapes.violations(crate))
