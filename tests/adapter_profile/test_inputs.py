import inputs
from _terms import BRIDGE, SCHEMA
from rdflib import Literal


def test_reports_nothing_for_an_input_that_satisfies_its_envelopes_schema(crate):
    assert not list(inputs.invalid(crate))


def test_reports_an_input_that_does_not_satisfy_its_schema(package):
    package.edit("fixtures/in/example-0001.xml", 'Version="3"', 'Version="third"')
    assert "does not validate against" in "\n".join(inputs.invalid(package.crate))


def test_falls_back_to_the_adapters_source_schema_when_an_envelope_declares_none(crate):
    without = [
        envelope
        for envelope in crate.graph.objects(crate.root, BRIDGE.envelope)
        if crate.graph.value(envelope, BRIDGE.documentSchema) is None
    ]
    assert without, "the fixture carries an envelope declaring no document schema"
    schema, declared_by = inputs.schema_for(crate, without[0])
    assert declared_by == "bridge:sourceSchema"
    assert schema == crate.graph.value(crate.root, BRIDGE.sourceSchema)


def test_holds_a_package_to_nothing_when_the_schema_language_is_one_it_cannot_read(crate):
    schemas = set(crate.graph.objects(crate.root, BRIDGE.sourceSchema)) | set(
        crate.graph.objects(None, BRIDGE.documentSchema)
    )
    for schema in schemas:
        crate.graph.set((schema, SCHEMA.encodingFormat, Literal("application/json")))
    assert not list(inputs.invalid(crate)), (
        "a JSON source schema is outside v1-draft: a gap in this lint, not a "
        "fault in the package"
    )


def test_reports_a_schema_that_is_not_a_file_in_the_package(package):
    crate = package.crate
    schema = crate.graph.value(crate.root, BRIDGE.sourceSchema)
    crate.file_at(schema).unlink()
    assert "which is not a file in this package" in "\n".join(inputs.invalid(crate))


def test_reports_a_schema_declared_in_a_media_type_it_cannot_validate_against(crate):
    schemas = set(crate.graph.objects(crate.root, BRIDGE.sourceSchema)) | set(
        crate.graph.objects(None, BRIDGE.documentSchema)
    )
    for schema in schemas:
        crate.graph.set((schema, SCHEMA.encodingFormat, Literal("text/plain")))
    assert "which this lint cannot validate against" in "\n".join(inputs.invalid(crate))


def test_reports_a_schema_that_declares_no_media_type(crate):
    schemas = set(crate.graph.objects(crate.root, BRIDGE.sourceSchema)) | set(
        crate.graph.objects(None, BRIDGE.documentSchema)
    )
    for schema in schemas:
        crate.graph.remove((schema, SCHEMA.encodingFormat, None))
    assert "declares no encodingFormat" in "\n".join(inputs.invalid(crate))
