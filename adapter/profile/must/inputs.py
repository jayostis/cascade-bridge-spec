import json
import sys
from pathlib import Path
from urllib.parse import urljoin, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rocrate_validator.models import ValidationContext
from rocrate_validator.requirements.python import PyFunctionCheck, check, requirement

from _crate import file_name_of, path_of
from _findings import report_findings
from _json_source import NotJson, a_number_as_validated, parsed, pointer_of, syntax_of, validated_value
from _json_source import records_of as json_records_of
from _selectors import expected_findings_file_of, json_nodes_recorded_on, violations_recorded_on
from _terms import BRIDGE, MF, SCHEMA

XSD_MEDIA_TYPES = {"application/xml", "text/xml"}
JSON_SCHEMA_MEDIA_TYPES = {"application/json", "application/schema+json"}
DOCUMENT_SCHEMA = "the envelope's bridge:documentSchema"
SOURCE_SCHEMA = "the adapter's bridge:sourceSchema"
XML_SCHEMA = "http://www.w3.org/2001/XMLSchema"
JSON_SCHEMA_DRAFT_06 = {"http://json-schema.org/draft-06/schema#", "http://json-schema.org/draft-06/schema"}
W3C_SCHEMAS = Path(__file__).resolve().parents[1] / "w3c"
SUPPLIED_BY_THE_BRIDGE = {
    "http://www.w3.org/XML/1998/namespace": W3C_SCHEMAS / "xml.xsd",
    "http://www.w3.org/1999/xlink": W3C_SCHEMAS / "xlink.xsd",
}


def records_of(document, element_name):
    return document.xpath("//*[local-name()=$name]", name=element_name)


def committed_inputs(crate):
    for test in crate.entries:
        action = crate.graph.value(test, MF.action)
        if action is None:
            continue
        for conversion in [action, *crate.graph.objects(action, BRIDGE.conversion)]:
            source = crate.graph.value(conversion, BRIDGE.input)
            if source is not None:
                yield test, source, crate.graph.value(conversion, BRIDGE.envelope)


def local_file(url):
    scheme = urlparse(url).scheme
    if scheme == "file":
        return path_of(url).resolve()
    if len(scheme) <= 1:
        return Path(url).resolve()
    return None


def resolving_in(etree, package, refused):
    def in_package(path):
        return path is not None and path.is_file() and path.is_relative_to(package)

    class InPackage(etree.Resolver):
        def resolve(self, url, public_id, context):
            path = local_file(url)
            if not (in_package(path) or path in SUPPLIED_BY_THE_BRIDGE.values()):
                refused.append(url)
                return self.resolve_string("<refused/>", context)
            document = etree.parse(str(path))
            for imported in document.iter(f"{{{XML_SCHEMA}}}import"):
                supplied = SUPPLIED_BY_THE_BRIDGE.get(imported.get("namespace"))
                location = imported.get("schemaLocation")
                shipped = None if location is None else local_file(urljoin(path.as_uri(), location))
                if supplied is not None and not in_package(shipped):
                    imported.set("schemaLocation", supplied.as_uri())
            return self.resolve_string(etree.tostring(document), context, base_url=path.as_uri())

    return InPackage()


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
        path = self.crate.file_at(schema_iri)
        if path is None:
            return f"{declared_by} names {schema_iri}, which is not a file in this package"
        if declared is None:
            return (
                f"{path.name} declares no encodingFormat, so this lint cannot "
                "tell which schema language to validate against"
            )
        if media_type in JSON_SCHEMA_MEDIA_TYPES:
            return (
                f"{path.name} is declared {media_type}, a JSON Schema, where an XML source is validated "
                "against an XSD 1.0 schema declared application/xml or text/xml"
            )
        if media_type not in XSD_MEDIA_TYPES:
            return f"{path.name} is declared {media_type}, which this lint cannot validate against"
        refused = []
        parser = self.etree.XMLParser(no_network=True)
        parser.resolvers.add(resolving_in(self.etree, self.crate.adapter.resolve(), refused))
        try:
            compiled = self.etree.XMLSchema(self.etree.parse(str(path), parser))
        except self.etree.Error as error:
            compiled = f"{path.name} is declared XML and does not compile as an XSD 1.0 schema: {error}"
        if refused:
            return "\n".join(f"{path.name} names {url}, which is not a file in this package" for url in refused)
        return compiled


