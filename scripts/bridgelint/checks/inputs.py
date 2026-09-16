"""Check 5: every committed input validates against the declared schema.

XSD 1.0 by lxml: v1-draft specifies XML sources. A source schema declared JSON
is outside that and is reported as not run, because reporting it as a pass
would be a claim nobody made, and crashing on it would make the lint unusable
for a package it has nothing against.
"""

from __future__ import annotations

from ..crate import entity_name
from ..result import failed, not_run, nothing_to_check, passed
from ..terms import BRIDGE, JSON_SCHEMA_MEDIA_TYPES, MF, SCHEMA, XSD_MEDIA_TYPES

HEADING = "5. Inputs against the declared schema"
TITLE = "every input validates against the declared schema"


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


def run(crate):
    tests = [(test, crate.graph.value(test, MF.action)) for test in crate.entries]
    inputs = [
        (
            test,
            crate.graph.value(action, BRIDGE.input),
            crate.graph.value(action, BRIDGE.envelope),
        )
        for test, action in tests
        if action is not None and crate.graph.value(action, BRIDGE.input) is not None
    ]
    referenced = len(tests) - len(inputs)

    def add_referenced_note(result):
        if referenced:
            result.says(
                "note",
                f"{referenced} test(s) name a referenced dataset rather than a "
                "committed input; those bytes are not here, and the Bridge that "
                "streams them validates them",
            )
        return result

    if not inputs:
        return add_referenced_note(
            nothing_to_check("the test manifest names no committed input").verdict(
                True, "the test manifest names no committed input"
            )
        )

    try:
        from lxml import etree
    except ImportError:
        return not_run("lxml is not installed").verdict(
            False,
            "lxml is not installed (pip install lxml), so no input was validated",
        )

    compiled = {}
    unreadable = {}

    def schema_engine(schema_iri):
        """An lxml XMLSchema for this schema entity, or why there is none.

        `fatal` separates the two ways a schema can yield no engine, which are
        not the same finding. A schema this lint does not read -- one declared
        JSON, one referenced rather than committed -- is a gap in the lint, and
        the package is not accused of anything. A schema declared an XSD that
        will not compile as one is the package being wrong, and fails.
        """
        if schema_iri in compiled:
            return compiled[schema_iri], None, False
        if schema_iri in unreadable:
            return (None,) + unreadable[schema_iri]
        media_type = str(crate.graph.value(schema_iri, SCHEMA.encodingFormat) or "")
        path = crate.path_of(schema_iri)
        if path is None or not path.is_file():
            outcome = (
                f"{schema_iri} is not a file committed in this package, so "
                "there is nothing here to validate against",
                False,
            )
        elif media_type in JSON_SCHEMA_MEDIA_TYPES:
            outcome = (
                f"{path.name} is declared {media_type}: a JSON source schema "
                "is outside v1-draft, which specifies XML sources",
                False,
            )
        elif media_type not in XSD_MEDIA_TYPES:
            outcome = (
                f"{path.name} is declared {media_type or 'no media type'}, "
                "which names no schema language this lint reads",
                False,
            )
        else:
            try:
                compiled[schema_iri] = etree.XMLSchema(etree.parse(str(path)))
                return compiled[schema_iri], None, False
            except etree.Error as error:
                outcome = (
                    f"{path.name} is declared XML and does not compile as an "
                    f"XSD 1.0 schema: {error}",
                    True,
                )
        unreadable[schema_iri] = outcome
        return (None,) + outcome

    validated = 0
    failures = []
    skipped = []
    for test, input_iri, envelope in inputs:
        name = crate.name_of(test)
        schema_iri, source = schema_for(crate, envelope)
        if schema_iri is None:
            failures.append(
                (
                    f"{name}: its envelope declares no bridge:documentSchema "
                    "and the adapter declares no bridge:sourceSchema, so there "
                    "is nothing to validate the input against",
                    (),
                )
            )
            continue
        input_path = crate.file_at(input_iri)
        if input_path is None:
            failures.append(
                (
                    f"{name}: bridge:input names {input_iri}, which is not a "
                    "file in this package",
                    (),
                )
            )
            continue
        engine, reason, fatal = schema_engine(schema_iri)
        if engine is None:
            if fatal:
                failures.append((f"{name}: {reason}", ()))
            else:
                skipped.append((name, reason))
            continue
        try:
            document = etree.parse(str(input_path))
        except etree.Error as error:
            failures.append(
                (f"{name}: {input_path.name} is not well-formed XML", (str(error),))
            )
            continue
        if engine.validate(document):
            validated += 1
        else:
            failures.append(
                (
                    f"{name}: {input_path.name} does not validate against "
                    f"{entity_name(schema_iri)}, the envelope's {source}",
                    tuple(
                        f"line {entry.line}: {entry.message}"
                        for entry in engine.error_log
                    ),
                )
            )

    if failures:
        result = failed(f"{len(failures)} input(s) did not validate")
    elif skipped and not validated:
        result = not_run(
            f"no input was validated; {len(skipped)} outside what this lint reads",
            benign=True,
        )
    elif skipped:
        result = passed(
            f"{validated} validated, {len(skipped)} outside what this lint reads"
        )
    else:
        result = passed(f"{validated} input(s) validated")

    if not failures and not skipped:
        result.verdict(
            True,
            f"{validated} committed input(s) against the schema each test's "
            "envelope declares",
        )
    for text, detail in failures:
        result.verdict(False, text, *detail)
    for name, reason in skipped:
        result.says("note", f"{name}: not validated -- {reason}")
    return add_referenced_note(result)
