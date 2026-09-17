from rdflib import BNode, Literal
from rdflib.namespace import RDF

import shapes
from _terms import BRIDGE, MF


def test_reports_nothing_for_a_crate_and_manifest_that_conform(crate):
    assert not list(shapes.violations(crate))


def test_reports_a_manifest_that_does_not_point_back_at_the_adapter(crate):
    crate.graph.remove((crate.manifest_iri, BRIDGE.adapter, None))
    assert "whose bridge:adapter is this adapter" in "\n".join(shapes.violations(crate))


def result_of_a_conversion_test(crate):
    test = next(crate.graph.subjects(RDF.type, BRIDGE.IsomorphicConversionTest))
    return crate.graph.value(test, MF.result)


def test_reports_a_conversion_result_that_names_no_expected_graph(crate):
    crate.graph.remove((result_of_a_conversion_test(crate), BRIDGE.expectedGraph, None))
    assert "bridge:expectedGraph" in "\n".join(shapes.violations(crate))


def test_reports_a_conversion_result_that_names_no_expected_findings(crate):
    crate.graph.remove((result_of_a_conversion_test(crate), BRIDGE.expectedFindings, None))
    assert "bridge:expectedFindings" in "\n".join(shapes.violations(crate))


def test_reports_a_stamp_predicate_that_is_not_an_iri(crate):
    crate.graph.add((crate.manifest_iri, BRIDGE.stampPredicate, Literal("generatedAtTime")))
    assert "bridge:stampPredicate" in "\n".join(shapes.violations(crate))


def test_reports_a_negative_records_processed_count(crate):
    test = next(crate.graph.subjects(RDF.type, BRIDGE.DatasetCompletionTest))
    result = crate.graph.value(test, MF.result)
    if result is None:
        result = BNode()
        crate.graph.add((test, MF.result, result))
    crate.graph.set((result, BRIDGE.recordsProcessedCount, Literal(-1)))
    assert "bridge:recordsProcessedCount" in "\n".join(shapes.violations(crate))
