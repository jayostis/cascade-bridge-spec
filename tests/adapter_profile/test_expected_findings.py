from rdflib import Graph
from rdflib.namespace import RDF, SH

import expected_findings
from _codes import W3C_XML_SCHEMA_RULE_ANCHORS
from _terms import BRIDGE, MF, OA
from adapter_profile_world import FIXTURE, selected_by

FINDINGS = "fixtures/findings/example-0001.ttl"

PREFIXES = """@prefix rdf:    <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix sh:     <http://www.w3.org/ns/shacl#> .
@prefix oa:     <http://www.w3.org/ns/oa#> .
@prefix bridge: <https://ns.cascadeprotocol.org/bridge/v1-draft#> .
@prefix ex:     <https://example.org/synthetic-adapter/v1#> .
"""

TWO_FINDINGS_SHARING_ONE_SELECTOR = (
    PREFIXES
    + """
<#selector> a oa:XPathSelector ;
  rdf:value "/ExampleRecordSet/ExampleRecord[1]" ;
  oa:refinedBy [ a oa:XPathSelector ; rdf:value "Note" ] .

[] a oa:Annotation ;
  oa:hasTarget [ oa:hasSource <../in/example-0001.xml> ; oa:hasSelector <#selector> ] ;
  oa:hasBody [ a oa:TextualBody ; rdf:value "no term for a free-text note" ] ;
  sh:resultSeverity sh:Info .

[] a oa:Annotation ;
  oa:hasTarget [ oa:hasSource <../in/example-0001.xml> ; oa:hasSelector <#selector> ] ;
  oa:hasBody [ a oa:TextualBody ; rdf:value "a second note" ] ;
  sh:resultSeverity sh:Info .
"""
)

TWO_FINDINGS_SHARING_ONE_TARGET = (
    PREFIXES
    + """
_:t oa:hasSource <../in/example-0001.xml> ;
  oa:hasSelector [ a oa:XPathSelector ; rdf:value "/ExampleRecordSet/ExampleRecord[1]" ;
                   oa:refinedBy [ a oa:XPathSelector ; rdf:value "Note" ] ] .

[] a oa:Annotation ;
  oa:hasTarget _:t ;
  oa:hasBody [ a oa:TextualBody ; rdf:value "no term for a free-text note" ] ;
  sh:resultSeverity sh:Info .

[] a oa:Annotation ;
  oa:hasTarget _:t ;
  oa:hasBody [ a oa:TextualBody ; rdf:value "a second note" ] ;
  sh:resultSeverity sh:Info .
"""
)

A_STRAY_SELECTOR_AND_NO_FINDING = (
    PREFIXES
    + """
[] a oa:XPathSelector ; rdf:value "/no/such/path[99]" .
"""
)


def finding(
    source="<../in/example-0001.xml>",
    record="/ExampleRecordSet/ExampleRecord[1]",
    refined="Note",
    body="ex:no-term-for-a-free-text-note",
    severity="sh:Info",
):
    target = [f"oa:hasSource {source}"]
    if record is not None:
        refinement = "" if refined is None else f' ; oa:refinedBy [ a oa:XPathSelector ; rdf:value "{refined}" ]'
        target.append(f'oa:hasSelector [ a oa:XPathSelector ; rdf:value "{record}"{refinement} ]')
    annotation = ["[] a oa:Annotation", f"oa:hasTarget [ {' ; '.join(target)} ]"]
    if body is not None:
        annotation.append(f"oa:hasBody {body}")
    annotation.append("oa:motivatedBy oa:classifying")
    if severity is not None:
        annotation.append(f"sh:resultSeverity {severity}")
    return PREFIXES + "\n" + " ;\n  ".join(annotation) + " .\n"


def test_reports_nothing_for_findings_that_select_the_node_each_one_is_about(crate):
    assert not list(expected_findings.faulty(crate))


def test_reports_expected_findings_that_are_not_turtle(package):
    package.edit(FINDINGS, "@prefix rdf:", "@prefixx rdf:")
    assert "does not parse as Turtle" in "\n".join(expected_findings.faulty(package.crate))


