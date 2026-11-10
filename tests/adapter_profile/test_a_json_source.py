import pytest
from rdflib import Literal, URIRef

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


LISTING_SCHEMA = "schema/example-listing.schema.json"
LISTING_INPUT = "fixtures/in/json-0008.json"
THE_SUBSCHEMA = "example-listing.schema.json#/definitions/record, the envelope's bridge:sourceSchema"


class TestDeclaringAJSONSourceFormat:
    """Declaring a JSON source format · bridge:recordPath, bridge:rootMember

    A JSON source has no element names, so its adapter says where the records are with a JSONPath, in a subset a Bridge
    reads without a JSONPath library.
    """

    class TestGivenACrateThatDeclaresItRightly:
        def test_reports_nothing_for_a_json_adapter_that_conforms(self, json_crate):
            """reports nothing for a JSON adapter that conforms"""
            assert not shape_file_messages(json_crate, "adapter.ttl")
            assert not shape_file_messages(json_crate, "envelope.ttl")
            assert not shape_file_messages(json_crate, "media_types.ttl")

        def test_reports_nothing_for_a_record_path_whose_name_shorthand_is_not_ascii(self, json_crate):
            json_crate.graph.set(
                (envelope_named(json_crate, "set"), BRIDGE.jsonPathOfEachRecord, Literal("$.récords[*]"))
            )
            assert not shape_file_messages(json_crate, "envelope.ttl")

        def test_reports_nothing_for_a_record_path_written_with_brackets(self, json_crate):
            json_crate.graph.set(
                (envelope_named(json_crate, "set"), BRIDGE.jsonPathOfEachRecord, Literal("$['records'][*]"))
            )
            assert not shape_file_messages(json_crate, "envelope.ttl")

    class TestGivenACrateThatDeclaresItWrongly:
        def test_reports_a_source_media_type_no_lift_applies_to(self, json_crate):
            json_crate.graph.set((json_crate.root, BRIDGE.sourceMediaType, Literal("text/csv")))
            assert "is one a lift applies to" in shape_file_messages(json_crate, "adapter.ttl")

        def test_reports_a_json_adapter_naming_an_element_name_of_each_record(self, json_crate):
            """reports a JSON adapter naming an element name of each record"""
            json_crate.graph.add((json_crate.root, BRIDGE.elementNameOfEachRecord, Literal("ExampleRecord")))
            assert "An adapter whose bridge:sourceMediaType is JSON carries no bridge:elementNameOfEachRecord" in (
                shape_file_messages(json_crate, "adapter.ttl")
            )

        def test_reports_an_xml_adapter_naming_no_element_name_of_each_record(self, crate):
            """reports an XML adapter naming no element name of each record"""
            crate.graph.remove((crate.root, BRIDGE.elementNameOfEachRecord, None))
            assert "An adapter whose bridge:sourceMediaType is XML carries a bridge:elementNameOfEachRecord" in (
                shape_file_messages(crate, "adapter.ttl")
            )

        def test_reports_a_json_envelope_naming_no_record_path(self, json_crate):
            """reports a JSON envelope naming no record path"""
            json_crate.graph.remove((envelope_named(json_crate, "set"), BRIDGE.jsonPathOfEachRecord, None))
            assert "carries a bridge:docRootMemberName and a bridge:jsonPathOfEachRecord" in shape_file_messages(
                json_crate, "envelope.ttl"
            )

        def test_reports_a_json_envelope_naming_no_root_member(self, json_crate):
            """reports a JSON envelope naming no root member"""
            json_crate.graph.remove((envelope_named(json_crate, "record"), BRIDGE.docRootMemberName, None))
            assert "carries a bridge:docRootMemberName and a bridge:jsonPathOfEachRecord" in shape_file_messages(
                json_crate, "envelope.ttl"
            )

        def test_reports_a_json_envelope_naming_a_document_root_element(self, json_crate):
            """reports a JSON envelope naming a document root element"""
            json_crate.graph.add((envelope_named(json_crate, "set"), BRIDGE.docRootElementName, Literal("Set")))
            assert "and no bridge:docRootElementName" in shape_file_messages(json_crate, "envelope.ttl")

        def test_reports_an_xml_envelope_naming_a_json_record_path(self, crate):
            """reports an XML envelope naming a JSON record path"""
            envelope = next(crate.graph.objects(crate.root, BRIDGE.envelope))
            crate.graph.add((envelope, BRIDGE.jsonPathOfEachRecord, Literal("$")))
            assert (
                "and none of bridge:docRootMemberName, bridge:docRootMemberValue and bridge:jsonPathOfEachRecord"
                in (shape_file_messages(crate, "envelope.ttl"))
            )

        def test_reports_a_record_path_outside_the_subset(self, json_crate):
            json_crate.graph.set(
                (envelope_named(json_crate, "set"), BRIDGE.jsonPathOfEachRecord, Literal("$..records"))
            )
            assert "written in the subset of RFC 9535 JSONPath" in shape_file_messages(json_crate, "envelope.ttl")

        @pytest.mark.parametrize("path", ["$.record-list[*]", "$.a$b", "$.x~y"])
        def test_reports_a_record_path_whose_name_shorthand_rfc_9535_does_not_allow(self, json_crate, path):
            """reports a record path whose name shorthand RFC 9535 does not allow"""
            json_crate.graph.set((envelope_named(json_crate, "set"), BRIDGE.jsonPathOfEachRecord, Literal(path)))
            assert "written in the subset of RFC 9535 JSONPath" in shape_file_messages(json_crate, "envelope.ttl")
            with pytest.raises(ValueError):
                segments_of(path)


