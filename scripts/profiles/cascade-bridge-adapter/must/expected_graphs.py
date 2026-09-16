"""Every graph a test names as its expected result parses as Turtle.

Parsing, and nothing else. Whether an expected graph conforms to Cascade's
shapes is a question for a Bridge's validate stage, asked of the graph a mapping
actually produced; asking it here would report a fixture as wrong for recording
something Cascade has no term for yet, which is what the findings sidecar beside
it is for.

A manifest may name no expected graph at all, and that is not a fault: an
input-only test records what a Bridge produced and judges nothing.
"""

from bridgelint.crate import from_context
from bridgelint.terms import BRIDGE, MF
from rdflib import Graph
from rocrate_validator.models import ValidationContext
from rocrate_validator.requirements.python import PyFunctionCheck, check, requirement


def unparsable(crate):
    """Every expected graph that is not Turtle here, as a message each."""
    for test in crate.entries:
        result = crate.graph.value(test, MF.result)
        if result is None:
            continue
        turtle = crate.graph.value(result, BRIDGE.graph)
        if turtle is None:
            continue
        name = crate.name_of(test)
        path = crate.file_at(turtle)
        if path is None:
            yield (
                f"{name}: bridge:graph names {turtle}, which is not a file in "
                "this package"
            )
            continue
        try:
            Graph().parse(path, format="turtle", publicID=str(turtle))
        except Exception as error:  # rdflib raises several unrelated types
            yield f"{name}: {path.name} does not parse as Turtle\n{error}"


@requirement(name="Expected graphs")
class ExpectedGraphs(PyFunctionCheck):
    """Every graph a test names as its expected result parses as Turtle."""

    @check(name="every expected graph parses as Turtle")
    def run_check(self, context: ValidationContext) -> bool:
        found = False
        for message in unparsable(from_context(context)):
            context.result.add_issue(message, self)
            found = True
        return not found
