from rdflib import Graph

from _findings import SHAPES, unmet

BASE = "https://example.org/synthetic-adapter/vocab/example-statuses.ttl"

PREFIXES = """@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix ex:   <https://example.org/synthetic-adapter/v1#> .

ex:statuses a skos:ConceptScheme .
"""

A_CONCEPT = "ex:status-current"
ANOTHER_CONCEPT = "ex:status-live"
A_CASCADE_TERM = "ex:Current"
ANOTHER_CASCADE_TERM = "ex:SubmitterLaboratory"


def concept(
    name=A_CONCEPT,
    in_scheme="ex:statuses",
    notation='"current"',
    exact_match=A_CASCADE_TERM,
    close_match=None,
):
    written = [f"{name} a skos:Concept"]
    written += [
        f"{predicate} {value}"
        for predicate, value in (
            ("skos:inScheme", in_scheme),
            ("skos:notation", notation),
            ("skos:exactMatch", exact_match),
            ("skos:closeMatch", close_match),
        )
        if value is not None
    ]
    return " ;\n  ".join(written) + " .\n"


def said_about(*concepts):
    return "\n".join(
        unmet(
            Graph().parse(data=PREFIXES + "\n" + "\n".join(concepts), format="turtle", publicID=BASE),
            Graph().parse(SHAPES, format="turtle"),
        )
    )


def test_rejects_a_concept_carrying_no_notation():
    assert "skos:notation" in said_about(concept(notation=None))
    assert not said_about(concept())


def test_rejects_a_concept_carrying_two_notations():
    assert "skos:notation" in said_about(concept(notation='"current", "Current"'))
    assert not said_about(concept())


def test_rejects_a_concept_matching_no_cascade_term():
    said = said_about(concept(exact_match=None))
    assert "skos:exactMatch" in said
    assert "skos:closeMatch" in said
    assert not said_about(concept())


def test_rejects_a_concept_matching_a_cascade_term_both_exactly_and_closely():
    said = said_about(concept(exact_match=A_CASCADE_TERM, close_match=A_CASCADE_TERM))
    assert "skos:exactMatch" in said
    assert "skos:closeMatch" in said
    assert not said_about(concept(exact_match=None, close_match=A_CASCADE_TERM))


def test_rejects_a_concept_carrying_two_exact_matches():
    assert "skos:exactMatch" in said_about(concept(exact_match=f"{A_CASCADE_TERM}, {ANOTHER_CASCADE_TERM}"))
    assert not said_about(concept())


def test_rejects_two_concepts_of_one_scheme_carrying_one_notation():
    said = said_about(concept(), concept(name=ANOTHER_CONCEPT, exact_match=ANOTHER_CASCADE_TERM))
    assert "skos:notation" in said
    assert not said_about(concept(), concept(name=ANOTHER_CONCEPT, notation='"live"'))


def test_rejects_a_concept_in_no_scheme_and_a_concept_in_two():
    assert "skos:inScheme" in said_about(concept(in_scheme=None))
    assert "skos:inScheme" in said_about(concept(in_scheme="ex:statuses, ex:kinds"))
    assert not said_about(concept())


def test_rejects_a_concept_matching_a_cascade_term_written_as_a_string_rather_than_by_iri():
    assert "skos:exactMatch" in said_about(concept(exact_match='"Current"'))
    assert not said_about(concept())
