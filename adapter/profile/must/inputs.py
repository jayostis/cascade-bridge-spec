import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _crate import file_name_of
from _findings import report_findings
from _terms import BRIDGE, MF, SCHEMA
from rocrate_validator.models import ValidationContext
from rocrate_validator.requirements.python import PyFunctionCheck, check, requirement

XSD_MEDIA_TYPES = {"application/xml", "text/xml"}
JSON_SCHEMA_MEDIA_TYPES = {"application/json", "application/schema+json"}


def schema_for(crate, envelope):
    document_schema = crate.graph.value(envelope, BRIDGE.documentSchema)
    if document_schema is not None:
        return document_schema, "bridge:documentSchema"
    return crate.graph.value(crate.root, BRIDGE.sourceSchema), "bridge:sourceSchema"


def committed_inputs(crate):
    for test in crate.entries:
        action = crate.graph.value(test, MF.action)
        if action is None:
            continue
        source = crate.graph.value(action, BRIDGE.input)
        if source is None:
            continue
        yield test, source, crate.graph.value(action, BRIDGE.envelope)


class XsdSchemas:
    """Each lookup is a compiled schema, a fault to report, or None for a schema language this lint does not read."""

    def __init__(self, crate, etree):
        self.crate = crate
        self.etree = etree
        self.looked_up = {}

    def lookup(self, schema_iri, declared_by):
        key = (schema_iri, declared_by)
        if key not in self.looked_up:
            self.looked_up[key] = self.compile(schema_iri, declared_by)
        return self.looked_up[key]

    def compile(self, schema_iri, declared_by):
        declared = self.crate.graph.value(schema_iri, SCHEMA.encodingFormat)
        media_type = str(declared or "")
        if media_type in JSON_SCHEMA_MEDIA_TYPES:
            return None
        path = self.crate.file_at(schema_iri)
        if path is None:
            return f"{declared_by} names {schema_iri}, which is not a file in this package"
        if declared is None:
            return (
                f"{path.name} declares no encodingFormat, so this lint cannot "
                "tell which schema language to validate against"
            )
        if media_type not in XSD_MEDIA_TYPES:
            return f"{path.name} is declared {media_type}, which this lint cannot validate against"
        try:
            return self.etree.XMLSchema(self.etree.parse(str(path)))
        except self.etree.Error as error:
            return f"{path.name} is declared XML and does not compile as an XSD 1.0 schema: {error}"


def invalid(crate):
    inputs = list(committed_inputs(crate))
    if not inputs:
        return

    try:
        from lxml import etree
    except ImportError:
        yield "lxml is not installed (pip install lxml), so no input was validated"
        return

    schemas = XsdSchemas(crate, etree)
    for test, source, envelope in inputs:
        name = crate.name_of(test)
        schema_iri, declared_by = schema_for(crate, envelope)
        if schema_iri is None:
            yield (
                f"{name}: its envelope declares no bridge:documentSchema and "
                "the adapter declares no bridge:sourceSchema, so there is "
                "nothing to validate the input against"
            )
            continue
        input_path = crate.file_at(source)
        if input_path is None:
            yield f"{name}: bridge:input names {source}, which is not a file in this package"
            continue
        xsd = schemas.lookup(schema_iri, declared_by)
        if xsd is None:
            continue
        if isinstance(xsd, str):
            yield f"{name}: {xsd}"
            continue
        try:
            document = etree.parse(str(input_path))
        except etree.Error as error:
            yield f"{name}: {input_path.name} is not well-formed XML\n{error}"
            continue
        if not xsd.validate(document):
            lines = "\n".join(f"line {entry.line}: {entry.message}" for entry in xsd.error_log)
            yield (
                f"{name}: {input_path.name} does not validate against "
                f"{file_name_of(schema_iri)}, the envelope's {declared_by}\n{lines}"
            )


@requirement(name="Inputs against the declared schema")
class Inputs(PyFunctionCheck):
    """Every committed input validates against the schema its envelope declares."""

    @check(name="every input validates against the declared schema")
    def run_check(self, context: ValidationContext) -> bool:
        return report_findings(self, context, invalid)
