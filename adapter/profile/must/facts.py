import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rdflib import Graph
from rocrate_validator.models import ValidationContext
from rocrate_validator.requirements.python import PyFunctionCheck, check, requirement

from _findings import report_findings, unmet
from _terms import BRIDGE, MF

SHAPES = Path(__file__).resolve().parents[3] / "shapes" / "facts.shapes.ttl"


def named_facts(crate):
    for test in crate.entries:
        action = crate.graph.value(test, MF.action)
        if action is None:
            continue
        for conversion in [action, *crate.graph.objects(action, BRIDGE.conversion)]:
            for facts in crate.graph.objects(conversion, BRIDGE.facts):
                yield crate.name_of(test), facts


def faulty(crate):
    shapes = Graph().parse(SHAPES, format="turtle")
    read = set()
    for name, facts in named_facts(crate):
        path = crate.file_at(facts)
        if path is None:
            yield f"{name}: bridge:facts names {facts}, which is not a file in this package"
            continue
        if path in read:
            continue
        read.add(path)
        graph = Graph()
        try:
            graph.parse(path, format="turtle")
        except Exception as error:
            yield f"{name}: {path.name} does not parse as Turtle\n{error}"
            continue
        for message in unmet(graph, shapes):
            yield f"{path.name}: {message}"


@requirement(name="Supplied facts")
class SuppliedFacts(PyFunctionCheck):
    """Every file of facts a test supplies with its input is a Turtle file of the facts a Bridge reads."""

    @check(name="every file of supplied facts is one a Bridge reads")
    def run_check(self, context: ValidationContext) -> bool:
        return report_findings(self, context, faulty)
