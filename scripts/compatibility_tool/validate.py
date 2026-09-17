import json

from pyshacl import validate as shacl_validate
from rdflib import Graph
from rdflib.namespace import RDF, SH

from compatibility_tool.console import Status, detail, note, report
from compatibility_tool.document import (
    CONTEXT_IRI,
    CRATE,
    FILE,
    SPEC_ROOT,
    form_problem,
    is_adapter,
    name_clashes,
    problems_json_ld_hides_from_shacl,
    read_file,
)

SHAPES = SPEC_ROOT / "shapes" / "bridge.shapes.ttl"
CONTEXT_FILE = SPEC_ROOT / "vocab" / "compatibility.context.jsonld"


def shape_violations(directory, document):
    context = json.loads(CONTEXT_FILE.read_text(encoding="utf-8"))["@context"]
    data = dict(document, **{"@context": context})
    graph = Graph().parse(data=json.dumps(data), format="json-ld", base=(directory / FILE).resolve().as_uri())
    conforms, results, _ = shacl_validate(
        graph, shacl_graph=Graph().parse(SHAPES, format="turtle"), advanced=True, inplace=False
    )
    if conforms:
        return []
    return sorted(
        {
            str(results.value(result, SH.resultMessage) or "").strip()
            for result in results.subjects(RDF.type, SH.ValidationResult)
        }
    )


def validate_command(directory, options):
    kind = "an adapter" if is_adapter(directory) else "an engine"
    print(f"{FILE}, in {kind}'s form")
    document = read_file(directory)
    if document is None:
        if is_adapter(directory):
            report(True, f"{directory} has no {FILE}: nothing to check")
            return Status.NOTHING_TO_CHECK
        report(
            False,
            f"{directory} holds no {CRATE}, so it is an engine, and an engine "
            f"states its spec pin in {FILE}, which is not there",
        )
        return Status.FAIL
    if not isinstance(document, dict) or document.get("@context") != CONTEXT_IRI:
        found = document.get("@context") if isinstance(document, dict) else document
        report(False, f"its @context is {found!r}, where a {FILE} names {CONTEXT_IRI}")
        return Status.FAIL

    problems = problems_json_ld_hides_from_shacl(document) + name_clashes(directory, document)
    for problem in problems:
        report(False, problem)

    violations = shape_violations(directory, document)
    if violations:
        report(False, f"{len(violations)} shape violation(s)")
        for message in violations:
            detail(message)
        return Status.FAIL
    report(True, f"{SHAPES.name} against {FILE}")

    form = form_problem(directory, document)
    if form:
        report(False, form)
        return Status.FAIL
    report(True, f"the form is {kind}'s, as the directory is")
    if problems:
        return Status.FAIL

    listed = document.get("mustPassWith")
    count = len(listed) if isinstance(listed, list) else 0
    note(f"{count} mustPassWith entr{'y' if count == 1 else 'ies'}")
    return Status.OK
