from adapter_profile_world import an_output_validation_finding, said_about_findings


class TestTheFormOfAFinding:
    """The form of a finding · shapes/bridge.shapes.ttl

    A finding is a Web Annotation: one body classifying it, one target naming its source and selector, and a severity.
    These are the shapes every findings file is held to, whoever wrote it.
    """

    class TestGivenAFindingFromValidatingABridgesOutput:
        """given a finding from validating a Bridge's output"""

        def test_takes_as_its_focus_node_the_iri_of_the_node_that_broke_never_a_blank_node(self):
            """takes as its focus node the IRI of the node that broke, never a blank node"""
            assert not said_about_findings(an_output_validation_finding())
            assert "sh:focusNode" in said_about_findings(an_output_validation_finding(focus="[ a ex:Record ]"))

        def test_carries_a_target_and_a_selector_of_its_own_refined_no_further_where_two_are_about_one_record(self):
            """carries a target and a selector of its own, refined no further, where two are about one record"""
            assert not said_about_findings(
                an_output_validation_finding(path="ex:status"), an_output_validation_finding(path="ex:label")
            )
            assert "refined no further" in said_about_findings(an_output_validation_finding(refined="Status"))

        def test_names_an_undeclared_predicate_as_its_result_path_at_sh_violation(self):
            """names an undeclared predicate as its result path, at `sh:Violation`"""
            assert not said_about_findings(
                an_output_validation_finding(body="bridge:predicateNotDeclared", path="ex:sourceRecordId")
            )
            assert "sh:resultPath" in said_about_findings(
                an_output_validation_finding(body="bridge:predicateNotDeclared", path=None)
            )
            assert "sh:Violation" in said_about_findings(
                an_output_validation_finding(body="bridge:predicateNotDeclared", severity="sh:Info")
            )
