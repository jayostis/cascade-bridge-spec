import pytest
from rdflib import Literal

import expected_findings
import inputs
import queries
import source_accounting
from _json_source import segments_of
from _terms import BRIDGE, SCHEMA
from adapter_profile_world import shape_file_messages

RECORD_SCHEMA = "schema/example-record.schema.json"
SET_ENVELOPE = "#envelope-set"
FINDINGS_0001 = "fixtures/findings/json-0001.ttl"
FINDINGS_0003 = "fixtures/findings/json-0003.ttl"
DRAFT_06 = "https://datatracker.ietf.org/doc/html/draft-wright-json-schema-validation-01#section-6."


def envelope_named(crate, name):
    return next(
        envelope
        for envelope in crate.graph.objects(crate.root, BRIDGE.envelope)
        if str(crate.graph.value(envelope, SCHEMA.name)) == name
    )


def said(check, crate):
    return "\n".join(check.faulty(crate) if hasattr(check, "faulty") else check.invalid(crate))


def test_reports_nothing_for_a_json_adapter_that_conforms(json_crate):
    assert not shape_file_messages(json_crate, "adapter.ttl")
    assert not shape_file_messages(json_crate, "envelope.ttl")
    assert not shape_file_messages(json_crate, "media_types.ttl")


def test_reports_a_source_media_type_no_lift_applies_to(json_crate):
    json_crate.graph.set((json_crate.root, BRIDGE.sourceMediaType, Literal("text/csv")))
    assert "is one a lift applies to" in shape_file_messages(json_crate, "adapter.ttl")


def test_reports_a_json_adapter_naming_an_element_name_of_each_record(json_crate):
    json_crate.graph.add((json_crate.root, BRIDGE.elementNameOfEachRecord, Literal("ExampleRecord")))
    assert "An adapter whose bridge:sourceMediaType is JSON carries no bridge:elementNameOfEachRecord" in (
        shape_file_messages(json_crate, "adapter.ttl")
    )


def test_reports_an_xml_adapter_naming_no_element_name_of_each_record(crate):
    crate.graph.remove((crate.root, BRIDGE.elementNameOfEachRecord, None))
    assert "An adapter whose bridge:sourceMediaType is XML carries a bridge:elementNameOfEachRecord" in (
        shape_file_messages(crate, "adapter.ttl")
    )


def test_reports_a_json_envelope_naming_no_record_path(json_crate):
    json_crate.graph.remove((envelope_named(json_crate, "set"), BRIDGE.jsonPathOfEachRecord, None))
    assert "carries a bridge:docRootMemberName and a bridge:jsonPathOfEachRecord" in shape_file_messages(
        json_crate, "envelope.ttl"
    )


def test_reports_a_json_envelope_naming_no_root_member(json_crate):
    json_crate.graph.remove((envelope_named(json_crate, "record"), BRIDGE.docRootMemberName, None))
    assert "carries a bridge:docRootMemberName and a bridge:jsonPathOfEachRecord" in shape_file_messages(
        json_crate, "envelope.ttl"
    )


def test_reports_a_json_envelope_naming_a_document_root_element(json_crate):
    json_crate.graph.add((envelope_named(json_crate, "set"), BRIDGE.docRootElementName, Literal("Set")))
    assert "and no bridge:docRootElementName" in shape_file_messages(json_crate, "envelope.ttl")


def test_reports_an_xml_envelope_naming_a_json_record_path(crate):
    envelope = next(crate.graph.objects(crate.root, BRIDGE.envelope))
    crate.graph.add((envelope, BRIDGE.jsonPathOfEachRecord, Literal("$")))
    assert "and none of bridge:docRootMemberName, bridge:docRootMemberValue and bridge:jsonPathOfEachRecord" in (
        shape_file_messages(crate, "envelope.ttl")
    )


def test_reports_a_record_path_outside_the_subset(json_crate):
    json_crate.graph.set((envelope_named(json_crate, "set"), BRIDGE.jsonPathOfEachRecord, Literal("$..records")))
    assert "written in the subset of RFC 9535 JSONPath" in shape_file_messages(json_crate, "envelope.ttl")


@pytest.mark.parametrize("path", ["$.record-list[*]", "$.a$b", "$.x~y"])
def test_reports_a_record_path_whose_name_shorthand_rfc_9535_does_not_allow(json_crate, path):
    json_crate.graph.set((envelope_named(json_crate, "set"), BRIDGE.jsonPathOfEachRecord, Literal(path)))
    assert "written in the subset of RFC 9535 JSONPath" in shape_file_messages(json_crate, "envelope.ttl")
    with pytest.raises(ValueError):
        segments_of(path)


def test_reports_nothing_for_a_record_path_whose_name_shorthand_is_not_ascii(json_crate):
    json_crate.graph.set((envelope_named(json_crate, "set"), BRIDGE.jsonPathOfEachRecord, Literal("$.récords[*]")))
    assert not shape_file_messages(json_crate, "envelope.ttl")


def test_reports_nothing_for_a_record_path_written_with_brackets(json_crate):
    json_crate.graph.set((envelope_named(json_crate, "set"), BRIDGE.jsonPathOfEachRecord, Literal("$['records'][*]")))
    assert not shape_file_messages(json_crate, "envelope.ttl")


def test_reports_nothing_for_committed_json_inputs_whose_failures_their_findings_record(json_crate):
    assert not said(inputs, json_crate)


