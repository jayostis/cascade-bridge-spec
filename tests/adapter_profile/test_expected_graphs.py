import expected_graphs
from _terms import BRIDGE

EXPECTED = "fixtures/expected/example-0001.ttl"


class TestExpectedGraphsOfAConversion:
    """Expected graphs of a conversion · adapter/profile/must/expected_graphs.py

    The graph a conversion test expects is checked only for being Turtle that parses; whether it is right is the
    Bridge's run to say.
    """

    class TestGivenATestsExpectedGraph:
        """given a test's expected graph"""

        def test_reports_nothing_for_an_expected_graph_that_parses(self, crate):
            assert not list(expected_graphs.unparsable(crate))

        def test_reports_an_expected_graph_that_is_not_turtle(self, package):
            """reports an expected graph that is not Turtle"""
            package.edit(EXPECTED, "@prefix ex:", "@prefixx ex:")
            said = "\n".join(expected_graphs.unparsable(package.crate))
            assert "example-0001: example-0001.ttl does not parse as Turtle" in said

        def test_reports_nothing_for_entries_naming_no_expected_graph(self, crate):
            crate.graph.remove((None, BRIDGE.expectedGraph, None))
            assert not list(expected_graphs.unparsable(crate))

        def test_never_judges_it_against_the_cascade_vocabularys_shapes(self, package):
            """never judges it against the Cascade vocabulary's shapes"""
            prefix = "@prefix ex:     <https://example.org/synthetic-adapter/v1#> ."
            package.edit(
                EXPECTED,
                prefix,
                prefix + "\n<https://example.org/x> <https://example.org/undefined> 1 .",
            )
            assert not list(expected_graphs.unparsable(package.crate))
