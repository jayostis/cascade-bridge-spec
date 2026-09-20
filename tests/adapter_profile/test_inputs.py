from rdflib import Literal

import inputs
from _terms import BRIDGE, SCHEMA

A_DOCUMENT_SCHEMA_HOLDING_EVERY_RECORD_TO_NOTHING = """<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="ExampleRecordSet">
    <xs:complexType>
      <xs:sequence>
        <xs:any processContents="skip" maxOccurs="unbounded"/>
      </xs:sequence>
    </xs:complexType>
  </xs:element>
</xs:schema>
"""

AN_INPUT_IN_THE_SCHEMA_LANGUAGE_THIS_LINT_CANNOT_READ = '{"ExampleRecord": [{"Accession": "EX000001"}]}\n'


def schemas_of(crate):
    return set(crate.graph.objects(crate.root, BRIDGE.sourceSchema)) | set(
        crate.graph.objects(None, BRIDGE.documentSchema)
    )


def test_reports_nothing_for_an_input_that_satisfies_its_envelopes_schema(crate):
    assert not list(inputs.invalid(crate))


def test_reports_an_input_that_does_not_satisfy_its_schema(package):
    package.edit("fixtures/in/example-0001.xml", 'Version="3"', 'Version="third"')
    assert "does not validate against" in "\n".join(inputs.invalid(package.crate))


def test_reports_nothing_for_a_schema_failure_its_entrys_expected_findings_record(crate):
    assert not [message for message in inputs.invalid(crate) if "example-0003" in message]


def test_reports_a_schema_failure_its_entrys_expected_findings_record_at_a_lesser_severity(package):
    package.edit("fixtures/findings/example-0003.ttl", "sh:Violation", "sh:Warning", times=2)
    assert "example-0003.xml does not validate against example-set.xsd" in "\n".join(inputs.invalid(package.crate))


def test_reports_a_schema_failure_its_entrys_expected_findings_record_against_another_node(package):
    package.edit(
        "fixtures/findings/example-0003.ttl",
        '"/ExampleRecordSet"',
        '"/ExampleRecordSet/ExampleRecord[1]"',
        times=2,
    )
    assert "example-0003.xml does not validate against example-set.xsd" in "\n".join(inputs.invalid(package.crate))


def test_reports_a_record_that_fails_the_source_schema_where_the_document_schema_passes_the_document(package):
    package.write("schema/example-set.xsd", A_DOCUMENT_SCHEMA_HOLDING_EVERY_RECORD_TO_NOTHING)
    package.edit("fixtures/in/example-0001.xml", 'Version="1"', 'Version="first"')
    assert (
        "/ExampleRecordSet/ExampleRecord[2] of example-0001.xml does not validate against "
        "example-record.xsd, the adapter's bridge:sourceSchema"
    ) in "\n".join(inputs.invalid(package.crate))


def test_validates_a_record_against_the_source_schema_when_its_envelope_declares_no_document_schema(package):
    package.edit("fixtures/in/example-0002.xml", 'Version="2"', 'Version="second"')
    assert (
        "/ExampleRecord of example-0002.xml does not validate against "
        "example-record.xsd, the adapter's bridge:sourceSchema"
    ) in "\n".join(inputs.invalid(package.crate))


def test_reports_an_input_holding_no_record_of_the_element_name_the_adapter_declares(crate):
    crate.graph.set((crate.root, BRIDGE.elementNameOfEachRecord, Literal("MissingRecord")))
    assert ("example-0001.xml holds no MissingRecord, the adapter's bridge:elementNameOfEachRecord") in "\n".join(
        inputs.invalid(crate)
    )


def test_reports_a_source_schema_no_record_was_validated_against_for_want_of_an_element_name(crate):
    crate.graph.remove((crate.root, BRIDGE.elementNameOfEachRecord, None))
    assert (
        "the adapter declares bridge:sourceSchema and no bridge:elementNameOfEachRecord, "
        "so no record of example-0001.xml was validated against it"
    ) in "\n".join(inputs.invalid(crate))


def test_holds_a_package_to_nothing_when_the_schema_language_is_one_it_cannot_read(package):
    crate = package.crate
    for schema in schemas_of(crate):
        crate.graph.set((schema, SCHEMA.encodingFormat, Literal("application/schema+json")))
    for _, source, _ in inputs.committed_inputs(crate):
        crate.file_at(source).write_text(AN_INPUT_IN_THE_SCHEMA_LANGUAGE_THIS_LINT_CANNOT_READ, encoding="utf-8")
    assert not list(inputs.invalid(crate))


def test_reports_an_input_that_is_not_well_formed_xml_where_the_schema_is_one_it_reads(package):
    package.edit("fixtures/in/example-0001.xml", "</ExampleRecordSet>", "")
    assert "example-0001.xml is not well-formed XML" in "\n".join(inputs.invalid(package.crate))


def test_reports_a_schema_that_is_not_a_file_in_the_package(package):
    crate = package.crate
    schema = crate.graph.value(crate.root, BRIDGE.sourceSchema)
    crate.file_at(schema).unlink()
    assert "which is not a file in this package" in "\n".join(inputs.invalid(crate))


def test_reports_a_schema_declared_in_a_media_type_it_cannot_validate_against(crate):
    for schema in schemas_of(crate):
        crate.graph.set((schema, SCHEMA.encodingFormat, Literal("text/plain")))
    assert "which this lint cannot validate against" in "\n".join(inputs.invalid(crate))


def test_reports_a_schema_that_declares_no_media_type(crate):
    for schema in schemas_of(crate):
        crate.graph.remove((schema, SCHEMA.encodingFormat, None))
    assert "declares no encodingFormat" in "\n".join(inputs.invalid(crate))


def test_reports_a_schema_that_does_not_compile_for_every_input_validated_against_it(package):
    crate = package.crate
    crate.graph.remove((None, BRIDGE.documentSchema, None))
    tests = list(inputs.committed_inputs(crate))
    assert len(tests) > 1, "the fixture has more than one input to share the schema"
    source_schema = crate.graph.value(crate.root, BRIDGE.sourceSchema)
    crate.file_at(source_schema).write_text("<not-a-schema/>", encoding="utf-8")
    faults = [message for message in inputs.invalid(crate) if "does not compile" in message]
    assert len(faults) == len(tests)


def test_reports_a_schema_failure_its_entrys_expected_findings_record_as_a_gap_rather_than_a_broken_rule(package):
    for rule in ("cvc-complex-type", "cvc-elt"):
        package.edit(
            "fixtures/findings/example-0003.ttl",
            f"<https://www.w3.org/TR/xmlschema-1/#{rule}>",
            "<https://example.org/synthetic-adapter/v1#no-term-for-a-free-text-note>",
        )
    assert "example-0003.xml does not validate against example-set.xsd" in "\n".join(inputs.invalid(package.crate))
