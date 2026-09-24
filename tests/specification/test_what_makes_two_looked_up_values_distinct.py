def test_a_value_is_distinguished_by_its_spelling_rather_than_by_the_key_it_is_looked_up_by(sparql_contract):
    assert "Values are distinct by spelling, not by key" in sparql_contract


def test_one_key_spelled_two_ways_is_two_findings_each_carrying_its_own_spelling_and_its_own_count(sparql_contract):
    assert (
        "a key spelled two ways is two findings, each carrying its own spelling and counting only the nodes that hold it"
    ) in sparql_contract


def test_a_key_is_what_sparqls_lcase_and_stripping_the_whitespace_the_lift_names_give(sparql_contract):
    assert (
        "A value's key is the value under SPARQL's `LCASE`, stripped of leading and trailing XML whitespace"
        in sparql_contract
    )
    assert "Whitespace is XML's `S` production, and no other character." in sparql_contract