def test_reports_a_json_schema_failure_the_expected_findings_do_not_record(json_package):
    json_package.edit(FINDINGS_0003, f"<{DRAFT_06}4>", f"<{DRAFT_06}25>")
    json_package.edit(FINDINGS_0003, 'rdf:value "/version"', 'rdf:value "/accession"')
    assert "/records/0/version: 0 is less than the minimum of 1" in said(inputs, json_package.crate)


def test_reports_a_json_input_that_is_not_a_json_text(json_package):
    json_package.edit("fixtures/in/json-0002.json", '"kind": "record",', '"kind": "record"')
    assert "json-0002.json is not a JSON text in UTF-8" in said(inputs, json_package.crate)


def test_reports_a_json_input_escaping_a_lone_surrogate(json_package):
    json_package.edit("fixtures/in/json-0003.json", '"label": 5', '"label": "\\ud800"')
    assert "json-0003.json is not a JSON text in UTF-8" in said(inputs, json_package.crate)


def test_reports_nothing_for_a_json_schema_failure_on_a_null_member_its_findings_record(json_package):
    json_package.edit("fixtures/in/json-0003.json", '"label": 5', '"label": null')
    assert not said(inputs, json_package.crate)
    assert not said(expected_findings, json_package.crate)


def test_reports_a_json_schema_naming_another_draft(json_package):
    json_package.edit(RECORD_SCHEMA, "draft-06", "draft-07")
    assert "names no JSON Schema draft-06 as its $schema" in said(inputs, json_package.crate)


def test_reports_a_ref_to_nothing_in_the_package_and_fetches_nothing(json_package):
    json_package.edit(RECORD_SCHEMA, '"$ref": "#/definitions/positiveInteger"', '"$ref": "other.schema.json"')
    assert "which is not a file in this package" in said(inputs, json_package.crate)


def test_reports_a_json_adapter_whose_schema_is_an_xsd(json_crate):
    schema = json_crate.graph.value(json_crate.root, BRIDGE.sourceSchema)
    json_crate.graph.set((schema, SCHEMA.encodingFormat, Literal("application/xml")))
    assert "where a JSON source is validated against a JSON Schema" in said(inputs, json_crate)


def test_reports_nothing_for_the_committed_json_findings(json_crate):
    assert not said(expected_findings, json_crate)


def test_reports_a_json_finding_selecting_by_xpath(json_package):
    json_package.edit(
        FINDINGS_0001,
        'a oa:FragmentSelector ; dcterms:conformsTo <https://www.rfc-editor.org/rfc/rfc6901> ; rdf:value "/note"',
        'a oa:XPathSelector ; rdf:value "note"',
        times=4,
    )
    assert "where a finding about a JSON document selects by an oa:FragmentSelector" in said(
        expected_findings, json_package.crate
    )


def test_reports_a_json_pointer_selecting_no_node(json_package):
    json_package.edit(FINDINGS_0001, 'rdf:value "/records/1"', 'rdf:value "/records/7"', times=2)
    assert "'/records/7' selects no node of json-0001.json" in said(expected_findings, json_package.crate)


def test_reports_a_json_pointer_selecting_a_node_that_is_no_record(json_package):
    json_package.edit(FINDINGS_0001, 'rdf:value "/records/1"', 'rdf:value "/records"', times=2)
    assert "'/records' selects a node of json-0001.json that is no record" in said(
        expected_findings, json_package.crate
    )


def test_reports_a_refinement_selecting_no_node_of_the_record(json_package):
    json_package.edit(FINDINGS_0003, 'rdf:value "/label"', 'rdf:value "/absent"')
    assert "'/absent' selects no node of the record '/records/0' selects" in said(expected_findings, json_package.crate)


def test_reports_a_json_pointer_whose_percent_encoding_is_not_utf_8_as_selecting_no_node(json_package):
    json_package.edit(FINDINGS_0003, 'rdf:value "/label"', 'rdf:value "/%FF"')
    assert "'/%FF' selects no node of the record '/records/0' selects" in said(expected_findings, json_package.crate)
    assert "/records/0/label: " in said(inputs, json_package.crate)


def test_reports_an_xsd_rule_as_the_body_of_a_json_schema_finding(json_package):
    json_package.edit(FINDINGS_0003, f"<{DRAFT_06}4>", "<https://www.w3.org/TR/xmlschema-1/#cvc-complex-type>")
    assert "the anchor of a JSON Schema draft-06 validation keyword" in said(expected_findings, json_package.crate)


def test_reports_a_json_source_path_written_in_steps_it_cannot_read(json_package):
    json_package.edit("vocab/example-accounting.ttl", '"/label"', '"label"')
    assert "label is written in steps this lint cannot read" in said(source_accounting, json_package.crate)


def test_reports_a_carried_json_path_no_mapping_mentions(json_package):
    json_package.edit("vocab/example-accounting.ttl", '"/label"', '"/caption"')
    assert "/caption is bridge:carried, where no bridge:mapping of this adapter mentions caption" in said(
        source_accounting, json_package.crate
    )


def test_reports_nothing_for_the_committed_json_accounting(json_crate):
    assert not said(source_accounting, json_crate)


def test_reports_a_json_findings_query_constructing_an_xpath_selector(json_package):
    json_package.edit(
        "in/example-findings.rq",
        """a oa:FragmentSelector ;
        dcterms:conformsTo <https://www.rfc-editor.org/rfc/rfc6901> ;""",
        "a oa:XPathSelector ;",
    )
    assert "where a finding about a JSON document selects by oa:FragmentSelector" in "\n".join(
        queries.malformed(json_package.crate)
    )


def test_reports_nothing_for_the_committed_json_queries(json_crate):
    assert not list(queries.malformed(json_crate))
