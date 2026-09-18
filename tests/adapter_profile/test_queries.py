import queries
from _terms import BRIDGE

FINDINGS_QUERY = "in/example-findings.rq"

A_FINDINGS_QUERY_NAMING_THIS_RECORD_OUTSIDE_ITS_TARGETS_SOURCE = """PREFIX rdf:    <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX sh:     <http://www.w3.org/ns/shacl#>
PREFIX oa:     <http://www.w3.org/ns/oa#>
PREFIX fx:     <http://sparql.xyz/facade-x/ns/>
PREFIX xyz:    <http://sparql.xyz/facade-x/data/>
PREFIX bridge: <https://ns.cascadeprotocol.org/bridge/v1-draft#>

CONSTRUCT {
  [] a oa:Annotation ;
    oa:hasTarget [
      oa:hasSource <https://example.org/a-document-this-record-was-not-read-from> ;
      oa:hasSelector [ a oa:XPathSelector ; rdf:value "Note" ]
    ] ;
    oa:hasBody [ a oa:TextualBody ; rdf:value bridge:thisRecord ] ;
    sh:resultSeverity sh:Info .
}
WHERE {
  ?record a fx:root, xyz:ExampleRecord .
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


def test_reports_a_findings_query_that_is_an_ask(package):
    package.write(FINDINGS_QUERY, "ASK { ?record ?slot ?note }\n")
    assert "where bridge:findingsQuery requires CONSTRUCT" in "\n".join(queries.malformed(package.crate))


def test_reports_a_findings_query_that_is_a_select(package):
    package.write(FINDINGS_QUERY, "SELECT ?note WHERE { ?record ?slot ?note }\n")
    assert "is a SELECT query, where bridge:findingsQuery requires CONSTRUCT" in "\n".join(
        queries.malformed(package.crate)
    )


def test_reports_a_findings_query_constructing_no_this_record(package):
    package.edit(FINDINGS_QUERY, "oa:hasSource bridge:thisRecord", "oa:hasSource bridge:thisrecord")
    assert "constructs no oa:hasSource bridge:thisRecord" in "\n".join(queries.malformed(package.crate))


def test_reports_a_findings_query_naming_this_record_outside_its_targets_source(package):
    package.write(FINDINGS_QUERY, A_FINDINGS_QUERY_NAMING_THIS_RECORD_OUTSIDE_ITS_TARGETS_SOURCE)
    assert "constructs no oa:hasSource bridge:thisRecord" in "\n".join(queries.malformed(package.crate))


def test_reports_nothing_when_the_adapter_names_no_query(crate):
    for term in (BRIDGE.mapping, BRIDGE.findingsQuery, BRIDGE.detectQuery):
        crate.graph.remove((crate.root, term, None))
    assert not list(queries.malformed(crate))
