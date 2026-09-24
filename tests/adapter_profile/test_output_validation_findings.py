from adapter_profile_world import an_output_validation_finding, said_about_findings


def test_a_findings_focus_node_is_the_iri_of_the_node_that_broke_and_never_a_blank_node():
    assert not said_about_findings(an_output_validation_finding())
    assert "sh:focusNode" in said_about_findings(an_output_validation_finding(focus="[ a ex:Record ]"))


def test_two_findings_about_one_record_carry_a_target_and_a_selector_of_their_own_refined_no_further():
    assert not said_about_findings(
        an_output_validation_finding(path="ex:status"), an_output_validation_finding(path="ex:label")
    )
    assert "refined no further" in said_about_findings(an_output_validation_finding(refined="Status"))


def test_an_undeclared_predicate_finding_names_the_predicate_as_its_result_path_at_sh_violation():
    assert not said_about_findings(
        an_output_validation_finding(body="bridge:predicateNotDeclared", path="ex:sourceRecordId")
    )
    assert "sh:resultPath" in said_about_findings(
        an_output_validation_finding(body="bridge:predicateNotDeclared", path=None)
    )
    assert "sh:Violation" in said_about_findings(
        an_output_validation_finding(body="bridge:predicateNotDeclared", severity="sh:Info")
    )