def test_reports_expected_findings_that_are_not_a_file_in_the_package(package):
    crate = package.crate
    crate.file_at(next(crate.graph.objects(None, BRIDGE.expectedFindings))).unlink()
    assert "which is not a file in this package" in "\n".join(expected_findings.faulty(crate))


def test_reports_a_finding_that_selects_nothing(package):
    package.write(FINDINGS, finding(record="/ExampleRecordSet/ExampleRecord[3]"))
    assert "selects no node of example-0001.xml" in "\n".join(expected_findings.faulty(package.crate))


def test_reports_a_refined_selector_that_selects_no_node_of_its_record(package):
    package.write(FINDINGS, finding(refined="Absent"))
    assert "selects no node of example-0001.xml" in "\n".join(expected_findings.faulty(package.crate))


def test_reports_a_refined_selector_that_selects_more_than_one_node_of_its_record(package):
    package.write(FINDINGS, finding(refined="*"))
    assert "selects 2 nodes of example-0001.xml, where a finding selects exactly one" in "\n".join(
        expected_findings.faulty(package.crate)
    )


def test_reports_a_refined_selector_that_selects_a_node_of_another_record(package):
    package.write(
        FINDINGS,
        finding(record="/ExampleRecordSet/ExampleRecord[2]", refined="../ExampleRecord[1]/Note"),
    )
    assert (
        "../ExampleRecord[1]/Note selects a node of example-0001.xml outside "
        "/ExampleRecordSet/ExampleRecord[2], where a refinement selects a node of the record"
    ) in "\n".join(expected_findings.faulty(package.crate))


def test_reports_a_refined_selector_that_names_its_own_record_from_the_document_root(package):
    package.write(
        FINDINGS,
        finding(record="/ExampleRecordSet/ExampleRecord[2]", refined="/ExampleRecordSet/ExampleRecord[2]/Note"),
    )
    assert (
        "/ExampleRecordSet/ExampleRecord[2]/Note is an XPath rooted at example-0001.xml, "
        "where a refinement is relative to the record its selector names"
    ) in "\n".join(expected_findings.faulty(package.crate))


def test_reports_a_refined_selector_rooted_at_the_document_behind_leading_whitespace(package):
    package.write(
        FINDINGS,
        finding(record="/ExampleRecordSet/ExampleRecord[2]", refined=" /ExampleRecordSet/ExampleRecord[2]/Note"),
    )
    assert (
        "is an XPath rooted at example-0001.xml, where a refinement is relative to the record its selector names"
    ) in "\n".join(expected_findings.faulty(package.crate))


def test_reports_a_refined_selector_rooted_at_the_document_inside_parentheses(package):
    package.write(
        FINDINGS,
        finding(record="/ExampleRecordSet/ExampleRecord[2]", refined="(/ExampleRecordSet/ExampleRecord[2]/Note)"),
    )
    assert (
        "is an XPath rooted at example-0001.xml, where a refinement is relative to the record its selector names"
    ) in "\n".join(expected_findings.faulty(package.crate))


def test_reports_a_refined_selector_rooted_at_the_document_once_though_it_also_leaves_its_record(package):
    package.write(
        FINDINGS,
        finding(record="/ExampleRecordSet/ExampleRecord[2]", refined="/ExampleRecordSet/ExampleRecord[1]/Note"),
    )
    said = list(expected_findings.faulty(package.crate))
    assert len(said) == 1, said
    assert "where a refinement is relative to the record its selector names" in said[0]


def test_reports_nothing_for_a_refined_selector_that_selects_an_attribute(package):
    package.write(FINDINGS, finding(refined="@Version"))
    assert not list(expected_findings.faulty(package.crate))


def test_reports_a_record_selector_that_selects_an_attribute_as_a_node_that_is_not_an_element(package):
    package.write(FINDINGS, finding(record="/ExampleRecordSet/ExampleRecord[1]/@Version", refined=None))
    assert (
        "selects a node of example-0001.xml that is not an element, where a record's selector selects the record"
    ) in "\n".join(expected_findings.faulty(package.crate))