def measured_against(xsd, schema_iri, declared_by, nodes, name, recorded):
    """A failure the entry's expected findings record as a violation of that node is the adapter's, not a fault."""
    for what, addressed, node in nodes:
        if xsd.validate(node) or addressed in recorded:
            continue
        lines = "\n".join(f"line {entry.line}: {entry.message}" for entry in xsd.error_log)
        yield (f"{name}: {what} does not validate against {file_name_of(schema_iri)}, {declared_by}\n{lines}")


class JsonSchemas:
    """Each lookup is a draft-06 validator or a fault to report."""

    def __init__(self, crate):
        self.crate = crate
        self.looked_up = {}

    def lookup(self, schema_iri, declared_by):
        key = (schema_iri, declared_by)
        if key not in self.looked_up:
            self.looked_up[key] = self.compile(schema_iri, declared_by)
        return self.looked_up[key]

    def compile(self, schema_iri, declared_by):
        from jsonschema import Draft6Validator
        from jsonschema.exceptions import SchemaError
        from referencing import Registry, Resource
        from referencing.jsonschema import DRAFT6

        path = self.crate.file_at(schema_iri)
        if path is None:
            return f"{declared_by} names {schema_iri}, which is not a file in this package"
        media_type = str(self.crate.graph.value(schema_iri, SCHEMA.encodingFormat) or "")
        if media_type not in JSON_SCHEMA_MEDIA_TYPES:
            return (
                f"{path.name} is declared {media_type or 'in no encodingFormat'}, where a JSON source is validated "
                f"against a JSON Schema declared {' or '.join(sorted(JSON_SCHEMA_MEDIA_TYPES))}"
            )
        try:
            schema = json.loads(path.read_text(encoding="utf-8"), parse_float=a_number_as_validated)
        except ValueError as error:
            return f"{path.name} does not parse as JSON: {error}"
        if not isinstance(schema, dict) or schema.get("$schema") not in JSON_SCHEMA_DRAFT_06:
            return (
                f"{path.name} names no JSON Schema draft-06 as its $schema, http://json-schema.org/draft-06/schema#, "
                "the one draft a Bridge validates against"
            )
        try:
            Draft6Validator.check_schema(schema)
        except SchemaError as error:
            return f"{path.name} is not a draft-06 JSON Schema: {error.message}"
        package = self.crate.adapter.resolve()

        def retrieve(uri):
            named = local_file(uri) if uri.startswith("file:") else None
            if named is None or not named.is_file() or not named.is_relative_to(package):
                raise LookupError(f"{uri} is not a file in this package")
            return Resource.from_contents(
                json.loads(named.read_text(encoding="utf-8"), parse_float=a_number_as_validated),
                default_specification=DRAFT6,
            )

        registry = Registry(retrieve=retrieve).with_resource(
            path.as_uri(), Resource.from_contents(schema, default_specification=DRAFT6)
        )
        return Draft6Validator({"$ref": path.as_uri()}, registry=registry)


def json_failures(validator, schema_iri, declared_by, nodes, name, recorded):
    """A failure the entry's expected findings record as a violation of that node is the adapter's, not a fault."""
    from referencing.exceptions import Unresolvable

    for what, tokens, node in nodes:
        try:
            failures = [
                failure
                for failure in validator.iter_errors(node)
                if tokens + tuple(str(step) for step in failure.absolute_path) not in recorded
            ]
        except Unresolvable as error:
            yield f"{name}: {file_name_of(schema_iri)} names {error.ref}, which is not a file in this package"
            return
        if failures:
            lines = "\n".join(
                f"{pointer_of(tokens + tuple(str(step) for step in failure.absolute_path)) or '(the value)'}: "
                f"{failure.message}"
                for failure in failures
            )
            yield f"{name}: {what} does not validate against {file_name_of(schema_iri)}, {declared_by}\n{lines}"


