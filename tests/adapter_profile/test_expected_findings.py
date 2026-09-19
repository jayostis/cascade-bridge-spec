import expected_findings
from _terms import BRIDGE, MF

FINDINGS = "fixtures/findings/example-0001.ttl"

PREFIXES = """@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix sh:  <http://www.w3.org/ns/shacl#> .
@prefix oa:  <http://www.w3.org/ns/oa#> .
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
    body="no term for a free-text note",
    severity="sh:Info",
):
    target = [f"oa:hasSource {source}"]
    if record is not None:
        refinement = "" if refined is None else f' ; oa:refinedBy [ a oa:XPathSelector ; rdf:value "{refined}" ]'
        target.append(f'oa:hasSelector [ a oa:XPathSelector ; rdf:value "{record}"{refinement} ]')
    annotation = ["[] a oa:Annotation", f"oa:hasTarget [ {' ; '.join(target)} ]"]
    if body is not None:
        annotation.append(f'oa:hasBody [ a oa:TextualBody ; rdf:value "{body}" ]')
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
        finding(record="/ExampleRecordSet/ExampleRecord[2]", refined="/ExampleRecordSet/ExampleRecord[1]/Note"),
    )
    assert (
        "/ExampleRecordSet/ExampleRecord[1]/Note selects a node of example-0001.xml outside "
        "/ExampleRecordSet/ExampleRecord[2], where a refinement selects a node of the record"
    ) in "\n".join(expected_findings.faulty(package.crate))


def test_reports_nothing_for_a_refined_selector_that_names_its_own_record_from_the_document_root(package):
    package.write(
        FINDINGS,
        finding(record="/ExampleRecordSet/ExampleRecord[2]", refined="/ExampleRecordSet/ExampleRecord[2]/Note"),
    )
    assert not list(expected_findings.faulty(package.crate))


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


def test_reports_a_record_selector_that_selects_the_document_element_rather_than_a_record(package):
    package.write(FINDINGS, finding(record="/ExampleRecordSet", refined=None))
    assert (
        "/ExampleRecordSet selects ExampleRecordSet of example-0001.xml, where a record's selector selects "
        "ExampleRecord, the adapter's bridge:elementNameOfEachRecord"
    ) in "\n".join(expected_findings.faulty(package.crate))


def test_reports_a_record_selector_that_selects_an_element_inside_a_record(package):
    package.write(FINDINGS, finding(record="/ExampleRecordSet/ExampleRecord[1]/Label", refined=None))
    assert (
        "selects Label of example-0001.xml, where a record's selector selects "
        "ExampleRecord, the adapter's bridge:elementNameOfEachRecord"
    ) in "\n".join(expected_findings.faulty(package.crate))


def test_holds_a_record_selector_to_no_element_name_when_the_adapter_declares_none(package):
    package.write(FINDINGS, finding(record="/ExampleRecordSet", refined=None))
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


def test_reports_a_record_selector_that_names_its_record_another_way(package):
    package.write(FINDINGS, finding(record="/ExampleRecordSet/*[local-name()='ExampleRecord'][1]"))
    assert (
        "selects the record /ExampleRecordSet/ExampleRecord[1] names, where a record's selector "
        "is the XPath from the document element to the record"
    ) in "\n".join(expected_findings.faulty(package.crate))
