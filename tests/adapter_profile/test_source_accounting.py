from rdflib import URIRef

import source_accounting
from _terms import BRIDGE

PREFIXES = """@prefix bridge: <https://ns.cascadeprotocol.org/bridge/v1-draft#> .
@prefix ex:     <https://example.org/synthetic-adapter/v1#> .
"""

A_SCHEME_HOLDING_A_GAP_OF_EACH_KIND_A_VERDICT_IMPLIES = """@prefix skos:   <http://www.w3.org/2004/02/skos/core#> .
@prefix bridge: <https://ns.cascadeprotocol.org/bridge/v1-draft#> .
@prefix ex:     <https://example.org/synthetic-adapter/v1#> .

ex:gaps a skos:ConceptScheme .

ex:no-term-for-a-free-text-note a skos:Concept ;
  skos:prefLabel "no term for a free-text note" ;
  skos:inScheme ex:gaps ;
  skos:broader bridge:noPredicate .

ex:only-the-first-note-is-carried a skos:Concept ;
  skos:prefLabel "only the first note is carried" ;
  skos:inScheme ex:gaps ;
  skos:broader bridge:carriedWithLoss .

ex:a-status-outside-the-set-the-vocabulary-fixes a skos:Concept ;
  skos:prefLabel "a status outside the set the vocabulary fixes" ;
  skos:inScheme ex:gaps ;
  skos:broader bridge:valueNotMapped .

ex:no-source-for-the-curation-date-a-shape-requires a skos:Concept ;
  skos:prefLabel "no source for the curation date a shape requires" ;
  skos:inScheme ex:gaps ;
  skos:broader bridge:sourceLacksRequired .
"""

A_GAP_WITH_NO_PREDICATE = "ex:no-term-for-a-free-text-note"
A_GAP_CARRIED_WITH_LOSS = "ex:only-the-first-note-is-carried"
A_GAP_OF_A_VALUE_NOT_MAPPED = "ex:a-status-outside-the-set-the-vocabulary-fixes"
A_GAP_OF_A_SOURCE_LACKING_WHAT_A_SHAPE_REQUIRES = "ex:no-source-for-the-curation-date-a-shape-requires"

THE_VERSION = "/ExampleRecord/@Version"
THE_MAPPING_MENTIONS = "/ExampleRecord/Label"
ONLY_THE_FINDINGS_QUERY_MENTIONS = "/ExampleRecord/Note"
NO_QUERY_MENTIONS = "/ExampleRecord/Provenance"
THE_ACCESSION = "/ExampleRecord/@Accession"

A_PATH_IS_STEPS = (
    "is written in steps this lint cannot read, where a step of a bridge:sourcePath follows a /, and is an "
    "element's name or, for a node in a namespace, *[local-name()='name' and namespace-uri()='uri'], an "
    "attribute's step that form after an @, and no step carries a position"
)

AN_EXTENSION_NAMESPACE = "https://example.org/synthetic-adapter/ext/v1"
A_NAMESPACED_ELEMENT_NO_QUERY_MENTIONS = (
    f"/ExampleRecord/*[local-name()='Extension' and namespace-uri()='{AN_EXTENSION_NAMESPACE}']"
)
A_NAMESPACED_ELEMENT_THE_MAPPING_MENTIONS = (
    f"/ExampleRecord/*[local-name()='Label' and namespace-uri()='{AN_EXTENSION_NAMESPACE}']"
)
A_NAMESPACED_ATTRIBUTE_OF_THE_RECORD = (
    f"/ExampleRecord/@*[local-name()='kind' and namespace-uri()='{AN_EXTENSION_NAMESPACE}']"
)

CARRIED = "bridge:carried"
CARRIED_IN_PART = "bridge:carriedInPart"
REDUNDANT_WITH = "bridge:redundantWith"
CONSUMED = "bridge:consumed"
NO_HOME = "bridge:noHome"
IGNORED = "bridge:ignored"


def entry(path, verdict=CARRIED, names_gap=None, same_fact_as=None, because=None):
    written = ["[] a bridge:PathEntry", f'bridge:sourcePath "{path}"', f"bridge:verdict {verdict}"]
    written += [
        f"{predicate} {value}"
        for predicate, value in (
            ("bridge:namesGap", names_gap),
            ("bridge:sameFactAs", None if same_fact_as is None else f'"{same_fact_as}"'),
            ("bridge:because", because),
        )
        if value is not None
    ]
    return " ;\n  ".join(written) + " .\n"


def accounting(*entries):
    return PREFIXES + "\n" + "\n".join(entries)


def accounted(package, *entries):
    return package.gap_scheme(A_SCHEME_HOLDING_A_GAP_OF_EACH_KIND_A_VERDICT_IMPLIES).source_accounting(
        accounting(*entries)
    )


def said_about(package):
    return "\n".join(source_accounting.faulty(package.crate))


