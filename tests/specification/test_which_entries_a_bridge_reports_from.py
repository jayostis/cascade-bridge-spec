A_KIND_TRUE_OF_THE_PATH = "A gap of kind `bridge:noPredicate` or `bridge:sourceLacksRequired` is true of the path"
A_KIND_TRUE_OF_WHAT_A_RECORD_HOLDS = (
    "A gap of kind `bridge:carriedWithLoss`, `bridge:valueNotMapped` or `bridge:schemaRuleUnnamed` is true of what a "
    "record holds"
)


def test_a_bridge_reports_from_an_entry_whose_verdict_is_carried_in_part_or_no_home_and_from_no_other(sparql_contract):
    assert "verdict is `bridge:carriedInPart` or `bridge:noHome`, and from no other" in sparql_contract


def test_a_gap_of_a_kind_true_of_the_path_is_reported_by_the_entry_naming_it(sparql_contract):
    assert f"{A_KIND_TRUE_OF_THE_PATH}, and the entry naming it reports it" in sparql_contract


def test_a_gap_of_a_kind_true_of_what_a_record_holds_is_reported_by_no_verdict(sparql_contract):
    assert A_KIND_TRUE_OF_WHAT_A_RECORD_HOLDS in sparql_contract
    assert "which a verdict cannot name, and reports nothing" in sparql_contract


def test_an_entrys_lookup_is_read_whatever_its_verdict_is(sparql_contract):
    assert "are read whatever its verdict is" in sparql_contract


def test_the_step_that_emits_a_finding_from_an_entry_applies_the_verdict_test_and_the_kind_test(sparql_contract):
    assert "carries a verdict a Bridge reports from and names a gap of a kind that reports" in sparql_contract


def test_a_gaps_kind_is_read_from_the_skos_broader_its_concept_declares(sparql_contract):
    assert "A gap's kind is the `skos:broader` its concept declares" in sparql_contract