def test_reports_a_record_selector_that_selects_a_text_node_as_a_node_that_is_not_an_element(package):
    package.write(FINDINGS, finding(record="/ExampleRecordSet/ExampleRecord[1]/Label/text()", refined=None))
    assert (
        "selects a node of example-0001.xml that is not an element, where a record's selector selects the record"
    ) in "\n".join(expected_findings.faulty(package.crate))


def test_reports_nothing_for_a_finding_about_the_document_selecting_the_document_element(package):
    package.write(FINDINGS, finding(record="/ExampleRecordSet", refined=None))
    assert not list(expected_findings.faulty(package.crate))


def test_reports_a_record_selector_that_selects_an_element_inside_a_record(package):
    package.write(FINDINGS, finding(record="/ExampleRecordSet/ExampleRecord[1]/Label", refined=None))
    assert (
        "selects Label of example-0001.xml, where a finding is about the document, selecting its "
        "document element, or about a record, selecting ExampleRecord, the adapter's "
        "bridge:elementNameOfEachRecord"
    ) in "\n".join(expected_findings.faulty(package.crate))


def test_holds_a_record_selector_to_no_element_name_when_the_adapter_declares_none(package):
    package.write(FINDINGS, finding(record="/ExampleRecordSet/ExampleRecord[1]/Label[1]", refined=None))
    crate = package.crate
    crate.graph.remove((crate.root, BRIDGE.elementNameOfEachRecord, None))
    assert not list(expected_findings.faulty(crate))


def test_reports_a_selector_that_is_not_an_xpath(package):
    package.write(FINDINGS, finding(refined="Note["))
    assert "is not an XPath this lint can evaluate" in "\n".join(expected_findings.faulty(package.crate))


def test_reports_a_finding_naming_a_source_other_than_the_entrys_input(package):
    package.write(FINDINGS, finding(source="<../in/example-0002.xml>"))
    assert (
        "names example-0002.xml as its oa:hasSource, where the entry's bridge:input is example-0001.xml"
        in "\n".join(expected_findings.faulty(package.crate))
    )


def test_reports_a_finding_with_no_selector(package):
    package.write(FINDINGS, finding(record=None))
    assert "carries exactly one oa:hasSelector" in "\n".join(expected_findings.faulty(package.crate))


def test_reports_a_finding_with_no_body(package):
    package.write(FINDINGS, finding(body=None))
    assert "carries exactly one oa:hasBody" in "\n".join(expected_findings.faulty(package.crate))


def test_reports_a_finding_with_no_severity(package):
    package.write(FINDINGS, finding(severity=None))
    assert "carries exactly one sh:resultSeverity" in "\n".join(expected_findings.faulty(package.crate))


def test_reports_a_severity_outside_the_scale(package):
    package.write(FINDINGS, finding(severity="<https://example.org/synthetic-adapter/severe>"))
    assert "sh:Info, sh:Warning, sh:Violation" in "\n".join(expected_findings.faulty(package.crate))


def test_reports_two_findings_sharing_one_selector(package):
    package.write(FINDINGS, TWO_FINDINGS_SHARING_ONE_SELECTOR)
    assert "selector of its own, shared with no other finding" in "\n".join(expected_findings.faulty(package.crate))


def test_reports_two_findings_sharing_one_target(package):
    package.write(FINDINGS, TWO_FINDINGS_SHARING_ONE_TARGET)
    assert "a target of its own, shared with no other finding" in "\n".join(expected_findings.faulty(package.crate))


def test_reports_expected_findings_holding_no_finding_at_all(package):
    package.write(FINDINGS, PREFIXES)
    assert "carries no oa:Annotation" in "\n".join(expected_findings.faulty(package.crate))


def test_reports_expected_findings_whose_only_finding_mistypes_the_annotation_class(package):
    package.write(FINDINGS, finding().replace("a oa:Annotation", "a oa:Annotaton"))
    assert "carries no oa:Annotation" in "\n".join(expected_findings.faulty(package.crate))


def test_reports_expected_findings_holding_a_selector_but_no_finding(package):
    package.write(FINDINGS, A_STRAY_SELECTOR_AND_NO_FINDING)
    assert "carries no oa:Annotation" in "\n".join(expected_findings.faulty(package.crate))


