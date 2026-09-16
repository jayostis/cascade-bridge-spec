"""The crate and its test manifest, as one graph, conform to the Cascade Bridge
shapes.

What the shapes require is shapes/bridge.shapes.ttl and nowhere else. The two
files are one graph, each parsed with its own location as base, which is what
makes the manifest's <../> the crate's root entity: load either with the wrong
base and every link between them silently becomes two unrelated nodes, and the
shapes report nothing rather than reporting a mistake.
"""

from bridgelint.crate import from_context
from bridgelint.terms import SHAPES
from pyshacl import validate as shacl_validate
from rdflib import Graph
from rdflib.namespace import RDF, SH
from rocrate_validator.models import ValidationContext
from rocrate_validator.requirements.python import PyFunctionCheck, check, requirement


def violations(crate):
    """Every shape violation, as a message each. Warnings are not violations
    and are not yielded."""
    _, report, _ = shacl_validate(
        crate.graph,
        shacl_graph=Graph().parse(SHAPES, format="turtle"),
        advanced=True,          # the shapes use sh:sparql constraints
        allow_warnings=True,
        inplace=False,
    )
    for found in report.subjects(RDF.type, SH.ValidationResult):
        if report.value(found, SH.resultSeverity) != SH.Violation:
            continue
        path = report.value(found, SH.resultPath)
        message = str(report.value(found, SH.resultMessage) or "").strip()
        yield f"{path or '-'}: {message}"


@requirement(name="Cascade Bridge shapes")
class Shapes(PyFunctionCheck):
    """The crate and the test manifest, loaded as one graph with their own base
    IRIs, conform to shapes/bridge.shapes.ttl."""

    @check(name="the crate and the test manifest conform to the shapes")
    def run_check(self, context: ValidationContext) -> bool:
        found = False
        for message in violations(from_context(context)):
            context.result.add_issue(message, self)
            found = True
        return not found
