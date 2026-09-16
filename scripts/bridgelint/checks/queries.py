"""Check 7: every query the adapter names parses, in its declared form.

Parsing, not running: whether a mapping produces its expected graph is the test
manifest's question, and it needs a Bridge.
"""

from __future__ import annotations

from rdflib.plugins.sparql import prepareQuery

from ..crate import entity_name
from ..result import failed, nothing_to_check, passed
from ..terms import BRIDGE

HEADING = "7. Queries"
TITLE = "every query parses in its declared form"

QUERY_FORMS = {
    BRIDGE.mapping: ("bridge:mapping", "CONSTRUCT"),
    BRIDGE.findingsQuery: ("bridge:findingsQuery", "SELECT"),
    BRIDGE.detectQuery: ("bridge:detectQuery", "ASK"),
}
FINDING_VARIABLES = ("sourceField", "reason", "severity", "context")


def run(crate):
    named = [
        (prop, query)
        for prop in QUERY_FORMS
        for query in sorted(crate.graph.objects(crate.root, prop))
    ]
    if not named:
        return nothing_to_check("the adapter names no query").verdict(
            True, "the adapter names no query"
        )

    failures = []
    for prop, query in named:
        term, form = QUERY_FORMS[prop]
        name = entity_name(query)
        path = crate.file_at(query)
        if path is None:
            failures.append(
                (f"{term} names {query}, which is not a file in this package", ())
            )
            continue
        try:
            parsed = prepareQuery(path.read_text(encoding="utf-8"))
        except Exception as error:  # the parser raises several unrelated types
            failures.append(
                (f"{name} does not parse as SPARQL 1.1", (str(error),))
            )
            continue
        found = parsed.algebra.name.removesuffix("Query").upper()
        if found != form:
            failures.append(
                (f"{name} is a {found} query, where {term} requires {form}", ())
            )
            continue
        if prop == BRIDGE.findingsQuery:
            projected = [str(variable) for variable in parsed.algebra["PV"]]
            # Sorted rather than a set: rdflib keeps a variable projected twice,
            # and a set would pass it as the four.
            if sorted(projected) != sorted(FINDING_VARIABLES):
                listed = " ".join("?" + v for v in projected)
                failures.append(
                    (
                        f"{name} projects {listed}, where a findings query "
                        "projects ?sourceField ?reason ?severity ?context, in "
                        "any order and no other variable",
                        (),
                    )
                )

    note = f"{len(named) - len(failures)} of {len(named)} in their declared form"
    result = (passed if not failures else failed)(note)
    if not failures:
        result.verdict(
            True,
            f"{len(named)} query file(s) parse as SPARQL 1.1, each in the form "
            "its property declares",
        )
    for text, detail in failures:
        result.verdict(False, text, *detail)
    return result
