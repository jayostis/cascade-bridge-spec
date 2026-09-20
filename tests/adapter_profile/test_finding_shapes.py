from rdflib import Graph

from _findings import SHAPES, unmet

BASE = "https://example.org/synthetic-adapter/fixtures/findings/example-0001.ttl"

PREFIXES = """@prefix rdf:    <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix sh:     <http://www.w3.org/ns/shacl#> .
@prefix oa:     <http://www.w3.org/ns/oa#> .
@prefix bridge: <https://ns.cascadeprotocol.org/bridge/v1-draft#> .
@prefix ex:     <https://example.org/synthetic-adapter/v1#> .
"""

TARGET = """oa:hasTarget [
    oa:hasSource <../in/example-0001.xml> ;
    oa:hasSelector [ a oa:XPathSelector ; rdf:value "/ExampleRecordSet/ExampleRecord[1]" ]
  ]"""


def finding(body="ex:no-term-for-a-free-text-note", motivation="oa:classifying", value=None, occurrences=None):
    written = ["[] a oa:Annotation", TARGET, "sh:resultSeverity sh:Info"]
    if body is not None:
        written.append(f"oa:hasBody {body}")
    if motivation is not None:
        written.append(f"oa:motivatedBy {motivation}")
    if value is not None:
        written.append(f"sh:value {value}")
    if occurrences is not None:
        written.append(f"bridge:occurrences {occurrences}")
    return PREFIXES + "\n" + " ;\n  ".join(written) + " .\n"


def said_about(turtle):
    return "\n".join(
        unmet(
            Graph().parse(data=turtle, format="turtle", publicID=BASE),
            Graph().parse(SHAPES, format="turtle"),
        )
    )


def test_rejects_a_finding_whose_body_is_an_oa_textual_body():
    assert (
        "A finding carries exactly one oa:hasBody, an IRI: the code the finding is an instance of, never a sentence."
    ) in said_about(finding(body='[ a oa:TextualBody ; rdf:value "no term for a free-text note" ]'))


def test_rejects_a_finding_whose_body_is_a_literal():
    assert (
        "A finding carries exactly one oa:hasBody, an IRI: the code the finding is an instance of, never a sentence."
    ) in said_about(finding(body='"no term for a free-text note"'))


def test_rejects_a_finding_carrying_two_bodies():
    assert (
        "A finding carries exactly one oa:hasBody, an IRI: the code the finding is an instance of, never a sentence."
    ) in said_about(finding(body="ex:no-term-for-a-free-text-note, ex:a-status-outside-the-set-the-vocabulary-fixes"))


def test_rejects_a_finding_carrying_no_motivation():
    assert "A finding carries exactly one oa:motivatedBy, oa:classifying." in said_about(finding(motivation=None))


def test_rejects_a_finding_motivated_by_something_other_than_classifying():
    assert "A finding carries exactly one oa:motivatedBy, oa:classifying." in said_about(
        finding(motivation="oa:commenting")
    )


def test_rejects_a_finding_carrying_two_motivations():
    assert "A finding carries exactly one oa:motivatedBy, oa:classifying." in said_about(
        finding(motivation="oa:classifying, oa:commenting")
    )


def test_rejects_a_finding_carrying_two_source_values():
    assert "A finding carries at most one sh:value, what in the source it is about." in said_about(
        finding(value='"clinically significant", "uncertain"')
    )


def test_accepts_a_finding_whose_body_is_an_iri_classifying_it_and_the_source_value_that_made_it_fire():
    assert not said_about(finding(value='"clinically significant"'))


def test_rejects_a_finding_carrying_two_occurrence_counts():
    assert "bridge:occurrences" in said_about(finding(occurrences="2, 3"))
    assert not said_about(finding(occurrences="2"))


def test_rejects_a_finding_whose_occurrence_count_is_no_integer():
    assert "bridge:occurrences" in said_about(finding(occurrences='"two"'))
    assert not said_about(finding(occurrences="297"))


def test_rejects_a_finding_whose_occurrence_count_is_one_where_a_count_of_one_is_written_by_omitting_it():
    assert "bridge:occurrences" in said_about(finding(occurrences="1"))
    assert not said_about(finding())
