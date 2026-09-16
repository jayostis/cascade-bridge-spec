import sys
from pathlib import Path

# The validator imports this file by path, without its directory on sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _held import held
from _terms import BRIDGE, MF
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
        return held(self, context, unparsable)