class TestInputsFindingsAndQueriesOfAJSONSource:
    """Inputs, findings and queries of a JSON source · adapter/profile/must/inputs.py, expected_findings.py, source_accounting.py, queries.py

    The same four requirements, as they read a JSON source: inputs against a JSON Schema, findings selecting by JSON
    Pointer, and paths written as member names.
    """

    class TestGivenAJSONInputAndItsSchema:
        """given a JSON input and its schema"""

        def test_reports_nothing_for_committed_json_inputs_whose_failures_their_findings_record(self, json_crate):
            """reports nothing for committed JSON inputs whose failures their findings record"""
            assert not said(inputs, json_crate)

        def test_reports_a_json_schema_failure_the_expected_findings_do_not_record(self, json_package):
            """reports a JSON schema failure the expected findings do not record"""
            json_package.edit(FINDINGS_0003, f"<{DRAFT_06}4>", f"<{DRAFT_06}25>")
            json_package.edit(FINDINGS_0003, 'rdf:value "/version"', 'rdf:value "/accession"')
            assert "/records/0/version: 0 is less than the minimum of 1" in said(inputs, json_package.crate)

        def test_reports_a_json_input_that_is_not_a_json_text(self, json_package):
            """reports a JSON input that is not a JSON text"""
            json_package.edit("fixtures/in/json-0002.json", '"kind": "record",', '"kind": "record"')
            assert "json-0002.json is not a JSON text in UTF-8" in said(inputs, json_package.crate)

        def test_reports_a_json_input_escaping_a_lone_surrogate(self, json_package):
            """reports a JSON input escaping a lone surrogate"""
            json_package.edit("fixtures/in/json-0003.json", '"label": 5', '"label": "\\ud800"')
            assert "json-0003.json is not a JSON text in UTF-8" in said(inputs, json_package.crate)

        def test_reports_nothing_for_a_json_schema_failure_on_a_null_member_its_findings_record(self, json_package):
            """reports nothing for a JSON schema failure on a null member its findings record"""
            json_package.edit("fixtures/in/json-0003.json", '"label": 5', '"label": null')
            assert not said(inputs, json_package.crate)
            assert not said(expected_findings, json_package.crate)

        def test_reports_a_json_schema_naming_another_draft(self, json_package):
            """reports a JSON schema naming another draft"""
            json_package.edit(RECORD_SCHEMA, "draft-06", "draft-07")
            assert "names no JSON Schema draft-06 as its $schema" in said(inputs, json_package.crate)

        def test_reports_a_ref_to_nothing_in_the_package(self, json_package):
            """reports a `$ref` to nothing in the package"""
            json_package.edit(RECORD_SCHEMA, '"$ref": "#/definitions/positiveInteger"', '"$ref": "other.schema.json"')
            assert "which is not a file in this package" in said(inputs, json_package.crate)

        def test_reports_a_json_adapter_whose_schema_is_an_xsd(self, json_crate):
            """reports a JSON adapter whose schema is an XSD"""
            schema = json_crate.graph.value(json_crate.root, BRIDGE.sourceSchema)
            json_crate.graph.set((schema, SCHEMA.encodingFormat, Literal("application/xml")))
            assert "where a JSON source is validated against a JSON Schema" in said(inputs, json_crate)

        def test_reports_nothing_for_a_fractional_value_the_schema_holds_to_a_fractional_multiple(self, json_package):
            json_package.edit(
                RECORD_SCHEMA,
                '"label": {"type": "string"}',
                '"label": {"type": ["string", "number"], "multipleOf": 0.5}',
            )
            json_package.edit("fixtures/in/json-0001.json", '"label": "first synthetic JSON record"', '"label": 1.5')
            assert "json-0001" not in said(inputs, json_package.crate)

        def test_reports_a_fractional_value_that_is_no_multiple_of_the_schemas_fraction(self, json_package):
            """reports a fractional value that is no multiple of the schema's fraction"""
            json_package.edit(
                RECORD_SCHEMA,
                '"label": {"type": "string"}',
                '"label": {"type": ["string", "number"], "multipleOf": 0.5}',
            )
            json_package.edit("fixtures/in/json-0001.json", '"label": "first synthetic JSON record"', '"label": 1.2')
            assert "is not a multiple of 0.5" in said(inputs, json_package.crate)

        def test_reports_nothing_for_an_integer_written_with_a_zero_fraction(self, json_package):
            json_package.edit("fixtures/in/json-0001.json", '"version": 3', '"version": 3.0')
            assert "json-0001" not in said(inputs, json_package.crate)

    class TestGivenAnExpectedFindingOfAJSONInput:
        """given an expected finding of a JSON input"""

        def test_reports_nothing_for_the_committed_json_findings(self, json_crate):
            """reports nothing for the committed JSON findings"""
            assert not said(expected_findings, json_crate)

        def test_reports_a_json_finding_selecting_by_xpath(self, json_package):
            """reports a JSON finding selecting by XPath"""
            json_package.edit(
                FINDINGS_0001,
                'a oa:FragmentSelector ; dcterms:conformsTo <https://www.rfc-editor.org/rfc/rfc6901> ; rdf:value "/note"',
                'a oa:XPathSelector ; rdf:value "note"',
                times=4,
            )
            assert "where a finding about a JSON document selects by an oa:FragmentSelector" in said(
                expected_findings, json_package.crate
            )

        def test_reports_a_json_pointer_selecting_no_node(self, json_package):
            """reports a JSON pointer selecting no node"""
            json_package.edit(FINDINGS_0001, 'rdf:value "/records/1"', 'rdf:value "/records/7"', times=2)
            assert "'/records/7' selects no node of json-0001.json" in said(expected_findings, json_package.crate)

        def test_reports_a_json_pointer_selecting_a_node_that_is_no_record(self, json_package):
            """reports a JSON pointer selecting a node that is no record"""
            json_package.edit(FINDINGS_0001, 'rdf:value "/records/1"', 'rdf:value "/records"', times=2)
            assert "'/records' selects a node of json-0001.json that is no record" in said(
                expected_findings, json_package.crate
            )

        def test_reports_a_refinement_selecting_no_node_of_the_record(self, json_package):
            json_package.edit(FINDINGS_0003, 'rdf:value "/label"', 'rdf:value "/absent"')
            assert "'/absent' selects no node of the record '/records/0' selects" in said(
                expected_findings, json_package.crate
            )

        def test_reports_a_json_pointer_whose_percent_encoding_is_not_utf_8_as_selecting_no_node(self, json_package):
            """reports a JSON pointer whose percent encoding is not UTF-8 as selecting no node"""
            json_package.edit(FINDINGS_0003, 'rdf:value "/label"', 'rdf:value "/%FF"')
            assert "'/%FF' selects no node of the record '/records/0' selects" in said(
                expected_findings, json_package.crate
            )
            assert "/records/0/label: " in said(inputs, json_package.crate)

        def test_reports_an_xsd_rule_as_the_body_of_a_json_schema_finding(self, json_package):
            """reports an XSD rule as the body of a JSON schema finding"""
            json_package.edit(FINDINGS_0003, f"<{DRAFT_06}4>", "<https://www.w3.org/TR/xmlschema-1/#cvc-complex-type>")
            assert "the anchor of a JSON Schema draft-06 validation keyword" in said(
                expected_findings, json_package.crate
            )

    class TestGivenTheAccountingOfAJSONSource:
        """given the accounting of a JSON source"""

        def test_reports_a_json_source_path_written_in_steps_it_cannot_read(self, json_package):
            """reports a JSON source path written in steps it cannot read"""
            json_package.edit("vocab/example-accounting.ttl", '"/label"', '"label"')
            assert "label is written in steps this lint cannot read" in said(source_accounting, json_package.crate)

        def test_reports_a_carried_json_path_no_mapping_mentions(self, json_package):
            """reports a carried JSON path no mapping mentions"""
            json_package.edit("vocab/example-accounting.ttl", '"/label"', '"/caption"')
            assert "/caption is bridge:carried, where no bridge:mapping of this adapter mentions caption" in said(
                source_accounting, json_package.crate
            )

        def test_reports_nothing_for_the_committed_json_accounting(self, json_crate):
            """reports nothing for the committed JSON accounting"""
            assert not said(source_accounting, json_crate)

        def test_reports_nothing_for_a_carried_json_path_a_mapping_mentions_with_an_escaped_local_name(
            self, json_package
        ):
            """reports nothing for a carried JSON path a mapping mentions with an escaped local name"""
            json_package.edit("vocab/example-accounting.ttl", '"/label"', '"/a~0b"')
            json_package.edit("in/example-record.rq", "xyz:label ?label", "xyz:a\~b ?label")
            assert "mentions a~b" not in said(source_accounting, json_package.crate)

    class TestGivenAFindingsQueryOfAJSONSource:
        """given a findings query of a JSON source"""

        def test_reports_a_json_findings_query_constructing_an_xpath_selector(self, json_package):
            """reports a JSON findings query constructing an XPath selector"""
            json_package.edit(
                "in/example-findings.rq",
                """a oa:FragmentSelector ;
        dcterms:conformsTo <https://www.rfc-editor.org/rfc/rfc6901> ;""",
                "a oa:XPathSelector ;",
            )
            assert "where a finding about a JSON document selects by oa:FragmentSelector" in "\n".join(
                queries.malformed(json_package.crate)
            )

        def test_reports_a_json_findings_query_whose_pointer_does_not_conform_to_rfc_6901(self, json_package):
            """reports a JSON findings query whose pointer does not conform to RFC 6901"""
            json_package.edit(
                "in/example-findings.rq",
                """a oa:FragmentSelector ;
        dcterms:conformsTo <https://www.rfc-editor.org/rfc/rfc6901> ;""",
                "a oa:FragmentSelector ;",
            )
            assert "whose dcterms:conformsTo is not <https://www.rfc-editor.org/rfc/rfc6901>" in "\n".join(
                queries.malformed(json_package.crate)
            )

        def test_reports_nothing_for_the_committed_json_queries(self, json_crate):
            """reports nothing for the committed JSON queries"""
            assert not list(queries.malformed(json_crate))

    class TestGivenAnEnvelopeNamingASourceSchemaOfItsOwn:
        def test_validates_a_record_against_the_source_schema_its_envelope_names_not_the_adapters(self, json_package):
            """validates a record against the source schema its envelope names, not the adapter's"""
            json_package.edit(LISTING_INPUT, ', "label": "a record read in the listing envelope"', "")
            assert f"/records/0 of json-0008.json does not validate against {THE_SUBSCHEMA}" in said(
                inputs, json_package.crate
            )

        def test_resolves_a_ref_of_the_subschema_a_fragment_names_against_the_whole_schema_document(self, json_package):
            """resolves a `$ref` of the subschema a fragment names against the whole schema document"""
            json_package.edit(LISTING_INPUT, '"version": 1,', '"version": 0,')
            assert "/records/0/version: 0 is less than the minimum of 1" in said(inputs, json_package.crate)
            assert THE_SUBSCHEMA in said(inputs, json_package.crate)

        def test_reports_a_source_schema_fragment_naming_no_subschema(self, json_package):
            json_package.edit("ro-crate-metadata.json", "#/definitions/record", "#/definitions/absent")
            assert "example-listing.schema.json holds no subschema at #/definitions/absent" in said(
                inputs, json_package.crate
            )

        def test_reports_a_source_schema_fragment_that_is_no_json_pointer(self, json_package):
            """reports a source schema fragment that is no JSON pointer"""
            json_package.edit("ro-crate-metadata.json", "#/definitions/record", "#record")
            assert "#record is not a JSON Pointer" in said(inputs, json_package.crate)

        def test_reports_an_envelope_carrying_two_source_schemas(self, json_crate):
            listing = envelope_named(json_crate, "listing")
            json_crate.graph.add(
                (listing, BRIDGE.sourceSchema, json_crate.graph.value(json_crate.root, BRIDGE.sourceSchema))
            )
            assert "at most one bridge:sourceSchema" in shape_file_messages(json_crate, "envelope.ttl")

        def test_reports_an_envelope_source_schema_naming_no_file_of_the_crate(self, json_crate):
            listing = envelope_named(json_crate, "listing")
            schema = json_crate.graph.value(listing, BRIDGE.sourceSchema)
            json_crate.graph.set((listing, BRIDGE.sourceSchema, URIRef(str(schema).replace("listing", "absent"))))
            assert "names a crate File entity" in shape_file_messages(json_crate, "envelope.ttl")

        def test_reports_nothing_for_an_adapters_source_schema_naming_a_subschema_of_a_crate_file(self, json_crate):
            """reports nothing for an adapter's source schema naming a subschema of a crate file"""
            listing = envelope_named(json_crate, "listing")
            json_crate.graph.set(
                (json_crate.root, BRIDGE.sourceSchema, json_crate.graph.value(listing, BRIDGE.sourceSchema))
            )
            assert not shape_file_messages(json_crate, "adapter.ttl")
