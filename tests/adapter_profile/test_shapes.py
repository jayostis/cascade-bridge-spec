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


def action_of_a_conversion_test(crate):
    test = next(crate.graph.subjects(RDF.type, BRIDGE.IsomorphicConversionTest))
    return crate.graph.value(test, MF.action)


def test_reports_facts_named_by_a_literal_rather_than_a_file_of_the_crate(crate):
    action = action_of_a_conversion_test(crate)
    crate.graph.remove((action, BRIDGE.facts, None))
    crate.graph.add((action, BRIDGE.facts, Literal("facts/example-registry.ttl")))
    assert "bridge:facts" in "\n".join(shapes.violations(crate))


def an_identity_relation_test(crate):
    return next(crate.graph.subjects(RDF.type, BRIDGE.IdentityRelationTest))


def test_reports_an_identity_relation_test_carrying_one_conversion(crate):
    action = crate.graph.value(an_identity_relation_test(crate), MF.action)
    crate.graph.remove((action, BRIDGE.conversion, next(crate.graph.objects(action, BRIDGE.conversion))))
    assert "exactly two bridge:conversion" in "\n".join(shapes.violations(crate))


def test_reports_an_identity_relation_test_whose_result_is_no_boolean(crate):
    result = crate.graph.value(an_identity_relation_test(crate), MF.result)
    crate.graph.set((result, BRIDGE.sameRecord, Literal("yes")))
    assert "bridge:sameRecord, an xsd:boolean" in "\n".join(shapes.violations(crate))


def test_reports_a_conversion_naming_an_envelope_the_adapter_does_not_list(crate):
    action = crate.graph.value(an_identity_relation_test(crate), MF.action)
    conversion = next(crate.graph.objects(action, BRIDGE.conversion))
    crate.graph.set((conversion, BRIDGE.envelope, crate.root))
    assert "one the manifest's adapter lists" in "\n".join(shapes.violations(crate))


def test_reports_a_negative_records_processed_count(crate):
    test = next(crate.graph.subjects(RDF.type, BRIDGE.DatasetCompletionTest))
    result = crate.graph.value(test, MF.result)
    if result is None:
        result = BNode()
        crate.graph.add((test, MF.result, result))
    crate.graph.set((result, BRIDGE.recordsProcessedCount, Literal(-1)))
    assert "bridge:recordsProcessedCount" in "\n".join(shapes.violations(crate))