def test_evaluates_no_selector_for_an_entry_naming_no_input(crate):
    for test in crate.entries:
        crate.graph.remove((crate.graph.value(test, MF.action), BRIDGE.input, None))
    assert not [message for message in expected_findings.faulty(crate) if "selects" in message]


def test_reports_nothing_for_a_record_selector_that_names_its_record_another_way(package):
    package.write(FINDINGS, finding(record="/ExampleRecordSet/*[local-name()='ExampleRecord'][1]"))
    assert not list(expected_findings.faulty(package.crate))


def test_reports_nothing_for_a_document_selector_that_names_the_document_element_another_way(package):
    package.write(FINDINGS, finding(record="/*[local-name()='ExampleRecordSet']", refined=None))
    assert not list(expected_findings.faulty(package.crate))


A_FINDING_WITH_TWO_TARGETS = (
    PREFIXES
    + """
[] a oa:Annotation ;
  oa:hasTarget [ oa:hasSource <../in/example-0001.xml> ;
                 oa:hasSelector [ a oa:XPathSelector ; rdf:value "/ExampleRecordSet/ExampleRecord[1]" ] ] ;
  oa:hasTarget [ oa:hasSource <../in/example-0001.xml> ;
                 oa:hasSelector [ a oa:XPathSelector ; rdf:value "/ExampleRecordSet/ExampleRecord[2]" ] ] ;
  oa:hasBody [ a oa:TextualBody ; rdf:value "no term for a free-text note" ] ;
  sh:resultSeverity sh:Info .
"""
)

A_FINDING_SOURCED_BY_A_LITERAL = (
    PREFIXES
    + """
[] a oa:Annotation ;
  oa:hasTarget [ oa:hasSource "example-0001.xml" ;
                 oa:hasSelector [ a oa:XPathSelector ; rdf:value "/ExampleRecordSet/ExampleRecord[1]" ] ] ;
  oa:hasBody [ a oa:TextualBody ; rdf:value "no term for a free-text note" ] ;
  sh:resultSeverity sh:Info .
"""
)

A_FINDING_NAMED_RATHER_THAN_WRITTEN_FOR_ITSELF = (
    PREFIXES
    + """
<#the-one-finding> a oa:Annotation ;
  oa:hasTarget [ oa:hasSource <../in/example-0001.xml> ;
                 oa:hasSelector [ a oa:XPathSelector ; rdf:value "/ExampleRecordSet/ExampleRecord[1]" ] ] ;
  oa:hasBody [ a oa:TextualBody ; rdf:value "no term for a free-text note" ] ;
  sh:resultSeverity sh:Info .
"""
)


def finding_carrying(body="ex:no-term-for-a-free-text-note", selector=None):
    selector = selector or '[ a oa:XPathSelector ; rdf:value "/ExampleRecordSet/ExampleRecord[1]" ]'
    return (
        PREFIXES
        + f"""
[] a oa:Annotation ;
  oa:hasTarget [ oa:hasSource <../in/example-0001.xml> ; oa:hasSelector {selector} ] ;
  oa:hasBody {body} ;
  oa:motivatedBy oa:classifying ;
  sh:resultSeverity sh:Info .
"""
    )


def test_reports_a_finding_carrying_more_than_one_target(package):
    package.write(FINDINGS, A_FINDING_WITH_TWO_TARGETS)
    assert ("A finding about the source document carries exactly one oa:hasTarget") in "\n".join(
        expected_findings.faulty(package.crate)
    )


def test_reports_a_target_naming_its_source_as_a_literal_rather_than_by_iri(package):
    package.write(FINDINGS, A_FINDING_SOURCED_BY_A_LITERAL)
    assert (
        "A finding's target names exactly one oa:hasSource by IRI, the document the record was read from."
    ) in "\n".join(expected_findings.faulty(package.crate))


def test_reports_a_finding_named_rather_than_written_for_itself(package):
    package.write(FINDINGS, A_FINDING_NAMED_RATHER_THAN_WRITTEN_FOR_ITSELF)
    assert "A finding is a blank node written for that one finding" in "\n".join(
        expected_findings.faulty(package.crate)
    )