def test_reports_an_adapter_that_names_more_than_one_accounting(crate):
    crate.graph.remove((crate.root, BRIDGE.sourceAccounting, None))
    for named in (
        "https://example.org/synthetic-adapter/vocab/example-accounting.ttl",
        "https://example.org/synthetic-adapter/vocab/the-rest-of-it.ttl",
    ):
        crate.graph.add((crate.root, BRIDGE.sourceAccounting, URIRef(named)))
    said = "\n".join(source_accounting.faulty(crate))
    assert "more than one" in said
    assert "bridge:sourceAccounting" in said


def test_reports_an_accounting_that_is_not_a_file_in_the_package(crate):
    crate.graph.remove((crate.root, BRIDGE.sourceAccounting, None))
    crate.graph.add((crate.root, BRIDGE.sourceAccounting, URIRef("https://example.org/an-accounting.ttl")))
    assert "which is not a file in this package" in "\n".join(source_accounting.faulty(crate))


def test_reports_a_source_path_that_starts_at_the_document_rather_than_at_the_record(package):
    accounted(package, entry("/ExampleRecordSet/ExampleRecord/Label"))
    assert (
        "/ExampleRecordSet/ExampleRecord/Label starts at ExampleRecordSet, where a bridge:sourcePath "
        "starts at ExampleRecord, the adapter's bridge:elementNameOfEachRecord"
    ) in said_about(package)


def test_reports_a_source_path_that_is_the_record_element_alone(package):
    accounted(package, entry("/ExampleRecord"))
    assert (
        "/ExampleRecord is the record element alone, where a bridge:sourcePath names a node below it"
    ) in said_about(package)


def test_reports_a_source_path_whose_step_carries_a_position(package):
    accounted(package, entry("/ExampleRecord/Note[1]", verdict=NO_HOME, names_gap=A_GAP_WITH_NO_PREDICATE))
    assert "/ExampleRecord/Note[1] " + A_PATH_IS_STEPS in said_about(package)


def test_reports_a_source_path_whose_step_is_padded_with_whitespace(package):
    accounted(package, entry("/ExampleRecord/ Note ", verdict=NO_HOME, names_gap=A_GAP_WITH_NO_PREDICATE))
    assert "/ExampleRecord/ Note  " + A_PATH_IS_STEPS in said_about(package)


def test_reports_a_source_path_that_names_a_node_in_a_namespace_by_a_prefix(package):
    accounted(package, entry("/ExampleRecord/@xsi:schemaLocation", verdict=CONSUMED))
    assert "/ExampleRecord/@xsi:schemaLocation " + A_PATH_IS_STEPS in said_about(package)


def test_reports_a_source_path_writing_an_attribute_before_its_last_step(package):
    accounted(package, entry("/ExampleRecord/@Label/Emphasis", verdict=NO_HOME, names_gap=A_GAP_WITH_NO_PREDICATE))
    assert (
        "/ExampleRecord/@Label/Emphasis writes @ before a step that is not its last, "
        "where an attribute is the node a path ends at"
    ) in said_about(package)


def test_reports_nothing_for_a_source_path_naming_an_element_in_a_namespace(package):
    accounted(
        package,
        entry(A_NAMESPACED_ELEMENT_NO_QUERY_MENTIONS, verdict=NO_HOME, names_gap=A_GAP_WITH_NO_PREDICATE),
    )
    assert not said_about(package)


def test_reports_nothing_for_a_source_path_naming_an_attribute_in_a_namespace(package):
    accounted(package, entry(A_NAMESPACED_ATTRIBUTE_OF_THE_RECORD, verdict=CONSUMED))
    assert not said_about(package)


def test_reports_a_carried_entry_for_an_element_in_a_namespace_by_the_local_name_the_mapping_would_write(package):
    accounted(package, entry(A_NAMESPACED_ELEMENT_NO_QUERY_MENTIONS))
    said = said_about(package)
    assert "no bridge:mapping of this adapter mentions Extension" in said

    accounted(package, entry(A_NAMESPACED_ELEMENT_THE_MAPPING_MENTIONS))
    assert not said_about(package)


def test_reports_two_entries_sharing_a_source_path(package):
    accounted(package, entry(THE_MAPPING_MENTIONS), entry(THE_MAPPING_MENTIONS, verdict=CONSUMED))
    said = said_about(package)
    assert "bridge:sourcePath" in said
    assert THE_MAPPING_MENTIONS in said


def test_reports_a_same_fact_as_naming_a_path_the_accounting_does_not_carry(package):
    accounted(
        package,
        entry(THE_MAPPING_MENTIONS),
        entry(THE_ACCESSION, verdict=REDUNDANT_WITH, same_fact_as=NO_QUERY_MENTIONS),
    )
    said = said_about(package)
    assert "bridge:sameFactAs" in said
    assert NO_QUERY_MENTIONS in said


def test_reports_a_same_fact_as_naming_the_entrys_own_path(package):
    accounted(package, entry(THE_ACCESSION, verdict=REDUNDANT_WITH, same_fact_as=THE_ACCESSION))
    said = said_about(package)
    assert "bridge:sameFactAs" in said
    assert THE_ACCESSION in said