def invalid_json(crate, inputs):
    schemas = JsonSchemas(crate)
    source_schema = crate.graph.value(crate.root, BRIDGE.sourceSchema)
    for test, source, envelope in inputs:
        name = crate.name_of(test)
        document_schema = crate.graph.value(envelope, BRIDGE.documentSchema)
        input_path = crate.file_at(source)
        if input_path is None:
            yield f"{name}: bridge:input names {source}, which is not a file in this package"
            continue
        data = input_path.read_bytes()
        try:
            written = parsed(data)
        except NotJson as error:
            yield f"{name}: {input_path.name} is not a JSON text in UTF-8: {error}"
            continue
        if not isinstance(written, list):
            yield f"{name}: {input_path.name} holds neither an object nor an array, so the JSON lift lifts nothing of it"
            continue
        against_document = None if document_schema is None else schemas.lookup(document_schema, DOCUMENT_SCHEMA)
        against_records = None if source_schema is None else schemas.lookup(source_schema, SOURCE_SCHEMA)
        for fault in (against_document, against_records):
            if isinstance(fault, str):
                yield f"{name}: {fault}"
        findings_file = expected_findings_file_of(crate, test)
        recorded = set() if findings_file is None else json_nodes_recorded_on(findings_file, written)
        value = validated_value(data)
        if against_document is not None and not isinstance(against_document, str):
            yield from json_failures(
                against_document, document_schema, DOCUMENT_SCHEMA, [(input_path.name, (), value)], name, recorded
            )
        record_path = crate.graph.value(envelope, BRIDGE.jsonPathOfEachRecord)
        if against_records is None or isinstance(against_records, str) or record_path is None:
            continue
        try:
            records = json_records_of(value, str(record_path))
        except ValueError:
            continue
        if not records:
            yield (
                f"{name}: {input_path.name} holds no record at {record_path}, "
                "its envelope's bridge:jsonPathOfEachRecord"
            )
        yield from json_failures(
            against_records,
            source_schema,
            SOURCE_SCHEMA,
            [
                (f"{pointer_of(tokens) or 'the value'} of {input_path.name}", tokens, record)
                for tokens, record in records
            ],
            name,
            recorded,
        )


def invalid(crate):
    inputs = list(committed_inputs(crate))
    if not inputs:
        return
    if syntax_of(crate) == "json":
        yield from invalid_json(crate, inputs)
        return

    try:
        from lxml import etree
    except ImportError:
        yield "lxml is not installed (pip install lxml), so no input was validated"
        return

    schemas = XsdSchemas(crate, etree)
    source_schema = crate.graph.value(crate.root, BRIDGE.sourceSchema)
    record_name = str(crate.graph.value(crate.root, BRIDGE.elementNameOfEachRecord) or "")
    for test, source, envelope in inputs:
        name = crate.name_of(test)
        document_schema = crate.graph.value(envelope, BRIDGE.documentSchema)
        if document_schema is None and source_schema is None:
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
        against_document = None if document_schema is None else schemas.lookup(document_schema, DOCUMENT_SCHEMA)
        against_records = None if source_schema is None else schemas.lookup(source_schema, SOURCE_SCHEMA)
        for fault in (against_document, against_records):
            if isinstance(fault, str):
                yield f"{name}: {fault}"
        if not any(isinstance(xsd, etree.XMLSchema) for xsd in (against_document, against_records)):
            continue
        try:
            document = etree.parse(str(input_path))
        except etree.Error as error:
            yield f"{name}: {input_path.name} is not well-formed XML\n{error}"
            continue
        findings_file = expected_findings_file_of(crate, test)
        recorded = set() if findings_file is None else violations_recorded_on(findings_file, document)
        if isinstance(against_document, etree.XMLSchema):
            yield from measured_against(
                against_document,
                document_schema,
                DOCUMENT_SCHEMA,
                [(input_path.name, document.getroot(), document)],
                name,
                recorded,
            )
        if not isinstance(against_records, etree.XMLSchema):
            continue
        if not record_name:
            yield (
                f"{name}: the adapter declares bridge:sourceSchema and no "
                f"bridge:elementNameOfEachRecord, so no record of {input_path.name} "
                "was validated against it"
            )
            continue
        records = records_of(document, record_name)
        if not records:
            yield (f"{name}: {input_path.name} holds no {record_name}, the adapter's bridge:elementNameOfEachRecord")
        yield from measured_against(
            against_records,
            source_schema,
            SOURCE_SCHEMA,
            [(f"{document.getpath(record)} of {input_path.name}", record, record) for record in records],
            name,
            recorded,
        )


@requirement(name="Inputs against the declared schemas")
class Inputs(PyFunctionCheck):
    """Every committed input validates whole against its envelope's document schema, and record by record against the source schema, except where the entry's expected findings record the failure."""

    @check(name="every input and every record in it validates against the declared schema")
    def run_check(self, context: ValidationContext) -> bool:
        return report_findings(self, context, invalid)
