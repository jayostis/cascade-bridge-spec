from adapter_profile_world import a_finding, said_about_findings


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