def test_reports_a_record_selector_that_is_not_an_xpath_selector(package):
    package.write(
        FINDINGS,
        finding_carrying(selector='[ a oa:TextQuoteSelector ; rdf:value "/ExampleRecordSet/ExampleRecord[1]" ]'),
    )
    assert "A record's selector is an oa:XPathSelector." in "\n".join(expected_findings.faulty(package.crate))


def test_reports_a_record_selector_carrying_no_xpath(package):
    package.write(FINDINGS, finding_carrying(selector="[ a oa:XPathSelector ]"))
    assert "A selector carries exactly one rdf:value, its XPath, a string." in "\n".join(
        expected_findings.faulty(package.crate)
    )


def test_reports_a_record_selector_refined_more_than_once(package):
    package.write(
        FINDINGS,
        finding_carrying(
            selector=(
                '[ a oa:XPathSelector ; rdf:value "/ExampleRecordSet/ExampleRecord[1]" ; '
                'oa:refinedBy [ a oa:XPathSelector ; rdf:value "Label" ] ; '
                'oa:refinedBy [ a oa:XPathSelector ; rdf:value "Note" ] ]'
            )
        ),
    )
    assert "A record's selector is refined by at most one selector" in "\n".join(
        expected_findings.faulty(package.crate)
    )


def test_reports_a_refinement_that_is_not_an_xpath_selector(package):
    package.write(
        FINDINGS,
        finding_carrying(
            selector=(
                '[ a oa:XPathSelector ; rdf:value "/ExampleRecordSet/ExampleRecord[1]" ; '
                'oa:refinedBy [ a oa:TextQuoteSelector ; rdf:value "Note" ] ]'
            )
        ),
    )
    assert "A selector refining a record's selector is an oa:XPathSelector." in "\n".join(
        expected_findings.faulty(package.crate)
    )


def test_reports_a_refinement_refined_further(package):
    package.write(
        FINDINGS,
        finding_carrying(
            selector=(
                '[ a oa:XPathSelector ; rdf:value "/ExampleRecordSet/ExampleRecord[1]" ; '
                'oa:refinedBy [ a oa:XPathSelector ; rdf:value "Note" ; '
                'oa:refinedBy [ a oa:XPathSelector ; rdf:value "text()" ] ] ]'
            )
        ),
    )
    assert "A selector refining a record's selector is refined no further." in "\n".join(
        expected_findings.faulty(package.crate)
    )


A_GAP_OF_THE_SCHEME = "ex:no-term-for-a-free-text-note"
A_GAP_WHOSE_VALUE_IS_OUTSIDE_A_FIXED_SET = "ex:a-status-outside-the-set-the-vocabulary-fixes"


