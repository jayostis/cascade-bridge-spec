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
"""

A_GAP_WITH_NO_PREDICATE = "ex:no-term-for-a-free-text-note"
A_GAP_CARRIED_WITH_LOSS = "ex:only-the-first-note-is-carried"
A_GAP_OF_A_VALUE_NOT_MAPPED = "ex:a-status-outside-the-set-the-vocabulary-fixes"

THE_VERSION = "/ExampleRecord/@Version"
THE_MAPPING_MENTIONS = "/ExampleRecord/Label"
ONLY_THE_FINDINGS_QUERY_MENTIONS = "/ExampleRecord/Note"
NO_QUERY_MENTIONS = "/ExampleRecord/Provenance"
THE_ACCESSION = "/ExampleRecord/@Accession"

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
