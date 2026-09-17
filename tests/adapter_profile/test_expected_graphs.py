import expected_graphs

EXPECTED = "fixtures/expected/example-0001.ttl"


def test_reports_nothing_for_an_expected_graph_that_parses(crate):
    assert not list(expected_graphs.unparsable(crate))


def test_reports_an_expected_graph_that_is_not_turtle(package):
    package.edit(EXPECTED, "@prefix ex:", "@prefixx ex:")
    assert "does not parse as Turtle" in "\n".join(
        expected_graphs.unparsable(package.crate)
    )


def test_never_judges_an_expected_graph_against_cascades_shapes(package):
    prefix = "@prefix ex:   <https://example.org/synthetic-adapter/v1#> ."
    package.edit(
        EXPECTED,
        prefix,
        prefix + "\n<https://example.org/x> <https://example.org/undefined> 1 .",
    )
    assert not list(expected_graphs.unparsable(package.crate))
