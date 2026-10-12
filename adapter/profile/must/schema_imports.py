import sys
from pathlib import Path
from urllib.parse import urljoin

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rocrate_validator.models import ValidationContext
from rocrate_validator.requirements.python import PyFunctionCheck, check, requirement

from _findings import report_findings
from _json_source import syntax_of
from _terms import BRIDGE

XML_SCHEMA = "http://www.w3.org/2001/XMLSchema"
REFERENCES = tuple(f"{{{XML_SCHEMA}}}{directive}" for directive in ("include", "import", "redefine", "override"))


def bare(iri):
    return str(iri).partition("#")[0]


def named_schemas(crate):
    return {
        bare(schema)
        for predicate in (BRIDGE.sourceSchema, BRIDGE.documentSchema)
        for schema in crate.graph.objects(None, predicate)
    }


def reached_from(crate, etree, iri, reached):
    path = crate.file_at(iri)
    if path is None:
        return
    try:
        schema = etree.parse(str(path))
    except etree.Error:
        return
    for reference in schema.iter(*REFERENCES):
        location = reference.get("schemaLocation")
        if location is None:
            continue
        referred = urljoin(iri, location)
        if crate.file_at(referred) is not None and referred not in reached:
            reached.add(referred)
            reached_from(crate, etree, referred, reached)


def declarations(crate):
    for subject in (crate.root, *crate.graph.objects(crate.root, BRIDGE.envelope)):
        for iri in crate.graph.objects(subject, BRIDGE.schemaImport):
            yield bare(iri)


def relative(crate, iri):
    return str(iri)[len(crate.adapter.resolve().as_uri().rstrip("/")) + 1 :]


def undeclared(crate):
    if syntax_of(crate) != "xml":
        return
    from lxml import etree

    named = named_schemas(crate)
    reached = set()
    for iri in named:
        reached_from(crate, etree, iri, reached)
    reached -= named
    declared = set(declarations(crate))
    for iri in sorted(reached - declared):
        yield (
            f"{relative(crate, iri)} is included or imported by a schema of the adapter and no bridge:schemaImport "
            "of the root entity or an envelope names it, so a host listing the files to load does not give it up front."
        )
    for iri in sorted(declared - reached):
        yield f"bridge:schemaImport names {relative(crate, iri)}, which no schema of the adapter includes or imports."


@requirement(name="Schema imports")
class SchemaImports(PyFunctionCheck):
    """The files a named schema includes or imports, directly or through another schema, are the root entity's and the envelopes' bridge:schemaImport values."""

    @check(name="every schema file a named schema reaches is declared, and every declaration is reached")
    def run_check(self, context: ValidationContext) -> bool:
        return report_findings(self, context, undeclared)
