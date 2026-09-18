import queries
from _terms import BRIDGE

FINDINGS_QUERY = "in/example-findings.rq"

SUPERSEDED_SELECT_FINDINGS_QUERY = """PREFIX fx:  <http://sparql.xyz/facade-x/ns/>
PREFIX xyz: <http://sparql.xyz/facade-x/data/>

SELECT ?sourceField ?reason ?severity ?context
WHERE {
  ?record a fx:root, xyz:ExampleRecord ;
    xyz:Accession ?context ;
    ?slot ?note .
  ?note a xyz:Note .
  BIND("ExampleRecord/Note" AS ?sourceField)
  BIND("no term for a free-text note" AS ?reason)
  BIND("info" AS ?severity)
}
"""


def test_reports_nothing_for_queries_in_the_form_their_property_declares(crate):
    assert not list(queries.malformed(crate))


def test_reports_a_mapping_that_is_not_sparql(package):
    package.edit("in/example-record.rq", "CONSTRUCT", "CONSTRUKT")
    assert "does not parse as SPARQL 1.1" in "\n".join(queries.malformed(package.crate))


def test_reports_a_detect_query_that_is_not_an_ask(package):
    package.edit("in/example-detect.rq", "ASK {", "SELECT * WHERE {")
    assert "where bridge:detectQuery requires ASK" in "\n".join(queries.malformed(package.crate))


def test_reports_a_findings_query_that_is_neither_a_construct_nor_a_select(package):
    package.write(FINDINGS_QUERY, "ASK { ?record ?slot ?note }\n")
    assert "where bridge:findingsQuery requires CONSTRUCT" in "\n".join(queries.malformed(package.crate))


def test_reports_a_findings_query_constructing_no_this_record(package):
    package.edit(FINDINGS_QUERY, "oa:hasSource bridge:thisRecord", "oa:hasSource bridge:thisrecord")
    assert "constructs no bridge:thisRecord" in "\n".join(queries.malformed(package.crate))


def test_accepts_the_superseded_select_form_of_a_findings_query(package):
    package.write(FINDINGS_QUERY, SUPERSEDED_SELECT_FINDINGS_QUERY)
    assert not list(queries.malformed(package.crate))


def test_reports_a_superseded_findings_query_projecting_other_than_the_four_variables(package):
    package.write(
        FINDINGS_QUERY,
        SUPERSEDED_SELECT_FINDINGS_QUERY.replace(
            "SELECT ?sourceField ?reason ?severity ?context",
            "SELECT ?sourceField ?reason ?severity",
        ),
    )
    assert "?sourceField ?reason ?severity ?context" in "\n".join(queries.malformed(package.crate))


def test_reports_a_superseded_findings_query_projecting_one_of_the_four_variables_twice(package):
    package.write(
        FINDINGS_QUERY,
        SUPERSEDED_SELECT_FINDINGS_QUERY.replace(
            "SELECT ?sourceField ?reason ?severity ?context",
            "SELECT ?sourceField ?sourceField ?reason ?severity ?context",
        ),
    )
    assert "?sourceField ?sourceField" in "\n".join(queries.malformed(package.crate))


def test_reports_nothing_when_the_adapter_names_no_query(crate):
    for term in (BRIDGE.mapping, BRIDGE.findingsQuery, BRIDGE.detectQuery):
        crate.graph.remove((crate.root, term, None))
    assert not list(queries.malformed(crate))
