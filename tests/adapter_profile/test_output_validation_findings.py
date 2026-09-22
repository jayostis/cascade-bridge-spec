"""What a finding about the produced graph carries: the SHACL result that made it, pointed at the source record."""

from rdflib import Graph

from _findings import SHAPES, unmet

BASE = "https://example.org/synthetic-adapter/fixtures/findings/example-0001.ttl"

PREFIXES = """@prefix rdf:    <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix sh:     <http://www.w3.org/ns/shacl#> .
@prefix oa:     <http://www.w3.org/ns/oa#> .
@prefix bridge: <https://ns.cascadeprotocol.org/bridge/v1-draft#> .
@prefix ex:     <https://example.org/synthetic-adapter/v1#> .
"""

RECORD = "/ExampleRecordSet/ExampleRecord[1]"


def finding(
    body="sh:MinCountConstraintComponent",
    severity="sh:Violation",
    path="ex:status",
    focus="ex:record-1",
    record=RECORD,
    refined=None,
):
    refinement = "" if refined is None else f' ; oa:refinedBy [ a oa:XPathSelector ; rdf:value "{refined}" ]'
    written = [
        "[] a oa:Annotation",
        "oa:hasTarget [ oa:hasSource <../in/example-0001.xml> ; "
        f'oa:hasSelector [ a oa:XPathSelector ; rdf:value "{record}"{refinement} ] ]',
        f"oa:hasBody {body}",
        "oa:motivatedBy oa:classifying",
        f"sh:resultSeverity {severity}",
    ]
    if path is not None:
        written.append(f"sh:resultPath {path}")
    if focus is not None:
        written.append(f"sh:focusNode {focus}")
    return " ;\n  ".join(written) + " .\n"


def said_about(*findings):
    return "\n".join(
        unmet(
            Graph().parse(data=PREFIXES + "\n" + "\n".join(findings), format="turtle", publicID=BASE),
            Graph().parse(SHAPES, format="turtle"),
        )
    )


def test_a_findings_focus_node_is_the_iri_of_the_node_that_broke_and_never_a_blank_node():
    assert not said_about(finding())
    assert "sh:focusNode" in said_about(finding(focus="[ a ex:Record ]"))


def test_two_findings_about_one_record_carry_a_target_and_a_selector_of_their_own_refined_no_further():
    assert not said_about(finding(path="ex:status"), finding(path="ex:label"))
    assert "refined no further" in said_about(finding(refined="Status"))


def test_an_undeclared_predicate_finding_names_the_predicate_as_its_result_path_at_sh_violation():
    assert not said_about(finding(body="bridge:predicateNotDeclared", path="ex:sourceRecordId"))
    assert "sh:resultPath" in said_about(finding(body="bridge:predicateNotDeclared", path=None))
    assert "sh:Violation" in said_about(finding(body="bridge:predicateNotDeclared", severity="sh:Info"))
