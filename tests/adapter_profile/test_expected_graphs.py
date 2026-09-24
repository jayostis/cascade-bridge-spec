import expected_graphs
from _terms import BRIDGE

EXPECTED = "fixtures/expected/example-0001.ttl"


def test_reports_nothing_for_an_expected_graph_that_parses(crate):
    assert not list(expected_graphs.unparsable(crate))


def test_reports_an_expected_graph_that_is_not_turtle(package):
    package.edit(EXPECTED, "@prefix ex:", "@prefixx ex:")
    said = "\n".join(expected_graphs.unparsable(package.crate))
    assert "example-0001: example-0001.ttl does not parse as Turtle" in said


def test_reports_nothing_for_entries_naming_no_expected_graph(crate):
    crate.graph.remove((None, BRIDGE.expectedGraph, None))
    assert not list(expected_graphs.unparsable(crate))


def test_never_judges_an_expected_graph_against_cascades_shapes(package):
    prefix = "@prefix ex:   <https://example.org/synthetic-adapter/v1#> ."
    package.edit(
        EXPECTED,
        prefix,
        prefix + "\n<https://example.org/x> <https://example.org/undefined> 1 .",
    )
    assert not list(expected_graphs.unparsable(package.crate))
