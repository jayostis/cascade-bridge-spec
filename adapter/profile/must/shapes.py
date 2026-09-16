import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _held import held
from _terms import SHAPES
from pyshacl import validate as shacl_validate
from rdflib import Graph
from rdflib.namespace import RDF, SH
from rocrate_validator.models import ValidationContext
from rocrate_validator.requirements.python import PyFunctionCheck, check, requirement


def violations(crate):
    _, report, _ = shacl_validate(
        crate.graph,
        shacl_graph=Graph().parse(SHAPES, format="turtle"),
        advanced=True,
        inplace=False,
    )
    for found in report.subjects(RDF.type, SH.ValidationResult):
        path = report.value(found, SH.resultPath)
        message = str(report.value(found, SH.resultMessage) or "").strip()
        yield f"{path or '-'}: {message}"


@requirement(name="Cascade Bridge shapes")
class Shapes(PyFunctionCheck):
    """The crate and the test manifest, as one graph, conform to the shapes."""

    @check(name="the crate and the test manifest conform to the shapes")
    def run_check(self, context: ValidationContext) -> bool:
        return held(self, context, violations)