def test_reports_a_names_gap_that_is_no_gap_of_the_adapters_own_gap_scheme(package):
    accounted(package, entry(NO_QUERY_MENTIONS, verdict=NO_HOME, names_gap="ex:a-gap-the-scheme-does-not-hold"))
    said = said_about(package)
    assert "bridge:namesGap" in said
    assert "a-gap-the-scheme-does-not-hold" in said


def test_reports_a_no_home_entry_whose_gap_is_of_a_kind_the_verdict_does_not_imply(package):
    accounted(package, entry(NO_QUERY_MENTIONS, verdict=NO_HOME, names_gap=A_GAP_OF_A_VALUE_NOT_MAPPED))
    said = said_about(package)
    assert "bridge:noPredicate" in said
    assert A_GAP_OF_A_VALUE_NOT_MAPPED.removeprefix("ex:") in said


def test_reports_nothing_for_a_no_home_entry_naming_a_gap_of_a_source_lacking_what_a_shape_requires(package):
    accounted(
        package,
        entry(NO_QUERY_MENTIONS, verdict=NO_HOME, names_gap=A_GAP_OF_A_SOURCE_LACKING_WHAT_A_SHAPE_REQUIRES),
    )
    assert not said_about(package)


def test_reports_nothing_for_a_carried_in_part_entry_naming_a_gap_of_a_value_not_mapped(package):
    accounted(
        package,
        entry(THE_MAPPING_MENTIONS, verdict=CARRIED_IN_PART, names_gap=A_GAP_OF_A_VALUE_NOT_MAPPED),
    )
    assert not said_about(package)


def test_reports_a_no_home_entry_naming_a_gap_carried_with_loss_and_a_carried_in_part_entry_naming_one_with_no_predicate(
    package,
):
    accounted(package, entry(NO_QUERY_MENTIONS, verdict=NO_HOME, names_gap=A_GAP_CARRIED_WITH_LOSS))
    assert A_GAP_CARRIED_WITH_LOSS.removeprefix("ex:") in said_about(package)

    accounted(package, entry(THE_MAPPING_MENTIONS, verdict=CARRIED_IN_PART, names_gap=A_GAP_WITH_NO_PREDICATE))
    assert A_GAP_WITH_NO_PREDICATE.removeprefix("ex:") in said_about(package)


def test_reports_nothing_for_the_accounting_the_synthetic_adapter_commits(crate):
    assert not list(source_accounting.faulty(crate))


def test_reports_a_carried_in_part_entry_whose_gap_is_of_a_kind_the_verdict_does_not_imply(package):
    accounted(package, entry(THE_MAPPING_MENTIONS, verdict=CARRIED_IN_PART, names_gap=A_GAP_WITH_NO_PREDICATE))
    said = said_about(package)
    assert "bridge:carriedWithLoss" in said
    assert A_GAP_WITH_NO_PREDICATE.removeprefix("ex:") in said


def test_reports_a_carried_entry_for_a_path_only_a_findings_query_mentions_and_nothing_once_the_mapping_mentions_it(
    package,
):
    accounted(package, entry(ONLY_THE_FINDINGS_QUERY_MENTIONS))
    said = said_about(package)
    assert ONLY_THE_FINDINGS_QUERY_MENTIONS in said
    assert CARRIED in said

    package.edit("in/example-record.rq", "xyz:Label ; rdf:_1 ?label", "xyz:Note ; rdf:_1 ?label")
    assert not said_about(package)


def test_reports_a_carried_in_part_entry_for_a_path_no_mapping_mentions_and_nothing_where_the_verdict_is_no_home(
    package,
):
    accounted(package, entry(NO_QUERY_MENTIONS, verdict=CARRIED_IN_PART, names_gap=A_GAP_CARRIED_WITH_LOSS))
    said = said_about(package)
    assert NO_QUERY_MENTIONS in said
    assert CARRIED_IN_PART in said

    accounted(package, entry(NO_QUERY_MENTIONS, verdict=NO_HOME, names_gap=A_GAP_WITH_NO_PREDICATE))
    assert not said_about(package)


def test_reports_nothing_for_an_accounting_carrying_an_entry_of_each_verdict(package):
    accounted(
        package,
        entry(THE_MAPPING_MENTIONS),
        entry(THE_VERSION, verdict=CARRIED_IN_PART, names_gap=A_GAP_CARRIED_WITH_LOSS),
        entry(ONLY_THE_FINDINGS_QUERY_MENTIONS, verdict=REDUNDANT_WITH, same_fact_as=THE_MAPPING_MENTIONS),
        entry(THE_ACCESSION, verdict=CONSUMED),
        entry(NO_QUERY_MENTIONS, verdict=NO_HOME, names_gap=A_GAP_WITH_NO_PREDICATE),
        entry("/ExampleRecord/@SchemaVersion", verdict=IGNORED, because='"A schema version is not data."'),
    )
    assert not said_about(package)

    package.edit("in/example-record.rq", "xyz:Label ; rdf:_1 ?label", "xyz:Nowhere ; rdf:_1 ?label")
    assert THE_MAPPING_MENTIONS in said_about(package)
