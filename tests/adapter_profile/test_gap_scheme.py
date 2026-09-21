from rdflib import URIRef

import gap_scheme
from _terms import BRIDGE

PREFIXES = """@prefix skos:   <http://www.w3.org/2004/02/skos/core#> .
@prefix sh:     <http://www.w3.org/ns/shacl#> .
@prefix bridge: <https://ns.cascadeprotocol.org/bridge/v1-draft#> .
@prefix ex:     <https://example.org/synthetic-adapter/v1#> .

ex:gaps a skos:ConceptScheme .
"""

THE_GAP = "https://example.org/synthetic-adapter/v1#no-term-for-a-free-text-note"
THE_SCHEME = "https://example.org/synthetic-adapter/v1#gaps"

THE_KINDS_A_GAP_MAY_NAME = (
    "bridge:carriedWithLoss, bridge:noPredicate, bridge:schemaRuleUnnamed, "
    "bridge:sourceLacksRequired, bridge:valueNotMapped"
)


def scheme_of_one_gap(
    label='skos:prefLabel "no term for a free-text note"',
    in_scheme="skos:inScheme ex:gaps",
    broader="skos:broader bridge:noPredicate",
    closed_by=None,
    severity=None,
):
    written = ["ex:no-term-for-a-free-text-note a skos:Concept"]
    written += [statement for statement in (label, in_scheme, broader) if statement is not None]
    if closed_by is not None:
        written.append(f"bridge:closedBy {closed_by}")
    if severity is not None:
        written.append(f"sh:resultSeverity {severity}")
    return PREFIXES + "\n" + " ;\n  ".join(written) + " .\n"


def said_about(package, **gap):
    package.gap_scheme(scheme_of_one_gap(**gap))
    return "\n".join(gap_scheme.faulty(package.crate))


def test_reports_a_gap_declaring_two_severities(package):
    said = said_about(package, severity="sh:Warning, sh:Violation")
    assert THE_GAP in said
    assert "sh:resultSeverity" in said
    assert not said_about(package, severity="sh:Warning")


def test_reports_a_gap_whose_declared_severity_is_outside_the_three_a_finding_carries(package):
    said = said_about(package, severity="ex:as-loud-as-we-like")
    assert THE_GAP in said
    assert "sh:resultSeverity" in said
    assert not said_about(package, severity="sh:Violation")


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
        f"{THE_GAP} carries exactly one skos:inScheme, {THE_SCHEME}, "
        "the one skos:ConceptScheme example-gaps.ttl carries"
    ) in "\n".join(gap_scheme.faulty(package.crate))


def test_reports_a_gap_that_is_broader_than_no_kind(package):
    package.gap_scheme(scheme_of_one_gap(broader=None))
    assert f"{THE_GAP} is skos:broader exactly one of {THE_KINDS_A_GAP_MAY_NAME}" in "\n".join(
        gap_scheme.faulty(package.crate)
    )


def test_reports_a_gap_that_is_broader_than_two_kinds(package):
    package.gap_scheme(scheme_of_one_gap(broader="skos:broader bridge:noPredicate, bridge:carriedWithLoss"))
    assert f"{THE_GAP} is skos:broader exactly one of {THE_KINDS_A_GAP_MAY_NAME}" in "\n".join(
        gap_scheme.faulty(package.crate)
    )


def test_reports_a_gap_whose_kind_is_outside_the_kinds_the_vocabulary_declares(package):
    package.gap_scheme(scheme_of_one_gap(broader="skos:broader ex:a-kind-of-our-own"))
    assert f"{THE_GAP} is skos:broader exactly one of {THE_KINDS_A_GAP_MAY_NAME}" in "\n".join(
        gap_scheme.faulty(package.crate)
    )


def test_reports_a_gap_whose_kind_is_the_concept_a_census_carries(package):
    package.gap_scheme(scheme_of_one_gap(broader="skos:broader bridge:pathNotAccounted"))
    assert f"{THE_GAP} is skos:broader exactly one of {THE_KINDS_A_GAP_MAY_NAME}" in "\n".join(
        gap_scheme.faulty(package.crate)
    )


def test_reports_a_closing_term_that_is_a_literal(package):
    package.gap_scheme(scheme_of_one_gap(closed_by='"genomics:assertionDate"'))
    assert (f"{THE_GAP} names at most one bridge:closedBy, the Cascade term that would close it, by IRI") in "\n".join(
        gap_scheme.faulty(package.crate)
    )


def test_reports_nothing_for_a_gap_carrying_a_label_its_scheme_one_kind_and_a_closing_term(package):
    package.gap_scheme(scheme_of_one_gap(closed_by="<https://ns.cascadeprotocol.org/genomics/v1#assertionDate>"))
    assert not list(gap_scheme.faulty(package.crate))


A_SCHEME_FILE_NAMING_NO_CONCEPT_SCHEME = """@prefix skos:   <http://www.w3.org/2004/02/skos/core#> .
@prefix bridge: <https://ns.cascadeprotocol.org/bridge/v1-draft#> .
@prefix ex:     <https://example.org/synthetic-adapter/v1#> .

ex:no-term-for-a-free-text-note a skos:Concept ;
  skos:prefLabel "no term for a free-text note" ;
  skos:inScheme ex:gaps ;
  skos:broader bridge:noPredicate .
"""

A_SECOND_CONCEPT_SCHEME = "\nex:gaps-of-our-own a skos:ConceptScheme .\n"


def test_reports_a_gap_scheme_file_carrying_no_concept_scheme(package):
    package.gap_scheme(A_SCHEME_FILE_NAMING_NO_CONCEPT_SCHEME)
    assert (
        "example-gaps.ttl carries 0 skos:ConceptSchemes, where a gap scheme carries exactly one, "
        "the scheme every gap in it is skos:inScheme"
    ) in "\n".join(gap_scheme.faulty(package.crate))


def test_reports_a_gap_scheme_file_carrying_two_concept_schemes(package):
    package.gap_scheme(scheme_of_one_gap() + A_SECOND_CONCEPT_SCHEME)
    assert (
        "example-gaps.ttl carries 2 skos:ConceptSchemes, where a gap scheme carries exactly one, "
        "the scheme every gap in it is skos:inScheme"
    ) in "\n".join(gap_scheme.faulty(package.crate))


def test_reports_a_gap_that_names_a_scheme_other_than_the_one_its_file_carries(package):
    package.gap_scheme(scheme_of_one_gap(in_scheme="skos:inScheme ex:something-else"))
    assert (
        f"{THE_GAP} carries exactly one skos:inScheme, {THE_SCHEME}, "
        "the one skos:ConceptScheme example-gaps.ttl carries"
    ) in "\n".join(gap_scheme.faulty(package.crate))


def test_reports_a_gap_naming_two_closing_terms(package):
    package.gap_scheme(
        scheme_of_one_gap(
            closed_by=(
                "<https://ns.cascadeprotocol.org/genomics/v1#assertionDate>, "
                "<https://ns.cascadeprotocol.org/genomics/v1#assertionNote>"
            )
        )
    )
    assert (f"{THE_GAP} names at most one bridge:closedBy, the Cascade term that would close it, by IRI") in "\n".join(
        gap_scheme.faulty(package.crate)
    )


def test_reports_a_gap_scheme_that_does_not_parse_as_turtle(package):
    package.gap_scheme("ex:gaps a skos:ConceptScheme .\n")
    assert "example-gaps.ttl does not parse as Turtle" in "\n".join(gap_scheme.faulty(package.crate))
