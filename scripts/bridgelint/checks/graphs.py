"""Check 6: every expected graph parses as Turtle.

Parsing, and nothing else. Whether an expected graph conforms to Cascade's
shapes is a question for a Bridge's validate stage, asked of the graph a mapping
actually produced; asking it here would report a fixture as wrong for recording
something Cascade has no term for yet, which is what the findings sidecar beside
it is for.
"""

from __future__ import annotations

from rdflib import Graph

from ..result import failed, nothing_to_check, passed
from ..terms import BRIDGE, MF

HEADING = "6. Expected graphs"
TITLE = "every expected graph parses"


def run(crate):
    expected = []
    for test in crate.entries:
        result_node = crate.graph.value(test, MF.result)
        if result_node is None:
            continue
        turtle = crate.graph.value(result_node, BRIDGE.graph)
        if turtle is not None:
            expected.append((test, turtle))

    if not expected:
        return (
            nothing_to_check("the test manifest names no expected graph")
            .verdict(True, "the test manifest names no expected graph")
            .says(
                "note",
                "a manifest may legitimately name none: an input-only test "
                "records what a Bridge produced and judges nothing",
            )
        )

    failures = []
    triples = 0
    for test, turtle in expected:
        name = crate.name_of(test)
        path = crate.file_at(turtle)
        if path is None:
            failures.append(
                (
                    f"{name}: bridge:graph names {turtle}, which is not a file "
                    "in this package",
                    (),
                )
            )
            continue
        try:
            parsed = Graph()
            parsed.parse(path, format="turtle", publicID=str(turtle))
        except Exception as error:  # rdflib raises several unrelated parser types
            failures.append(
                (f"{name}: {path.name} does not parse as Turtle", (str(error),))
            )
            continue
        triples += len(parsed)

    note = f"{len(expected) - len(failures)} of {len(expected)} parsed"
    result = (passed if not failures else failed)(note)
    if not failures:
        result.verdict(
            True,
            f"{len(expected)} expected graph(s) parse as Turtle, "
            f"{triples} triples in all",
        )
    for text, detail in failures:
        result.verdict(False, text, *detail)
    return result.says(
        "note",
        "parsed, not judged. An expected graph is not validated against "
        "Cascade's shapes here: that is a Bridge's validate stage, and a pass "
        "above says the file is Turtle and nothing more",
    )
