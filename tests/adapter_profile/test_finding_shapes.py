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


A_POINTER = "a oa:FragmentSelector ; <http://purl.org/dc/terms/conformsTo> <https://www.rfc-editor.org/rfc/rfc6901>"


class TestTheFormOfAFinding:
    """The form of a finding · shapes/bridge.shapes.ttl

    A finding is a Web Annotation: one body classifying it, one target naming its source and selector, and a severity.
    These are the shapes every findings file is held to, whoever wrote it.
    """

    class TestGivenAFindingsBodyMotivationCountsSeverityAndNode:
        """given a finding's body, motivation, counts, severity and node"""

        def test_rejects_a_finding_whose_body_is_an_oa_textualbody(self):
            """rejects a finding whose body is an `oa:TextualBody`"""
            assert (
                "A finding carries exactly one oa:hasBody, an IRI: the code the finding is an instance of, never a sentence."
            ) in said_about_findings(a_finding(body='[ a oa:TextualBody ; rdf:value "no term for a free-text note" ]'))

        def test_rejects_a_finding_whose_body_is_a_literal(self):
            assert (
                "A finding carries exactly one oa:hasBody, an IRI: the code the finding is an instance of, never a sentence."
            ) in said_about_findings(a_finding(body='"no term for a free-text note"'))

        def test_rejects_a_finding_carrying_two_bodies(self):
            assert (
                "A finding carries exactly one oa:hasBody, an IRI: the code the finding is an instance of, never a sentence."
            ) in said_about_findings(
                a_finding(body="ex:no-term-for-a-free-text-note, ex:a-status-outside-the-set-the-vocabulary-fixes")
            )

        def test_rejects_a_finding_carrying_no_motivation(self):
            assert "A finding carries exactly one oa:motivatedBy, oa:classifying." in said_about_findings(
                a_finding(motivation=None)
            )

        def test_rejects_a_finding_motivated_by_something_other_than_classifying(self):
            assert "A finding carries exactly one oa:motivatedBy, oa:classifying." in said_about_findings(
                a_finding(motivation="oa:commenting")
            )

        def test_rejects_a_finding_carrying_two_motivations(self):
            assert "A finding carries exactly one oa:motivatedBy, oa:classifying." in said_about_findings(
                a_finding(motivation="oa:classifying, oa:commenting")
            )

        def test_rejects_a_finding_carrying_two_source_values(self):
            assert "A finding carries at most one sh:value, what in the source it is about." in said_about_findings(
                a_finding(value='"clinically significant", "uncertain"')
            )

        def test_accepts_a_finding_whose_body_is_an_iri_classifying_it_and_the_source_value_that_made_it_fire(self):
            """accepts a finding whose body is an IRI classifying it and the source value that made it fire"""
            assert not said_about_findings(a_finding(value='"clinically significant"'))

        def test_rejects_a_finding_carrying_two_occurrence_counts(self):
            assert "cascade:occurrenceCount" in said_about_findings(a_finding(occurrences="2, 3"))
            assert not said_about_findings(a_finding(occurrences="2"))

        def test_rejects_a_finding_whose_occurrence_count_is_no_integer(self):
            assert "cascade:occurrenceCount" in said_about_findings(a_finding(occurrences='"two"'))
            assert not said_about_findings(a_finding(occurrences="297"))

        def test_rejects_a_finding_whose_occurrence_count_is_one_where_a_count_of_one_is_written_by_omitting_it(self):
            assert "cascade:occurrenceCount" in said_about_findings(a_finding(occurrences="1"))
            assert not said_about_findings(a_finding())

        def test_rejects_a_finding_with_no_severity(self):
            assert "carries exactly one sh:resultSeverity" in said_about_findings(a_finding(severity=None))

        def test_rejects_a_severity_outside_the_scale(self):
            assert "sh:Info, sh:Warning, sh:Violation" in said_about_findings(
                a_finding(severity="<https://example.org/synthetic-adapter/severe>")
            )

        def test_rejects_a_finding_named_rather_than_written_for_itself(self):
            assert "A finding is a blank node written for that one finding" in said_about_findings(
                a_finding().replace("[] a oa:Annotation", "<#the-one-finding> a oa:Annotation")
            )

    class TestGivenAFindingsTargetAndSelector:
        """given a finding's target and selector"""

        def test_rejects_a_finding_with_no_selector(self):
            assert "carries exactly one oa:hasSelector" in said_about_findings(a_finding(record=None))

        def test_rejects_two_findings_sharing_one_selector(self):
            assert "selector of its own, shared with no other finding" in said_about_findings(
                TWO_FINDINGS_SHARING_ONE_SELECTOR
            )

        def test_rejects_two_findings_sharing_one_target(self):
            assert "a target of its own, shared with no other finding" in said_about_findings(
                TWO_FINDINGS_SHARING_ONE_TARGET
            )

        def test_rejects_a_finding_carrying_more_than_one_target(self):
            assert "A finding about the source document carries exactly one oa:hasTarget" in said_about_findings(
                A_FINDING_WITH_TWO_TARGETS
            )

        def test_rejects_a_target_naming_its_source_as_a_literal_rather_than_by_iri(self):
            """rejects a target naming its source as a literal rather than by IRI"""
            assert (
                "A finding's target names exactly one oa:hasSource by IRI, the document the record was read from."
            ) in said_about_findings(a_finding(source='"example-0001.xml"'))

        def test_rejects_a_record_selector_that_is_not_an_xpath_selector(self):
            """rejects a record selector that is not an XPath selector"""
            assert (
                "A record's selector is an oa:XPathSelector, or an oa:FragmentSelector whose dcterms:conformsTo is JSON Pointer"
                in said_about_findings(
                    a_finding(selector='[ a oa:TextQuoteSelector ; rdf:value "/ExampleRecordSet/ExampleRecord[1]" ]')
                )
            )

        def test_rejects_a_record_selector_carrying_no_xpath(self):
            """rejects a record selector carrying no XPath"""
            assert (
                "A selector carries exactly one rdf:value, its XPath or its JSON Pointer, a string."
                in said_about_findings(a_finding(selector="[ a oa:XPathSelector ]"))
            )

        def test_rejects_a_record_selector_refined_more_than_once(self):
            assert "A record's selector is refined by at most one selector" in said_about_findings(
                a_finding(
                    selector=(
                        '[ a oa:XPathSelector ; rdf:value "/ExampleRecordSet/ExampleRecord[1]" ; '
                        'oa:refinedBy [ a oa:XPathSelector ; rdf:value "Label" ] ; '
                        'oa:refinedBy [ a oa:XPathSelector ; rdf:value "Note" ] ]'
                    )
                )
            )

        def test_rejects_a_refinement_that_is_not_an_xpath_selector(self):
            """rejects a refinement that is not an XPath selector"""
            assert (
                "A selector refining a record's selector is an oa:XPathSelector, or an oa:FragmentSelector"
                in said_about_findings(
                    a_finding(
                        selector='[ a oa:XPathSelector ; rdf:value "/ExampleRecordSet/ExampleRecord[1]" ; oa:refinedBy [ a oa:TextQuoteSelector ; rdf:value "Note" ] ]'
                    )
                )
            )

        def test_rejects_a_refinement_refined_further(self):
            assert "A selector refining a record's selector is refined no further." in said_about_findings(
                a_finding(
                    selector=(
                        '[ a oa:XPathSelector ; rdf:value "/ExampleRecordSet/ExampleRecord[1]" ; '
                        'oa:refinedBy [ a oa:XPathSelector ; rdf:value "Note" ; '
                        'oa:refinedBy [ a oa:XPathSelector ; rdf:value "text()" ] ] ]'
                    )
                )
            )

        def test_accepts_a_record_selector_and_a_refinement_that_are_json_pointers(self):
            """accepts a record selector and a refinement that are JSON pointers"""
            assert not said_about_findings(
                a_finding(
                    selector=f'[ {A_POINTER} ; rdf:value "/records/0" ; oa:refinedBy [ {A_POINTER} ; rdf:value "/note" ] ]'
                )
            )

        def test_rejects_a_fragment_selector_conforming_to_no_json_pointer(self):
            """rejects a fragment selector conforming to no JSON pointer"""
            assert "whose dcterms:conformsTo is JSON Pointer" in said_about_findings(
                a_finding(selector='[ a oa:FragmentSelector ; rdf:value "/records/0" ]')
            )

        def test_rejects_a_refinement_of_another_kind_than_the_selector_it_refines(self):
            assert "A selector refining a record's selector is of its kind" in said_about_findings(
                a_finding(
                    selector=f'[ {A_POINTER} ; rdf:value "/records/0" ; oa:refinedBy [ a oa:XPathSelector ; rdf:value "Note" ] ]'
                )
            )
