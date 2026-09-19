import queries
from _terms import BRIDGE

FINDINGS_QUERY = "in/example-findings.rq"

PREFIXES = """PREFIX rdf:    <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX sh:     <http://www.w3.org/ns/shacl#>
PREFIX oa:     <http://www.w3.org/ns/oa#>
PREFIX fx:     <http://sparql.xyz/facade-x/ns/>
PREFIX xyz:    <http://sparql.xyz/facade-x/data/>
PREFIX bridge: <https://ns.cascadeprotocol.org/bridge/v1-draft#>
"""

WHERE = """WHERE {
  ?record a fx:root, xyz:ExampleRecord ;
    ?slot ?note .
  ?note a xyz:Note .
}
"""


def findings_query(template):
    return f"{PREFIXES}\nCONSTRUCT {{\n{template}\n}}\n{WHERE}"


A_FINDINGS_QUERY_NAMING_THIS_RECORD_OUTSIDE_ITS_TARGETS_SOURCE = findings_query("""  [] a oa:Annotation ;
    oa:hasTarget [
      oa:hasSource <https://example.org/a-document-this-record-was-not-read-from> ;
      oa:hasSelector [ a oa:XPathSelector ; rdf:value "Note" ]
    ] ;
    oa:hasBody [ a oa:TextualBody ; rdf:value bridge:thisRecord ] ;
    sh:resultSeverity sh:Info .""")


A_FINDINGS_QUERY_TARGETING_THE_RECORD_BY_NAME = findings_query("""  [] a oa:Annotation ;
    oa:hasTarget bridge:thisRecord ;
    oa:hasBody [ a oa:TextualBody ; rdf:value "no term for a free-text note" ] ;
    sh:resultSeverity sh:Info .
  bridge:thisRecord oa:hasSource bridge:thisRecord ;
    oa:hasSelector [ a oa:XPathSelector ; rdf:value "Note" ] .""")


A_FINDINGS_QUERY_SOURCING_THIS_RECORD_OUTSIDE_EVERY_TARGET = findings_query("""  [] a oa:Annotation ;
    oa:hasTarget [ oa:hasSelector [ a oa:XPathSelector ; rdf:value "Note" ] ] ;
    oa:hasBody [ a oa:TextualBody ; rdf:value "no term for a free-text note" ] ;
    sh:resultSeverity sh:Info .
  [] oa:hasSource bridge:thisRecord .""")


A_FINDINGS_QUERY_CONSTRUCTING_NO_ANNOTATION = findings_query("""  [] oa:hasSource bridge:thisRecord ;
    oa:hasSelector [ a oa:XPathSelector ; rdf:value "Note" ] .""")


TWO_FINDINGS_SHARING_ONE_TARGET = findings_query("""  [] a oa:Annotation ;
    oa:hasTarget _:t ;
    oa:hasBody [ a oa:TextualBody ; rdf:value "no term for a free-text note" ] ;
    sh:resultSeverity sh:Info .
  [] a oa:Annotation ;
    oa:hasTarget _:t ;
    oa:hasBody [ a oa:TextualBody ; rdf:value "a second note" ] ;
    sh:resultSeverity sh:Info .
  _:t oa:hasSource bridge:thisRecord ;
    oa:hasSelector [ a oa:XPathSelector ; rdf:value "Note" ] .""")


A_FINDINGS_QUERY_TARGETING_A_VARIABLE = findings_query("""  [] a oa:Annotation ;
    oa:hasTarget ?note ;
    oa:hasBody [ a oa:TextualBody ; rdf:value "no term for a free-text note" ] ;
    sh:resultSeverity sh:Info .
  ?note oa:hasSource bridge:thisRecord ;
    oa:hasSelector [ a oa:XPathSelector ; rdf:value "Note" ] .""")


