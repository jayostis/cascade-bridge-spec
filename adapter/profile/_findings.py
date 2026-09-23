from pathlib import Path

from pyshacl import validate as shacl_validate
from rdflib import BNode
from rdflib.namespace import SH

from _crate import from_context
from _terms import BRIDGE

SHAPES = Path(__file__).resolve().parents[2] / "shapes" / "bridge.shapes.ttl"


def named(node, graph):
    """How a reader finds the node in the file: its IRI, an entry's bridge:sourcePath, or what a blank node states."""
    if not isinstance(node, BNode):
        return str(node)
    paths = list(graph.objects(node, BRIDGE.sourcePath))
    if len(paths) == 1:
        return str(paths[0])
    stated = sorted(
        f"{predicate.n3(graph.namespace_manager)} {value.n3(graph.namespace_manager)}"
        for predicate, value in graph.predicate_objects(node)
        if not isinstance(value, BNode)
    )
    return f"[ {' ; '.join(stated)} ]"


def unmet(graph, shapes, standing_for=frozenset()):
    """Each shape the graph does not meet, said as narrowly as the report allows, after the node that broke it.

    A node standing for a variable binds whatever the query binds it to, so what a shape says
    about its value is not this lint's to judge, and neither is a result whose every detail is.
    """
    _, report, _ = shacl_validate(graph, shacl_graph=shapes, advanced=True, inplace=False)

    def about_a_binding(result):
        if report.value(result, SH.value) in standing_for:
            return True
        details = list(report.objects(result, SH.detail))
        return bool(details) and all(about_a_binding(detail) for detail in details)

    def said_by(result):
        narrower = [detail for detail in report.objects(result, SH.detail) if not about_a_binding(detail)]
        if not narrower:
            yield str(report.value(result, SH.resultMessage) or "").strip()
        for detail in narrower:
            yield from said_by(detail)

    for found in report.objects(None, SH.result):
        if not about_a_binding(found):
            node = named(report.value(found, SH.focusNode), graph)
            for message in said_by(found):
                yield f"{node}: {message}"


def report_findings(check, context, find):
    try:
        messages = list(find(from_context(context)))
    except Exception as error:
        messages = [f"could not be checked: {error}"]
    for message in messages:
        context.result.add_issue(message, check)
    return not messages
