from rdflib import URIRef

import schema_imports
from _terms import BRIDGE

A_SCHEMA = """<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema" elementFormDefault="qualified">
{body}
</xs:schema>
"""


def part(name, body=""):
    return A_SCHEMA.format(body=body), f"schema/{name}.xsd"


def including(package, included, by="example-record"):
    package.edit(
        f"schema/{by}.xsd",
        '<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema" elementFormDefault="qualified">',
        '<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema" elementFormDefault="qualified">\n'
        f'  <xs:include schemaLocation="{included}.xsd"/>',
    )


def written(package, name, body=""):
    text, path = part(name, body)
    package.write(path, text)


def declared(package, crate, name, on=None):
    iri = URIRef(package.path.resolve().as_uri().rstrip("/") + f"/schema/{name}.xsd")
    crate.graph.add((crate.root if on is None else on, BRIDGE.schemaImport, iri))


def said(crate):
    return "\n".join(schema_imports.undeclared(crate))


class TestSchemaFilesASchemaIncludesOrImports:
    """Schema files a schema includes or imports · adapter/profile/must/schema_imports.py, bridge:schemaImport

    A Bridge fetches nothing, so every file a named schema reaches by include, import or redefine is declared on the
    root entity or an envelope.
    """

    class TestGivenASchemaFileAnAdaptersSchemasReach:
        """given a schema file an adapter's schemas reach"""

        def test_reports_nothing_for_an_adapter_whose_schemas_are_the_ones_it_names(self, crate):
            assert not said(crate)

        def test_reports_a_schema_file_a_named_schema_includes_when_no_bridge_schemaimport_declares_it(self, package):
            """reports a schema file a named schema includes when no `bridge:schemaImport` declares it"""
            written(package, "example-part")
            including(package, "example-part")
            assert "schema/example-part.xsd is included or imported by a schema of the adapter" in said(package.crate)

        def test_reports_nothing_for_a_schema_file_a_named_schema_includes_once_the_root_declares_it(self, package):
            written(package, "example-part")
            including(package, "example-part")
            crate = package.crate
            declared(package, crate, "example-part")
            assert not said(crate)

        def test_reports_a_schema_file_reached_only_through_another_include(self, package):
            written(package, "example-part", '<xs:include schemaLocation="example-deeper.xsd"/>')
            written(package, "example-deeper")
            including(package, "example-part")
            crate = package.crate
            declared(package, crate, "example-part")
            assert "schema/example-deeper.xsd is included or imported" in said(crate)
            declared(package, crate, "example-deeper")
            assert not said(crate)

        def test_reports_a_schema_file_included_by_the_document_schema_of_an_envelope(self, package):
            written(package, "example-part")
            including(package, "example-part", by="example-set")
            assert "schema/example-part.xsd is included or imported" in said(package.crate)

        def test_accepts_a_declaration_on_an_envelope_as_on_the_root(self, package):
            written(package, "example-part")
            including(package, "example-part")
            crate = package.crate
            declared(package, crate, "example-part", on=next(crate.graph.subjects(BRIDGE.documentSchema)))
            assert not said(crate)

        def test_reports_a_declaration_on_an_entity_that_is_neither_the_root_nor_an_envelope(self, package):
            written(package, "example-part")
            including(package, "example-part")
            crate = package.crate
            declared(
                package,
                crate,
                "example-part",
                on=URIRef(package.path.resolve().as_uri().rstrip("/") + "/schema/example-record.xsd"),
            )
            assert "schema/example-part.xsd is included or imported" in said(crate)

        def test_follows_a_redefine_as_it_follows_an_include(self, package):
            written(package, "example-part")
            including(package, "example-part")
            package.edit("schema/example-record.xsd", "<xs:include ", "<xs:redefine ")
            assert "schema/example-part.xsd is included or imported" in said(package.crate)

        def test_reports_a_declaration_no_schema_of_the_adapter_includes_or_imports(self, package):
            written(package, "example-part")
            crate = package.crate
            declared(package, crate, "example-part")
            assert "bridge:schemaImport names schema/example-part.xsd, which no schema of the adapter" in said(crate)

        def test_asks_nothing_for_the_schema_a_bridge_supplies_for_the_xml_namespace(self, package):
            """asks nothing for the schema a Bridge supplies for the XML namespace"""
            written(
                package,
                "example-part",
                '<xs:import namespace="http://www.w3.org/XML/1998/namespace" schemaLocation="http://www.w3.org/2001/xml.xsd"/>',
            )
            including(package, "example-part")
            crate = package.crate
            declared(package, crate, "example-part")
            assert not said(crate)

        def test_reports_nothing_for_a_json_source(self, json_crate):
            """reports nothing for a JSON source"""
            assert not said(json_crate)