TWO_FINDINGS_EACH_WITH_A_TARGET_OF_ITS_OWN = findings_query("""  [] a oa:Annotation ;
    oa:hasTarget [
      oa:hasSource bridge:thisRecord ;
      oa:hasSelector [ a oa:XPathSelector ; rdf:value "Note" ]
    ] ;
    oa:hasBody [ a oa:TextualBody ; rdf:value "no term for a free-text note" ] ;
    sh:resultSeverity sh:Info .
  [] a oa:Annotation ;
    oa:hasTarget [
      oa:hasSource bridge:thisRecord ;
      oa:hasSelector [ a oa:XPathSelector ; rdf:value "Label" ]
    ] ;
    oa:hasBody [ a oa:TextualBody ; rdf:value "a second note" ] ;
    sh:resultSeverity sh:Info .""")


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
    assert "constructs a finding that targets no [ oa:hasSource bridge:thisRecord ]" in "\n".join(
        queries.malformed(package.crate)
    )


def test_reports_a_findings_query_naming_this_record_outside_its_targets_source(package):
    package.write(FINDINGS_QUERY, A_FINDINGS_QUERY_NAMING_THIS_RECORD_OUTSIDE_ITS_TARGETS_SOURCE)
    assert "constructs a finding that targets no [ oa:hasSource bridge:thisRecord ]" in "\n".join(
        queries.malformed(package.crate)
    )


def test_reports_a_findings_query_sourcing_this_record_outside_every_target(package):
    package.write(FINDINGS_QUERY, A_FINDINGS_QUERY_SOURCING_THIS_RECORD_OUTSIDE_EVERY_TARGET)
    assert "constructs a finding that targets no [ oa:hasSource bridge:thisRecord ]" in "\n".join(
        queries.malformed(package.crate)
    )


def test_reports_a_findings_query_constructing_no_annotation(package):
    package.write(FINDINGS_QUERY, A_FINDINGS_QUERY_CONSTRUCTING_NO_ANNOTATION)
    assert "constructs no oa:Annotation" in "\n".join(queries.malformed(package.crate))


def test_reports_a_findings_query_targeting_a_name_rather_than_a_blank_node(package):
    package.write(FINDINGS_QUERY, A_FINDINGS_QUERY_TARGETING_THE_RECORD_BY_NAME)
    assert (
        "targets <https://ns.cascadeprotocol.org/bridge/v1-draft#thisRecord>, where a finding's oa:hasTarget "
        "is a blank node written for that one finding: one name is one node for every finding the query produces"
    ) in "\n".join(queries.malformed(package.crate))


def test_reports_a_findings_query_giving_two_findings_one_labelled_blank_node_as_their_target(package):
    package.write(FINDINGS_QUERY, TWO_FINDINGS_SHARING_ONE_TARGET)
    assert (
        "targets _:t from more than one finding, where a finding's oa:hasTarget is a blank node written "
        "for that one finding"
    ) in "\n".join(queries.malformed(package.crate))


def test_reports_a_findings_query_targeting_a_variable_as_a_node_the_lift_already_holds(package):
    package.write(FINDINGS_QUERY, A_FINDINGS_QUERY_TARGETING_A_VARIABLE)
    messages = "\n".join(queries.malformed(package.crate))
    assert (
        "targets ?note, where a finding's oa:hasTarget is a blank node written for that one finding: "
        "a variable is bound to a node the lift already holds"
    ) in messages
    assert "one name is one node" not in messages


def test_reports_nothing_for_two_findings_each_targeting_a_blank_node_of_its_own(package):
    package.write(FINDINGS_QUERY, TWO_FINDINGS_EACH_WITH_A_TARGET_OF_ITS_OWN)
    assert not list(queries.malformed(package.crate))


def test_reports_nothing_when_the_adapter_names_no_query(crate):
    for term in (BRIDGE.mapping, BRIDGE.findingsQuery, BRIDGE.detectQuery):
        crate.graph.remove((crate.root, term, None))
    assert not list(queries.malformed(crate))