def coded_finding(
    body=A_GAP_OF_THE_SCHEME,
    record="/ExampleRecordSet/ExampleRecord[1]",
    refined="Note",
    value=None,
    severity="sh:Info",
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
    if value is not None:
        written.append(f"sh:value {value}")
    return PREFIXES + "\n" + " ;\n  ".join(written) + " .\n"


def said_about(package):
    return [message for message in expected_findings.faulty(package.crate) if "example-0001.ttl" in message]


def test_reports_nothing_for_a_finding_whose_body_is_a_gap_of_the_adapters_gap_scheme(package):
    package.gap_scheme().write(FINDINGS, coded_finding())
    assert not said_about(package)


def test_reports_a_finding_whose_body_is_no_gap_of_the_adapters_gap_scheme(package):
    package.gap_scheme().write(FINDINGS, coded_finding(body="ex:a-gap-the-scheme-does-not-hold"))
    assert (
        "https://example.org/synthetic-adapter/v1#a-gap-the-scheme-does-not-hold is not a gap of the adapter's "
        "bridge:gapScheme, the anchor of a validation rule in a W3C XML Schema Recommendation, "
        "bridge:schemaRuleUnnamed, or bridge:pathNotAccounted"
    ) in "\n".join(said_about(package))


def test_reports_nothing_for_a_finding_whose_body_is_the_anchor_of_a_w3c_xml_schema_validation_rule(package):
    package.gap_scheme().write(FINDINGS, coded_finding(body="<https://www.w3.org/TR/xmlschema-1/#cvc-complex-type>"))
    assert not said_about(package)


def test_reports_nothing_for_a_finding_whose_body_is_the_concept_for_a_schema_failure_w3c_names_no_rule_for(package):
    package.gap_scheme().write(FINDINGS, coded_finding(body="bridge:schemaRuleUnnamed"))
    assert not said_about(package)


def test_reports_nothing_for_a_finding_whose_body_is_the_concept_a_census_carries(package):
    package.gap_scheme().write(FINDINGS, coded_finding(body="bridge:pathNotAccounted"))
    assert not said_about(package)


def test_reports_the_concept_an_address_selecting_other_than_one_node_carries(package):
    package.gap_scheme().write(FINDINGS, coded_finding(body="bridge:addressNotOneNode"))
    assert (
        "https://ns.cascadeprotocol.org/bridge/v1-draft#addressNotOneNode is not a gap of the adapter's "
        "bridge:gapScheme, the anchor of a validation rule in a W3C XML Schema Recommendation, "
        "bridge:schemaRuleUnnamed, or bridge:pathNotAccounted"
    ) in "\n".join(said_about(package))


def test_reports_the_concept_a_census_carries_where_the_adapter_names_no_source_accounting(package):
    package.gap_scheme().write(FINDINGS, coded_finding(body="bridge:pathNotAccounted"))
    package.edit(
        "ro-crate-metadata.json",
        '      "bridge:sourceAccounting": {\n        "@id": "vocab/example-accounting.ttl"\n      },\n',
        "",
    )
    assert (
        "https://ns.cascadeprotocol.org/bridge/v1-draft#pathNotAccounted is not a gap of the adapter's "
        "bridge:gapScheme, the anchor of a validation rule in a W3C XML Schema Recommendation, "
        "or bridge:schemaRuleUnnamed, the adapter naming no bridge:sourceAccounting"
    ) in "\n".join(said_about(package))


def test_reports_a_finding_whose_body_is_the_anchor_of_no_w3c_xml_schema_validation_rule(package):
    package.gap_scheme().write(FINDINGS, coded_finding(body="<https://www.w3.org/TR/xmlschema-1/#cvc-nonesuch>"))
    assert (
        "https://www.w3.org/TR/xmlschema-1/#cvc-nonesuch is not a gap of the adapter's bridge:gapScheme, "
        "the anchor of a validation rule in a W3C XML Schema Recommendation, bridge:schemaRuleUnnamed, "
        "or bridge:pathNotAccounted"
    ) in "\n".join(said_about(package))


def test_reports_a_body_that_is_no_code_with_every_anchor_a_body_may_take(package):
    package.gap_scheme().write(FINDINGS, coded_finding(body="<https://www.w3.org/TR/xmlschema-1/#cvc-nonesuch>"))
    said = "\n".join(said_about(package))
    assert [str(anchor) for anchor in W3C_XML_SCHEMA_RULE_ANCHORS if str(anchor) not in said] == []


def test_reports_a_finding_whose_body_names_a_rule_in_the_recommendation_that_does_not_define_it(package):
    package.gap_scheme().write(FINDINGS, coded_finding(body="<https://www.w3.org/TR/xmlschema-1/#cvc-pattern-valid>"))
    assert (
        "https://www.w3.org/TR/xmlschema-1/#cvc-pattern-valid is not a gap of the adapter's bridge:gapScheme, "
        "the anchor of a validation rule in a W3C XML Schema Recommendation, bridge:schemaRuleUnnamed, "
        "or bridge:pathNotAccounted"
    ) in "\n".join(said_about(package))


def test_reports_nothing_for_a_finding_whose_gap_is_a_value_outside_a_fixed_set_carrying_no_source_value(package):
    package.gap_scheme().write(FINDINGS, coded_finding(body=A_GAP_WHOSE_VALUE_IS_OUTSIDE_A_FIXED_SET))
    assert not said_about(package)


def test_reports_nothing_for_a_finding_carrying_the_source_value_that_made_it_fire_where_its_gap_is_of_another_kind(
    package,
):
    package.gap_scheme().write(FINDINGS, coded_finding(value='"a free-text note"'))
    assert not said_about(package)


def test_reports_nothing_for_a_finding_whose_gap_is_a_value_outside_a_fixed_set_carrying_that_value(package):
    package.gap_scheme().write(
        FINDINGS, coded_finding(body=A_GAP_WHOSE_VALUE_IS_OUTSIDE_A_FIXED_SET, value='"provisional"')
    )
    assert not said_about(package)


def test_reports_nothing_for_a_finding_about_the_document_refined_to_one_element_under_the_document_element(package):
    package.gap_scheme().write(FINDINGS, coded_finding(record="/ExampleRecordSet", refined="ExampleRecord[1]"))
    assert not said_about(package)


def test_reports_a_finding_about_the_document_whose_refinement_selects_no_element(package):
    package.gap_scheme().write(FINDINGS, coded_finding(record="/ExampleRecordSet", refined="Absent"))
    assert said_about(package) == [
        "example-0001: example-0001.ttl: Absent selects no node of example-0001.xml, "
        "where a finding selects exactly one"
    ]


def test_reports_a_finding_about_the_document_whose_refinement_selects_more_than_one_element(package):
    package.gap_scheme().write(FINDINGS, coded_finding(record="/ExampleRecordSet", refined="*"))
    assert said_about(package) == [
        "example-0001: example-0001.ttl: * selects 2 nodes of example-0001.xml, where a finding selects exactly one"
    ]


def output_validation_finding(body, severity="sh:Violation"):
    """A finding about the produced graph: its body the SHACL result's code, pointed at the record, refined no further."""
    return (
        PREFIXES
        + f"""
[] a oa:Annotation ;
  oa:hasTarget [ oa:hasSource <../in/example-0001.xml> ;
                 oa:hasSelector [ a oa:XPathSelector ; rdf:value "/ExampleRecordSet/ExampleRecord[1]" ] ] ;
  oa:hasBody {body} ;
  oa:motivatedBy oa:classifying ;
  sh:resultPath ex:status ;
  sh:focusNode ex:record-1 ;
  sh:resultSeverity {severity} .
"""
    )


def test_reports_nothing_for_a_finding_whose_body_is_the_shacl_constraint_component_that_failed(package):
    package.gap_scheme().write(FINDINGS, output_validation_finding("sh:MinCountConstraintComponent"))
    assert not said_about(package)


def test_reports_nothing_for_a_finding_whose_body_is_the_gap_a_predicate_no_ontology_declares_opens(package):
    package.gap_scheme().write(FINDINGS, output_validation_finding("bridge:predicateNotDeclared"))
    assert not said_about(package)


def test_reports_a_finding_whose_body_is_the_name_of_no_shacl_constraint_component(package):
    package.gap_scheme().write(FINDINGS, output_validation_finding("sh:NonesuchConstraintComponent"))
    assert "http://www.w3.org/ns/shacl#NonesuchConstraintComponent is not a gap of the adapter's" in "\n".join(
        said_about(package)
    )


EXAMPLE_0003 = FIXTURE / "fixtures" / "findings" / "example-0003.ttl"


def test_the_schema_findings_the_synthetic_adapter_expects_are_w3cs_rules_and_the_element_they_were_broken_on():
    committed = Graph().parse(EXAMPLE_0003, format="turtle")
    findings = [
        finding
        for finding in committed.subjects(RDF.type, OA.Annotation)
        if committed.value(finding, SH.resultSeverity) == SH.Violation
    ]
    bodies = {committed.value(finding, OA.hasBody) for finding in findings}
    assert len(set(committed.subjects(RDF.type, OA.Annotation))) == len(findings) == 2
    assert len(bodies) == 2
    assert bodies <= W3C_XML_SCHEMA_RULE_ANCHORS
    assert len({selected_by(committed, finding) for finding in findings}) == 1
