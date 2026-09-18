import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rdflib.plugins.sparql import prepareQuery
from rocrate_validator.models import ValidationContext
from rocrate_validator.requirements.python import PyFunctionCheck, check, requirement

from _crate import file_name_of
from _findings import report_findings
from _terms import BRIDGE

QUERY_FORMS = {
    BRIDGE.mapping: ("bridge:mapping", "CONSTRUCT"),
    BRIDGE.findingsQuery: ("bridge:findingsQuery", "CONSTRUCT"),
    BRIDGE.detectQuery: ("bridge:detectQuery", "ASK"),
}
SUPERSEDED_SELECT_FINDING_VARIABLES = ("sourceField", "reason", "severity", "context")


def superseded_select(name, parsed):
    projected = [str(variable) for variable in parsed.algebra["PV"]]
    if sorted(projected) != sorted(SUPERSEDED_SELECT_FINDING_VARIABLES):
        listed = " ".join("?" + variable for variable in projected)
        yield (
            f"{name} projects {listed}, where the superseded SELECT form of a "
            "findings query projects ?sourceField ?reason ?severity ?context, "
            "in any order and no other variable"
        )


def constructs(parsed):
    return {term for triple in parsed.algebra.get("template") or () for term in triple}


def malformed(crate):
    named = [(prop, query) for prop in QUERY_FORMS for query in sorted(crate.graph.objects(crate.root, prop))]
    for prop, query in named:
        term, form = QUERY_FORMS[prop]
        name = file_name_of(query)
        path = crate.file_at(query)
        if path is None:
            yield f"{term} names {query}, which is not a file in this package"
            continue
        try:
            parsed = prepareQuery(path.read_text(encoding="utf-8"))
        except Exception as error:
            yield f"{name} does not parse as SPARQL 1.1\n{error}"
            continue
        found = parsed.algebra.name.removesuffix("Query").upper()
        if prop == BRIDGE.findingsQuery and found == "SELECT":
            yield from superseded_select(name, parsed)
            continue
        if found != form:
            yield f"{name} is a {found} query, where {term} requires {form}"
            continue
        if prop == BRIDGE.findingsQuery and BRIDGE.thisRecord not in constructs(parsed):
            yield f"{name} constructs no bridge:thisRecord, the record each finding it produces is about"


@requirement(name="Queries")
class Queries(PyFunctionCheck):
    """Every query parses as SPARQL 1.1, in the form the property naming it declares."""

    @check(name="every query parses in its declared form")
    def run_check(self, context: ValidationContext) -> bool:
        return report_findings(self, context, malformed)
