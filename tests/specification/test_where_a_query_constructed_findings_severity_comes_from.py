from pathlib import Path

CONTRACT = " ".join((Path(__file__).resolve().parents[2] / "engine" / "sparql.md").read_text(encoding="utf-8").split())

A_FINDING_A_FINDINGS_QUERY_CONSTRUCTS = "A finding a `bridge:findingsQuery` constructs"


def test_a_finding_a_findings_query_constructs_carries_the_severity_the_query_constructed_for_it():
    assert (
        f"{A_FINDING_A_FINDINGS_QUERY_CONSTRUCTS} carries as its `sh:resultSeverity` the one the query constructed "
        "for it"
    ) in CONTRACT


def test_a_finding_whose_query_constructed_no_severity_carries_the_one_its_gap_concept_declares():
    assert (
        "the `sh:resultSeverity` the gap concept its body names declares where the query constructed none"
    ) in CONTRACT


def test_a_finding_whose_gap_concept_declares_no_severity_carries_sh_info():
    assert (
        "`sh:Info` where that concept declares none, where its body is no concept of the adapter's "
        "`bridge:gapScheme`, or where it carries no body"
    ) in CONTRACT
