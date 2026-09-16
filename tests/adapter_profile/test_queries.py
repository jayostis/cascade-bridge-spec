import queries
from _terms import BRIDGE


def test_reports_nothing_for_queries_in_the_form_their_property_declares(crate):
    assert not list(queries.malformed(crate))


def test_reports_a_mapping_that_is_not_sparql(package):
    package.edit("in/example-record.rq", "CONSTRUCT", "CONSTRUKT")
    assert "does not parse as SPARQL 1.1" in "\n".join(queries.malformed(package.crate))


def test_reports_a_detect_query_that_is_not_an_ask(package):
    package.edit("in/example-detect.rq", "ASK {", "SELECT * WHERE {")
    assert "where bridge:detectQuery requires ASK" in "\n".join(
        queries.malformed(package.crate)
    )


def test_reports_a_findings_query_projecting_other_than_the_four_variables(package):
    package.edit(
        "in/example-findings.rq",
        "SELECT ?sourceField ?reason ?severity ?context",
        "SELECT ?sourceField ?reason ?severity",
    )
    assert "?sourceField ?reason ?severity ?context" in "\n".join(
        queries.malformed(package.crate)
    )


def test_reports_nothing_when_the_adapter_names_no_query(crate):
    for term in (BRIDGE.mapping, BRIDGE.findingsQuery, BRIDGE.detectQuery):
        crate.graph.remove((crate.root, term, None))
    assert not list(queries.malformed(crate)), (
        "found nothing of its kind is not a fault: the shapes are what require "
        "an adapter to name a mapping at all"
    )
