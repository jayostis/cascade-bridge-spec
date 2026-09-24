from adapter_profile_world import a_finding, said_about_findings

TWO_FINDINGS_SHARING_ONE_SELECTOR = """
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

TWO_FINDINGS_SHARING_ONE_TARGET = """
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

A_FINDING_WITH_TWO_TARGETS = """
[] a oa:Annotation ;
  oa:hasTarget [ oa:hasSource <../in/example-0001.xml> ;
                 oa:hasSelector [ a oa:XPathSelector ; rdf:value "/ExampleRecordSet/ExampleRecord[1]" ] ] ;
  oa:hasTarget [ oa:hasSource <../in/example-0001.xml> ;
                 oa:hasSelector [ a oa:XPathSelector ; rdf:value "/ExampleRecordSet/ExampleRecord[2]" ] ] ;
  oa:hasBody [ a oa:TextualBody ; rdf:value "no term for a free-text note" ] ;
  sh:resultSeverity sh:Info .
"""


def test_rejects_a_finding_whose_body_is_an_oa_textual_body():
    assert (
        "A finding carries exactly one oa:hasBody, an IRI: the code the finding is an instance of, never a sentence."
    ) in said_about_findings(a_finding(body='[ a oa:TextualBody ; rdf:value "no term for a free-text note" ]'))


def test_rejects_a_finding_whose_body_is_a_literal():
    assert (
        "A finding carries exactly one oa:hasBody, an IRI: the code the finding is an instance of, never a sentence."
    ) in said_about_findings(a_finding(body='"no term for a free-text note"'))


def test_rejects_a_finding_carrying_two_bodies():
    assert (
        "A finding carries exactly one oa:hasBody, an IRI: the code the finding is an instance of, never a sentence."
    ) in said_about_findings(
        a_finding(body="ex:no-term-for-a-free-text-note, ex:a-status-outside-the-set-the-vocabulary-fixes")
    )


def test_rejects_a_finding_carrying_no_motivation():
    assert "A finding carries exactly one oa:motivatedBy, oa:classifying." in said_about_findings(
        a_finding(motivation=None)
    )


def test_rejects_a_finding_motivated_by_something_other_than_classifying():
    assert "A finding carries exactly one oa:motivatedBy, oa:classifying." in said_about_findings(
        a_finding(motivation="oa:commenting")
    )


def test_rejects_a_finding_carrying_two_motivations():
    assert "A finding carries exactly one oa:motivatedBy, oa:classifying." in said_about_findings(
        a_finding(motivation="oa:classifying, oa:commenting")
    )


def test_rejects_a_finding_carrying_two_source_values():
    assert "A finding carries at most one sh:value, what in the source it is about." in said_about_findings(
        a_finding(value='"clinically significant", "uncertain"')
    )


def test_accepts_a_finding_whose_body_is_an_iri_classifying_it_and_the_source_value_that_made_it_fire():
    assert not said_about_findings(a_finding(value='"clinically significant"'))


def test_rejects_a_finding_carrying_two_occurrence_counts():
    assert "bridge:occurrences" in said_about_findings(a_finding(occurrences="2, 3"))
    assert not said_about_findings(a_finding(occurrences="2"))


def test_rejects_a_finding_whose_occurrence_count_is_no_integer():
    assert "bridge:occurrences" in said_about_findings(a_finding(occurrences='"two"'))
    assert not said_about_findings(a_finding(occurrences="297"))


def test_rejects_a_finding_whose_occurrence_count_is_one_where_a_count_of_one_is_written_by_omitting_it():
    assert "bridge:occurrences" in said_about_findings(a_finding(occurrences="1"))
    assert not said_about_findings(a_finding())


def test_rejects_a_finding_with_no_selector():
    assert "carries exactly one oa:hasSelector" in said_about_findings(a_finding(record=None))


def test_rejects_a_finding_with_no_severity():
    assert "carries exactly one sh:resultSeverity" in said_about_findings(a_finding(severity=None))


def test_rejects_a_severity_outside_the_scale():
    assert "sh:Info, sh:Warning, sh:Violation" in said_about_findings(
        a_finding(severity="<https://example.org/synthetic-adapter/severe>")
    )


def test_rejects_two_findings_sharing_one_selector():
    assert "selector of its own, shared with no other finding" in said_about_findings(TWO_FINDINGS_SHARING_ONE_SELECTOR)


def test_rejects_two_findings_sharing_one_target():
    assert "a target of its own, shared with no other finding" in said_about_findings(TWO_FINDINGS_SHARING_ONE_TARGET)


def test_rejects_a_finding_carrying_more_than_one_target():
    assert "A finding about the source document carries exactly one oa:hasTarget" in said_about_findings(
        A_FINDING_WITH_TWO_TARGETS
    )


def test_rejects_a_target_naming_its_source_as_a_literal_rather_than_by_iri():
    assert (
        "A finding's target names exactly one oa:hasSource by IRI, the document the record was read from."
    ) in said_about_findings(a_finding(source='"example-0001.xml"'))


def test_rejects_a_finding_named_rather_than_written_for_itself():
    assert "A finding is a blank node written for that one finding" in said_about_findings(
        a_finding().replace("[] a oa:Annotation", "<#the-one-finding> a oa:Annotation")
    )


def test_rejects_a_record_selector_that_is_not_an_xpath_selector():
    assert "A record's selector is an oa:XPathSelector." in said_about_findings(
        a_finding(selector='[ a oa:TextQuoteSelector ; rdf:value "/ExampleRecordSet/ExampleRecord[1]" ]')
    )


def test_rejects_a_record_selector_carrying_no_xpath():
    assert "A selector carries exactly one rdf:value, its XPath, a string." in said_about_findings(
        a_finding(selector="[ a oa:XPathSelector ]")
    )


def test_rejects_a_record_selector_refined_more_than_once():
    assert "A record's selector is refined by at most one selector" in said_about_findings(
        a_finding(
            selector=(
                '[ a oa:XPathSelector ; rdf:value "/ExampleRecordSet/ExampleRecord[1]" ; '
                'oa:refinedBy [ a oa:XPathSelector ; rdf:value "Label" ] ; '
                'oa:refinedBy [ a oa:XPathSelector ; rdf:value "Note" ] ]'
            )
        )
    )


def test_rejects_a_refinement_that_is_not_an_xpath_selector():
    assert "A selector refining a record's selector is an oa:XPathSelector." in said_about_findings(
        a_finding(
            selector='[ a oa:XPathSelector ; rdf:value "/ExampleRecordSet/ExampleRecord[1]" ; oa:refinedBy [ a oa:TextQuoteSelector ; rdf:value "Note" ] ]'
        )
    )


def test_rejects_a_refinement_refined_further():
    assert "A selector refining a record's selector is refined no further." in said_about_findings(
        a_finding(
            selector=(
                '[ a oa:XPathSelector ; rdf:value "/ExampleRecordSet/ExampleRecord[1]" ; '
                'oa:refinedBy [ a oa:XPathSelector ; rdf:value "Note" ; '
                'oa:refinedBy [ a oa:XPathSelector ; rdf:value "text()" ] ] ]'
            )
        )
    )
