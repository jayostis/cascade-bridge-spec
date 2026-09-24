import lookups
from _terms import BRIDGE

ACCOUNTING = "vocab/example-accounting.ttl"
CONCEPT_MAP = "vocab/example-statuses.ttl"
THE_GAP_IT_NAMES = "bridge:lookupNamesGap ex:a-status-outside-the-set-the-vocabulary-fixes"
THE_SCHEME = "ex:statuses a skos:ConceptScheme .\n"


def said_about(crate):
    return "\n".join(lookups.faulty(crate))


def test_reports_nothing_for_the_lookup_the_synthetic_adapter_commits(crate):
    assert not said_about(crate)


def test_reports_nothing_for_an_adapter_naming_no_accounting(crate):
    crate.graph.remove((crate.root, BRIDGE.sourceAccounting, None))
    assert not said_about(crate)


def test_reports_a_concept_map_no_bridge_table_names(crate):
    crate.graph.remove((crate.root, BRIDGE.table, None))
    said = said_about(crate)
    assert "example-statuses.ttl, which the adapter declares as no bridge:table" in said


def test_reports_a_gap_of_a_kind_other_than_a_value_not_mapped(package):
    package.edit(ACCOUNTING, THE_GAP_IT_NAMES, "bridge:lookupNamesGap ex:no-term-for-a-free-text-note")
    said = said_about(package.crate)
    assert "no-term-for-a-free-text-note" in said
    assert "skos:broader bridge:valueNotMapped" in said


def test_reports_a_gap_no_scheme_of_the_adapter_holds(package):
    package.edit(ACCOUNTING, THE_GAP_IT_NAMES, "bridge:lookupNamesGap ex:a-gap-the-scheme-does-not-hold")
    said = said_about(package.crate)
    assert "a-gap-the-scheme-does-not-hold" in said
    assert "no gap of the adapter's bridge:gapScheme" in said


def test_reports_a_concept_map_carrying_two_concept_schemes(package):
    package.edit(CONCEPT_MAP, THE_SCHEME, THE_SCHEME + "ex:statuses-of-our-own a skos:ConceptScheme .\n")
    assert "example-statuses.ttl carries 2 skos:ConceptSchemes" in said_about(package.crate)


def test_reports_a_concept_map_carrying_no_concept_scheme(package):
    package.edit(CONCEPT_MAP, THE_SCHEME, "")
    assert "example-statuses.ttl carries 0 skos:ConceptSchemes" in said_about(package.crate)


def test_reports_a_concept_in_a_scheme_other_than_the_one_its_concept_map_carries(package):
    package.edit(
        CONCEPT_MAP,
        'skos:inScheme ex:statuses ;\n  skos:notation "superseded"',
        'skos:inScheme ex:status ;\n  skos:notation "superseded"',
    )
    assert "the one skos:ConceptScheme example-statuses.ttl carries" in said_about(package.crate)


def test_reports_a_concept_map_that_is_not_turtle(package):
    package.write(CONCEPT_MAP, "ex:statuses a skos:ConceptScheme .\n")
    assert "example-statuses.ttl does not parse as Turtle" in said_about(package.crate)


def test_applies_the_concept_map_shapes_to_the_concept_map(package):
    package.edit(CONCEPT_MAP, 'skos:notation "current"', 'skos:notation " Current"')
    said = said_about(package.crate)
    assert "example-statuses.ttl: https://example.org/synthetic-adapter/v1#status-current: " in said
    assert "A skos:notation is written as the key it is looked up by" in said
