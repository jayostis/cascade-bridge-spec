import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rdflib import Graph
from rocrate_validator.models import ValidationContext
from rocrate_validator.requirements.python import PyFunctionCheck, check, requirement

from _findings import report_findings
from _terms import BRIDGE

VOCABULARY = Path(__file__).resolve().parents[3] / "vocab" / "bridge.ttl"


def declared():
    graph = Graph().parse(VOCABULARY, format="turtle")
    return {str(term) for term in graph.subjects() if str(term).startswith(str(BRIDGE))}


def undeclared(crate):
    known = declared()
    carried = {
        str(term)
        for triple in crate.graph
        for term in triple
        if str(term).startswith(str(BRIDGE)) and str(term) not in known
    }
    for term in sorted(carried):
        yield (
            f"{term.replace(str(BRIDGE), 'bridge:')} is not a term the Cascade Bridge vocabulary declares: "
            "a value with no Cascade term goes in the namespace the adapter names as its bridge:extensionVocabulary."
        )


@requirement(name="Declared terms")
class DeclaredTerms(PyFunctionCheck):
    """Every bridge: term the crate and the test manifest carry is one the vocabulary declares."""

    @check(name="every bridge: term is declared")
    def run_check(self, context: ValidationContext) -> bool:
        return report_findings(self, context, undeclared)
