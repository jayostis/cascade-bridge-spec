from rdflib import URIRef

import gap_scheme
from _terms import BRIDGE

PREFIXES = """@prefix skos:   <http://www.w3.org/2004/02/skos/core#> .
@prefix bridge: <https://ns.cascadeprotocol.org/bridge/v1-draft#> .
@prefix ex:     <https://example.org/synthetic-adapter/v1#> .

ex:gaps a skos:ConceptScheme .
"""

THE_GAP = "https://example.org/synthetic-adapter/v1#no-term-for-a-free-text-note"

THE_KINDS = (
    "bridge:carriedWithLoss, bridge:noPredicate, bridge:schemaRuleUnnamed, "
    "bridge:sourceLacksRequired, bridge:valueNotMapped"
)


def scheme_of_one_gap(
    label='skos:prefLabel "no term for a free-text note"',
    in_scheme="skos:inScheme ex:gaps",
    broader="skos:broader bridge:noPredicate",
    closed_by=None,
):
    written = ["ex:no-term-for-a-free-text-note a skos:Concept"]
    written += [statement for statement in (label, in_scheme, broader) if statement is not None]
    if closed_by is not None:
        written.append(f"bridge:closedBy {closed_by}")
    return PREFIXES + "\n" + " ;\n  ".join(written) + " .\n"


def test_reports_an_adapter_that_names_a_findings_query_and_no_gap_scheme(crate):
    crate.graph.remove((crate.root, BRIDGE.gapScheme, None))
    assert (
        "the adapter names a bridge:findingsQuery and no bridge:gapScheme, the one file of skos:Concepts "
        "the bodies a findings query constructs are gaps of"
    ) in "\n".join(gap_scheme.faulty(crate))


def test_reports_an_adapter_that_names_more_than_one_gap_scheme(crate):
    crate.graph.remove((crate.root, BRIDGE.gapScheme, None))
    for named in ("https://example.org/synthetic-adapter/v1#gaps", "https://example.org/synthetic-adapter/v2#gaps"):
        crate.graph.add((crate.root, BRIDGE.gapScheme, URIRef(named)))
    assert (
        "the adapter names more than one bridge:gapScheme, where a findings query's bodies are gaps of one scheme"
    ) in "\n".join(gap_scheme.faulty(crate))


def test_reports_a_gap_scheme_that_is_not_a_file_in_the_package(crate):
    crate.graph.remove((crate.root, BRIDGE.gapScheme, None))
    crate.graph.add((crate.root, BRIDGE.gapScheme, URIRef("https://example.org/synthetic-adapter/v1#gaps")))
    assert (
        "bridge:gapScheme names https://example.org/synthetic-adapter/v1#gaps, which is not a file in this package"
    ) in "\n".join(gap_scheme.faulty(crate))


def test_reports_nothing_for_an_adapter_that_names_neither_a_findings_query_nor_a_gap_scheme(crate):
    crate.graph.remove((crate.root, BRIDGE.findingsQuery, None))
    crate.graph.remove((crate.root, BRIDGE.gapScheme, None))
    assert not list(gap_scheme.faulty(crate))


def test_reports_a_gap_carrying_no_preferred_label(package):
    package.gap_scheme(scheme_of_one_gap(label=None))
    assert f"{THE_GAP} carries exactly one skos:prefLabel, the sentence a finding no longer carries" in "\n".join(
        gap_scheme.faulty(package.crate)
    )


def test_reports_a_gap_that_names_no_scheme(package):
    package.gap_scheme(scheme_of_one_gap(in_scheme=None))
    assert (
        f"{THE_GAP} carries exactly one skos:inScheme, the scheme the adapter's bridge:gapScheme names"
    ) in "\n".join(gap_scheme.faulty(package.crate))


def test_reports_a_gap_that_is_broader_than_no_kind(package):
    package.gap_scheme(scheme_of_one_gap(broader=None))
    assert f"{THE_GAP} is skos:broader exactly one of {THE_KINDS}" in "\n".join(gap_scheme.faulty(package.crate))


def test_reports_a_gap_that_is_broader_than_two_kinds(package):
    package.gap_scheme(scheme_of_one_gap(broader="skos:broader bridge:noPredicate, bridge:carriedWithLoss"))
    assert f"{THE_GAP} is skos:broader exactly one of {THE_KINDS}" in "\n".join(gap_scheme.faulty(package.crate))


def test_reports_a_gap_whose_kind_is_outside_the_kinds_the_vocabulary_declares(package):
    package.gap_scheme(scheme_of_one_gap(broader="skos:broader ex:a-kind-of-our-own"))
    assert f"{THE_GAP} is skos:broader exactly one of {THE_KINDS}" in "\n".join(gap_scheme.faulty(package.crate))


def test_reports_a_closing_term_that_is_a_literal(package):
    package.gap_scheme(scheme_of_one_gap(closed_by='"genomics:assertionDate"'))
    assert (f"{THE_GAP} names at most one bridge:closedBy, the Cascade term that would close it, by IRI") in "\n".join(
        gap_scheme.faulty(package.crate)
    )


def test_reports_nothing_for_a_gap_carrying_a_label_its_scheme_one_kind_and_a_closing_term(package):
    package.gap_scheme(scheme_of_one_gap(closed_by="<https://ns.cascadeprotocol.org/genomics/v1#assertionDate>"))
    assert not list(gap_scheme.faulty(package.crate))
