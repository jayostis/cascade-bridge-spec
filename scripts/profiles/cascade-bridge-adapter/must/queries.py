from bridgelint.requirement import held
from bridgelint.crate import entity_name, from_context
from bridgelint.terms import BRIDGE
from rdflib.plugins.sparql import prepareQuery
from rocrate_validator.models import ValidationContext
from rocrate_validator.requirements.python import PyFunctionCheck, check, requirement

QUERY_FORMS = {
    BRIDGE.mapping: ("bridge:mapping", "CONSTRUCT"),
    BRIDGE.findingsQuery: ("bridge:findingsQuery", "SELECT"),
    BRIDGE.detectQuery: ("bridge:detectQuery", "ASK"),
}
FINDING_VARIABLES = ("sourceField", "reason", "severity", "context")


def malformed(crate):
    """Every query that does not parse, or is not the form its property
    declares, as a message each."""
    named = [
        (prop, query)
        for prop in QUERY_FORMS
        for query in sorted(crate.graph.objects(crate.root, prop))
    ]
    for prop, query in named:
        term, form = QUERY_FORMS[prop]
        name = entity_name(query)
        path = crate.file_at(query)
        if path is None:
            yield f"{term} names {query}, which is not a file in this package"
            continue
        try:
            parsed = prepareQuery(path.read_text(encoding="utf-8"))
        except Exception as error:  # the parser raises several unrelated types
            yield f"{name} does not parse as SPARQL 1.1\n{error}"
            continue
        found = parsed.algebra.name.removesuffix("Query").upper()
        if found != form:
            yield f"{name} is a {found} query, where {term} requires {form}"
            continue
        if prop == BRIDGE.findingsQuery:
            projected = [str(variable) for variable in parsed.algebra["PV"]]
            # Sorted rather than a set: rdflib keeps a variable projected twice,
            # and a set would pass it as the four.
            if sorted(projected) != sorted(FINDING_VARIABLES):
                listed = " ".join("?" + v for v in projected)
                yield (
                    f"{name} projects {listed}, where a findings query projects "
                    "?sourceField ?reason ?severity ?context, in any order and "
                    "no other variable"
                )


@requirement(name="Queries")
class Queries(PyFunctionCheck):
    """Every query parses as SPARQL 1.1, in the form the property naming it declares."""

    @check(name="every query parses in its declared form")
    def run_check(self, context: ValidationContext) -> bool:
        return held(self, context, malformed(from_context(context)))
