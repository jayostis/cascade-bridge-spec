from pathlib import Path

CONTRACT = " ".join((Path(__file__).resolve().parents[2] / "engine" / "sparql.md").read_text(encoding="utf-8").split())

A_KIND_TRUE_OF_THE_PATH = "A gap of kind `bridge:noPredicate` or `bridge:sourceLacksRequired` is true of the path"
A_KIND_TRUE_OF_WHAT_A_RECORD_HOLDS = (
    "A gap of kind `bridge:carriedWithLoss`, `bridge:valueNotMapped` or `bridge:schemaRuleUnnamed` is true of what a "
    "record holds"
)


def test_a_bridge_reports_from_an_entry_whose_verdict_is_carried_in_part_or_no_home_and_from_no_other():
    assert "verdict is `bridge:carriedInPart` or `bridge:noHome`, and from no other" in CONTRACT


def test_a_gap_of_a_kind_true_of_the_path_is_reported_by_the_entry_naming_it():
    assert f"{A_KIND_TRUE_OF_THE_PATH}, and the entry naming it reports it" in CONTRACT


def test_a_gap_of_a_kind_true_of_what_a_record_holds_is_reported_by_no_verdict():
    assert A_KIND_TRUE_OF_WHAT_A_RECORD_HOLDS in CONTRACT
    assert "which a verdict cannot name, and reports nothing" in CONTRACT


def test_an_entrys_lookup_is_read_whatever_its_verdict_is():
    assert "are read whatever its verdict is" in CONTRACT


def test_the_step_that_emits_a_finding_from_an_entry_applies_the_verdict_test_and_the_kind_test():
    assert "carries a verdict a Bridge reports from and names a gap of a kind that reports" in CONTRACT


def test_a_gaps_kind_is_read_from_the_skos_broader_its_concept_declares():
    assert "A gap's kind is the `skos:broader` its concept declares" in CONTRACT
