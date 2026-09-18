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


def test_evaluates_no_selector_for_an_entry_naming_no_input(crate):
    for test in crate.entries:
        crate.graph.remove((crate.graph.value(test, MF.action), BRIDGE.input, None))
    assert not [message for message in expected_findings.faulty(crate) if "selects" in message]
