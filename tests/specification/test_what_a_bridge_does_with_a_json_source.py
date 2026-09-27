from pathlib import Path

STAGES = " ".join((Path(__file__).resolve().parents[2] / "engine" / "stages.md").read_text(encoding="utf-8").split())


def test_a_json_record_is_an_object_its_envelopes_record_path_selects(sparql_contract):
    assert (
        "A record of a JSON document is an object the `bridge:jsonPathOfEachRecord` of the envelope it is read in "
        "selects, in document order; a value it selects that is not an object is no record." in sparql_contract
    )


def test_a_record_path_is_a_subset_of_rfc_9535(sparql_contract):
    assert (
        "made only of `$` followed by any sequence of child segments, each a name selector, written `.name` or "
        "`['name']`, or the wildcard `[*]`" in sparql_contract
    )


def test_the_json_skeleton_keeps_a_records_scalar_members(sparql_contract):
    assert (
        "every record is lifted with its place among its parent's members or items and its members whose value is "
        "a string, a number, `true` or `false`, and without its members whose value is an object or an array"
        in sparql_contract
    )


def test_a_json_envelope_admits_a_document_by_a_member_of_its_root_object(sparql_contract):
    assert (
        "a JSON document whose value is an object with a member named its `bridge:docRootMemberName`, whose value, "
        "where the envelope names a `bridge:docRootMemberValue`, is a string, number, `true` or `false` the lift "
        "writes as that value" in sparql_contract
    )


def test_a_json_selector_is_a_json_pointer_through_a_fragment_selector(sparql_contract):
    assert (
        "In a JSON document, a record's selector is an `oa:FragmentSelector` whose `dcterms:conformsTo` is "
        "`<https://www.rfc-editor.org/rfc/rfc6901>`" in sparql_contract
    )
    assert "in its URI fragment identifier representation without the `#`" in sparql_contract


def test_a_finding_about_a_json_document_selects_its_value_by_the_empty_pointer(sparql_contract):
    assert (
        "Where a finding selects the document element, in a JSON document it selects the document's value, by the "
        "empty pointer." in sparql_contract
    )


def test_a_json_path_is_member_names_as_pointer_tokens_with_no_position(sparql_contract):
    assert (
        "In a JSON record, a path is the names of the members from the record down to the node, each written as a "
        "JSON Pointer reference token after a `/`, `~` as `~0` and `/` as `~1`. An array is no node of a path: its "
        "items stand at its path, so no step carries a position." in sparql_contract
    )


def test_a_json_schema_finding_names_the_draft_06_section_of_the_keyword_failed(sparql_contract):
    assert (
        "`https://datatracker.ietf.org/doc/html/draft-wright-json-schema-validation-01#section-6.17`" in sparql_contract
    )
    assert "Draft-06 is the only draft specified, and `format` is not asserted." in sparql_contract


def test_a_keyword_failing_only_through_a_subschema_is_not_the_finding(sparql_contract):
    assert "`anyOf`, `oneOf`, `not` and `contains` fail as themselves." in sparql_contract


def test_a_json_schemas_ref_fetches_nothing():
    assert (
        "A JSON Schema's `$ref` resolves as its draft says**, against the schema's `$id` or, where it declares "
        "none, its own IRI, and only within the schema or to files in the adapter package. Nothing is fetched."
        in STAGES
    )
