from pathlib import Path

STAGES = " ".join((Path(__file__).resolve().parents[2] / "engine" / "stages.md").read_text(encoding="utf-8").split())


def test_a_records_dataset_holds_the_supplied_facts_the_documents_sha256_and_the_records_selector(sparql_contract):
    assert (
        "the facts supplied with the document, with `bridge:serverBaseUrl` normalised, "
        "`bridge:thisDocument bridge:sha256` the document's SHA-256, and `bridge:thisRecord bridge:selector` the "
        "record's selector" in sparql_contract
    )


def test_a_records_dataset_holds_what_the_document_table_query_constructs_over_every_record_of_its_document(
    sparql_contract,
):
    assert (
        "the document table: the RDF merge, over every record of the document, of the graph each "
        "`bridge:documentTableQuery` constructs over that record's dataset" in sparql_contract
    )


def test_a_records_selector_numbers_every_step_below_the_document_element(sparql_contract):
    assert (
        "A record's selector is written `/` and the document element's step, then, for each element from the "
        "document element's child down to the record, `/`, its step and `[n]`" in sparql_contract
    )


def test_a_bridges_graph_is_a_function_of_the_document_and_the_facts_supplied_with_it():
    assert (
        "A Bridge's graph is a function of the document and the facts supplied with it**, and of nothing a pod holds."
        in STAGES
    )


def test_a_reference_to_a_record_not_in_the_document_is_never_dropped():
    assert (
        "A reference to a record not in the document is its computed name**, which resolves when that record "
        "arrives. Nothing is dropped." in STAGES
    )


def test_the_idempotent_receiver_is_the_pod_writers_re_import_checks():
    assert (
        "a pod writer's re-import checks (the same document, the same source version, the same version as the current one) make it one"
        in STAGES
    )


def test_the_document_carries_every_supplied_fact_under_its_sha256():
    assert "**the document**: its SHA-256 as its name, `a prov:Entity`, and every supplied fact" in STAGES


def test_a_versions_arrival_is_completed_by_the_bridge_from_what_the_mapping_linked_to_it():
    assert (
        "one blank node carrying every triple the mapping wrote of a node it linked to that version by "
        "`bridge:arrivedAs`, and `bridge:arrivedAs` the version's name, `bridge:selector` its record's selector, "
        "`prov:wasDerivedFrom` the document and `prov:wasGeneratedBy` the import" in STAGES
    )
