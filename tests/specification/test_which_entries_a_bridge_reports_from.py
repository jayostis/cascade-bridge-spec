from pathlib import Path

CONTRACT = " ".join((Path(__file__).resolve().parents[2] / "engine" / "sparql.md").read_text(encoding="utf-8").split())

THE_VERDICT = (
    "A Bridge reports from an entry whose verdict is `bridge:carriedInPart` or `bridge:noHome`, and from no other."
)

THE_KIND = (
    "A gap of kind `bridge:noPredicate` or `bridge:sourceLacksRequired` is true of the path, and the entry naming it "
    "reports it. A gap of kind `bridge:carriedWithLoss`, `bridge:valueNotMapped` or `bridge:schemaRuleUnnamed` is "
    "true of what a record holds at the path, which an entry cannot name, and reports nothing."
)


def test_a_bridge_reports_from_an_entry_whose_verdict_is_carried_in_part_or_no_home():
    assert THE_VERDICT in CONTRACT


def test_a_bridge_reports_a_gap_of_a_kind_true_of_the_path():
    assert THE_KIND in CONTRACT


def test_the_verdict_and_the_kind_are_stated_as_the_pair_a_bridge_applies():
    assert f"{THE_VERDICT} {THE_KIND}" in CONTRACT
