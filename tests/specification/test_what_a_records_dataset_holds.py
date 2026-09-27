from pathlib import Path

STAGES = " ".join((Path(__file__).resolve().parents[2] / "engine" / "stages.md").read_text(encoding="utf-8").split())


def test_a_records_dataset_holds_the_supplied_facts_the_documents_sha256_and_the_records_selector(sparql_contract):
    assert (
        "the facts supplied with the document, with `bridge:serverBaseUrl` normalised, "
        "`bridge:thisDocument bridge:sha256` the document's SHA-256, and `bridge:thisRecord bridge:selector` the "
        "`rdf:value` of the record's selector" in sparql_contract
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
        "`bridge:arrivedAs`, and `bridge:arrivedAs` the version's name, `prov:wasDerivedFrom` the document, "
        "`prov:wasGeneratedBy` the import and, where the mapping wrote none, `bridge:selector` the `rdf:value` of "
        "the source record's selector" in STAGES
    )


def test_the_arrival_of_a_record_inside_the_source_record_selects_that_records_own_node():
    assert (
        "For a record it finds inside the source record, as a FHIR contained resource is, it writes there "
        "`bridge:selector` as the `rdf:value` of the selector that record would have as a source record of its own"
        in STAGES
    )


def test_a_bundle_entry_named_by_its_urn_uuid_full_url_is_so_named_whether_a_server_is_known_or_not(
    sparql_contract,
):
    assert (
        "| a FHIR Bundle entry with no `id` and a `urn:uuid` `fullUrl`, whether a server is known or not | the "
        "`fullUrl` |" in sparql_contract
    )


def test_a_record_without_a_usable_id_is_named_by_its_documents_sha256_and_its_selectors_value(sparql_contract):
    assert (
        "a FHIR resource with an `id` and no known server | the document's SHA-256 and the `rdf:value` of the "
        "record's selector |" in sparql_contract
    )


def test_an_arrivals_version_id_is_a_plain_string_and_its_last_update_the_sources_own_text():
    assert (
        "its version id as `pav:version`, a plain string, and when it was last updated as `pav:lastUpdateOn`, an "
        "`xsd:dateTime` whose lexical form is the source's text as written" in STAGES
    )


def test_a_reference_relative_to_an_unknown_server_names_no_record_and_is_reported(sparql_contract):
    assert (
        "A reference relative to a server, as FHIR's `Patient/123` is, in a document with no known server names no "
        "record: a mapping writes no link for it, and the adapter reports it as a finding." in sparql_contract
    )
