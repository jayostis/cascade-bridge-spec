def test_a_bridge_refuses_to_prepare_an_adapter_whose_query_holds_a_service_pattern_or_a_dataset_clause(
    sparql_contract,
):
    assert (
        "A Bridge refuses to prepare an adapter one of whose queries holds a `SERVICE` pattern anywhere "
        "or a `FROM` or `FROM NAMED` clause, and fetches nothing." in sparql_contract
    )
