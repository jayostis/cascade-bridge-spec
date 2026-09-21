from pathlib import Path

CONTRACT = " ".join((Path(__file__).resolve().parents[2] / "engine" / "sparql.md").read_text(encoding="utf-8").split())


def test_a_value_is_distinguished_by_its_spelling_rather_than_by_the_key_it_is_looked_up_by():
    assert "Values are distinct by spelling, not by key" in CONTRACT


def test_one_key_spelled_two_ways_is_two_findings_each_carrying_its_own_spelling_and_its_own_count():
    assert (
        "a key spelled two ways is two findings, each carrying its own spelling and counting only the nodes that hold it"
    ) in CONTRACT


def test_a_key_is_what_sparqls_lcase_and_stripping_the_whitespace_the_lift_names_give():
    assert "A value's key is the value under SPARQL's `LCASE`, stripped of leading and trailing whitespace" in CONTRACT
    assert "Whitespace is XML's `S` production, and no other character." in CONTRACT
