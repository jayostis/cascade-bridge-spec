import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rdflib import BNode
from rdflib.plugins.sparql import prepareQuery
from rocrate_validator.models import ValidationContext
from rocrate_validator.requirements.python import PyFunctionCheck, check, requirement

from _crate import file_name_of
from _findings import report_findings
from _terms import BRIDGE, OA

QUERY_FORMS = {
    BRIDGE.mapping: ("bridge:mapping", "CONSTRUCT"),
    BRIDGE.findingsQuery: ("bridge:findingsQuery", "CONSTRUCT"),
    BRIDGE.detectQuery: ("bridge:detectQuery", "ASK"),
}


def constructed(parsed, predicate):
    return {triple[2] for triple in parsed.algebra.get("template") or () if triple[1] == predicate}


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
        if found != form:
            yield f"{name} is a {found} query, where {term} requires {form}"
            continue
        if prop != BRIDGE.findingsQuery:
            continue
        if BRIDGE.thisRecord not in constructed(parsed, OA.hasSource):
            yield (
                f"{name} constructs no oa:hasSource bridge:thisRecord, "
                "the document each finding it produces is read from"
            )
        named = sorted(term for term in constructed(parsed, OA.hasTarget) if not isinstance(term, BNode))
        if named:
            yield (
                f"{name} targets {', '.join(term.n3() for term in named)}, where a finding's oa:hasTarget "
                "is a blank node: one name is one node for every finding the query produces, and which "
                "selector on it belongs to which finding is then unrecoverable"
            )


@requirement(name="Queries")
class Queries(PyFunctionCheck):
    """Every query parses as SPARQL 1.1, in the form the property naming it declares."""

    @check(name="every query parses in its declared form")
    def run_check(self, context: ValidationContext) -> bool:
        return report_findings(self, context, malformed)
