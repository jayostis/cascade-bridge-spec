from pathlib import Path

from pyshacl import validate as shacl_validate
from rdflib.namespace import SH

from _crate import from_context

SHAPES = Path(__file__).resolve().parents[2] / "shapes" / "bridge.shapes.ttl"


def unmet(graph, shapes, standing_for=frozenset()):
    """Each shape the graph does not meet, said as narrowly as the report allows.

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
            yield from said_by(found)


def report_findings(check, context, find):
    try:
        messages = list(find(from_context(context)))
    except Exception as error:
        messages = [f"could not be checked: {error}"]
    for message in messages:
        context.result.add_issue(message, check)
    return not messages
