def test_a_bridge_refuses_to_prepare_an_adapter_whose_query_holds_a_service_pattern_and_fetches_nothing(
    sparql_contract,
):
    assert (
        "A Bridge refuses to prepare an adapter one of whose queries holds a `SERVICE` pattern anywhere, "
        "and fetches nothing." in sparql_contract
    )
