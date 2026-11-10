from adapter_profile_world import said_over
from lookups import SHAPES

BASE = "https://example.org/synthetic-adapter/vocab/example-statuses.ttl"

PREFIXES = """@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix ex:   <https://example.org/synthetic-adapter/v1#> .

ex:statuses a skos:ConceptScheme .
"""

A_CONCEPT = "ex:status-current"
ANOTHER_CONCEPT = "ex:status-live"
A_CASCADE_TERM = "ex:Current"
ANOTHER_CASCADE_TERM = "ex:SubmitterLaboratory"

A_NOTATION_IS_A_KEY = "A skos:notation is written as the key it is looked up by"
ONE_KEY_IS_ONE_CONCEPTS = "One key is the skos:notation of one concept of a scheme"


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
    return said_over(PREFIXES + "\n" + "\n".join(concepts), SHAPES, BASE)


class TestLookingAValueUpInAConceptMap:
    """Looking a value up in a concept map · adapter/profile/must/lookups.py, shapes/concept-map.shapes.ttl

    A concept map is a SKOS scheme whose notations are a source's values and whose matches are Cascade terms. An entry
    that looks its path's values up names the map and the gap a value outside the map opens.
    """

    class TestGivenAConceptOfAConceptMapThatBreaksAConstraint:
        def test_rejects_a_concept_carrying_no_notation(self):
            assert "skos:notation" in said_about(concept(notation=None))
            assert not said_about(concept())

        def test_rejects_a_concept_carrying_two_notations(self):
            assert "skos:notation" in said_about(concept(notation='"current", "Current"'))
            assert not said_about(concept())

        def test_rejects_a_concept_matching_no_cascade_term(self):
            said = said_about(concept(exact_match=None))
            assert "skos:exactMatch" in said
            assert "skos:closeMatch" in said
            assert not said_about(concept())

        def test_rejects_a_concept_matching_a_cascade_term_both_exactly_and_closely(self):
            said = said_about(concept(exact_match=A_CASCADE_TERM, close_match=A_CASCADE_TERM))
            assert "skos:exactMatch" in said
            assert "skos:closeMatch" in said
            assert not said_about(concept(exact_match=None, close_match=A_CASCADE_TERM))

        def test_rejects_a_concept_carrying_two_exact_matches(self):
            assert "skos:exactMatch" in said_about(concept(exact_match=f"{A_CASCADE_TERM}, {ANOTHER_CASCADE_TERM}"))
            assert not said_about(concept())

        def test_rejects_two_concepts_of_one_scheme_carrying_one_notation(self):
            said = said_about(concept(), concept(name=ANOTHER_CONCEPT, exact_match=ANOTHER_CASCADE_TERM))
            assert "skos:notation" in said
            assert not said_about(concept(), concept(name=ANOTHER_CONCEPT, notation='"live"'))

        def test_rejects_a_notation_the_lowercasing_of_a_value_can_never_equal(self):
            assert A_NOTATION_IS_A_KEY in said_about(concept(notation='"Current"'))
            assert not said_about(concept())

        def test_rejects_a_notation_the_whitespace_stripping_of_a_value_can_never_equal(self):
            for spelled in ('" current"', '"current "', '"\\tcurrent"', '"current\\r"', '"current\\n"'):
                assert A_NOTATION_IS_A_KEY in said_about(concept(notation=spelled)), spelled
            assert not said_about(concept())

        def test_rejects_two_concepts_of_one_scheme_whose_notations_are_one_key_spelled_two_ways(self):
            said = said_about(
                concept(), concept(name=ANOTHER_CONCEPT, notation='"Current"', exact_match=ANOTHER_CASCADE_TERM)
            )
            assert ONE_KEY_IS_ONE_CONCEPTS in said
            assert not said_about(concept(), concept(name=ANOTHER_CONCEPT, notation='"live"'))

        def test_rejects_a_concept_in_no_scheme_and_a_concept_in_two(self):
            assert "skos:inScheme" in said_about(concept(in_scheme=None))
            assert "skos:inScheme" in said_about(concept(in_scheme="ex:statuses, ex:kinds"))
            assert not said_about(concept())

        def test_rejects_a_concept_matching_a_cascade_term_written_as_a_string_rather_than_by_iri(self):
            """rejects a concept matching a cascade term written as a string rather than by IRI"""
            assert "skos:exactMatch" in said_about(concept(exact_match='"Current"'))
            assert not said_about(concept())

    class TestGivenAConceptOfAConceptMapThatConforms:
        def test_accepts_a_notation_holding_a_character_that_is_whitespace_nowhere_xml_calls_whitespace(self):
            """accepts a notation holding a character that is whitespace nowhere XML calls whitespace"""
            assert not said_about(concept(notation='"\\u00A0current"'))

        def test_accepts_a_notation_lowercased_as_sparql_lowercases_it_where_case_folding_would_go_further(self):
            """accepts a notation lowercased as SPARQL lowercases it where case folding would go further"""
            assert not said_about(concept(notation='"stra\\u00DFe"'))
