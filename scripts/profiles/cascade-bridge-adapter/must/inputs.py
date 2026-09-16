"""Every committed input validates against the schema its envelope declares.

XSD 1.0 by lxml: v1-draft specifies XML sources. Three outcomes are not faults
in the package and yield nothing: a test naming a dataset has no committed bytes
here, and the Bridge that streams them validates them; a schema referenced
rather than committed is not fetched; and a source schema declared JSON is
outside v1-draft, which is a gap in this lint rather than something the package
did wrong.

lxml being absent is a different matter. The requirement then has not been met
by anything, and saying so is the point: a lint that silently checks nothing is
worse than no lint.
"""

from bridgelint.crate import entity_name, from_context
from bridgelint.terms import BRIDGE, JSON_SCHEMA_MEDIA_TYPES, MF, SCHEMA, XSD_MEDIA_TYPES
from rocrate_validator.models import ValidationContext
from rocrate_validator.requirements.python import PyFunctionCheck, check, requirement


def schema_for(crate, envelope):
    """The schema an input arriving in this envelope is validated against.

    The envelope's own bridge:documentSchema where it declares one -- an
    envelope has one exactly when its document root is not the one the source
    schema declares -- and the adapter's bridge:sourceSchema where it does not.
    """
    document_schema = crate.graph.value(envelope, BRIDGE.documentSchema)
    if document_schema is not None:
        return document_schema, "bridge:documentSchema"
    return crate.graph.value(crate.root, BRIDGE.sourceSchema), "bridge:sourceSchema"


def committed_inputs(crate):
    """Each test that names committed bytes, with its input and its envelope."""
    for test in crate.entries:
        action = crate.graph.value(test, MF.action)
        if action is None:
            continue
        source = crate.graph.value(action, BRIDGE.input)
        if source is None:
            continue
        yield test, source, crate.graph.value(action, BRIDGE.envelope)


def invalid(crate):
    """Every input that does not satisfy its declared schema, as a message
    each, plus anything that stopped this being asked at all."""
    inputs = list(committed_inputs(crate))
    if not inputs:
        return

    try:
        from lxml import etree
    except ImportError:
        yield (
            "lxml is not installed (pip install lxml), so no input was "
            "validated against any schema and nothing here says they would be"
        )
        return

    compiled = {}
    unreadable = set()

    def engine_for(schema_iri):
        """An lxml XMLSchema, or None with a message when there is a fault, or
        None with nothing when this lint simply cannot read that schema."""
        if schema_iri in compiled:
            return compiled[schema_iri], None
        if schema_iri in unreadable:
            return None, None
        media_type = str(crate.graph.value(schema_iri, SCHEMA.encodingFormat) or "")
        path = crate.file_at(schema_iri)
        if path is None or media_type in JSON_SCHEMA_MEDIA_TYPES or (
            media_type not in XSD_MEDIA_TYPES
        ):
            unreadable.add(schema_iri)
            return None, None
        try:
            compiled[schema_iri] = etree.XMLSchema(etree.parse(str(path)))
        except etree.Error as error:
            unreadable.add(schema_iri)
            return None, (
                f"{path.name} is declared XML and does not compile as an XSD "
                f"1.0 schema: {error}"
            )
        return compiled[schema_iri], None

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
            yield (
                f"{name}: bridge:input names {source}, which is not a file in "
                "this package"
            )
            continue
        engine, fault = engine_for(schema_iri)
        if engine is None:
            if fault:
                yield f"{name}: {fault}"
            continue
        try:
            document = etree.parse(str(input_path))
        except etree.Error as error:
            yield f"{name}: {input_path.name} is not well-formed XML\n{error}"
            continue
        if not engine.validate(document):
            lines = "\n".join(
                f"line {entry.line}: {entry.message}" for entry in engine.error_log
            )
            yield (
                f"{name}: {input_path.name} does not validate against "
                f"{entity_name(schema_iri)}, the envelope's {declared_by}\n{lines}"
            )


@requirement(name="Inputs against the declared schema")
class Inputs(PyFunctionCheck):
    """Every committed input validates against the schema its envelope
    declares, or the adapter's source schema where the envelope declares
    none."""

    @check(name="every input validates against the declared schema")
    def run_check(self, context: ValidationContext) -> bool:
        found = False
        for message in invalid(from_context(context)):
            context.result.add_issue(message, self)
            found = True
        return not found
