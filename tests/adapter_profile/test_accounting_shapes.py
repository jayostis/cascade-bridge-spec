from rdflib import Graph

from _findings import SHAPES, unmet

BASE = "https://example.org/synthetic-adapter/vocab/example-accounting.ttl"

PREFIXES = """@prefix bridge: <https://ns.cascadeprotocol.org/bridge/v1-draft#> .
@prefix ex:     <https://example.org/synthetic-adapter/v1#> .
"""

A_PATH = '"/ExampleRecord/Label"'
THE_PATH_THAT_CARRIES_THE_FACT = '"/ExampleRecord/@Accession"'
ANOTHER_PATH_THAT_CARRIES_IT = '"/ExampleRecord/@Version"'
A_GAP = "ex:no-term-for-a-free-text-note"
ANOTHER_GAP = "ex:only-the-first-note-is-carried"
A_GAP_OF_A_VALUE_NOT_MAPPED = "ex:a-status-outside-the-set-the-vocabulary-fixes"
A_CONCEPT_MAP = "<https://example.org/synthetic-adapter/vocab/example-statuses.ttl>"
ANOTHER_CONCEPT_MAP = "<https://example.org/synthetic-adapter/vocab/example-kinds.ttl>"
A_REASON = '"A schema location is not data about the record."'
ANOTHER_REASON = '"A record identifier is not data about the record either."'

CARRIED = "bridge:carried"
CARRIED_IN_PART = "bridge:carriedInPart"
REDUNDANT_WITH = "bridge:redundantWith"
CONSUMED = "bridge:consumed"
NO_HOME = "bridge:noHome"
IGNORED = "bridge:ignored"

ONE_VERDICT = (
    "An entry carries exactly one bridge:verdict, one of bridge:carried, bridge:carriedInPart, "
    "bridge:redundantWith, bridge:consumed, bridge:noHome, bridge:ignored."
)
ONE_SOURCE_PATH = "An entry carries exactly one bridge:sourcePath, the path it accounts for, a string."
AN_ENTRY_IS_TYPED = "A subject of a bridge:sourcePath is a bridge:PathEntry."


def entry(
    path=A_PATH,
    verdict=CARRIED,
    names_gap=None,
    same_fact_as=None,
    because=None,
    typed=True,
    lookup_in=None,
    lookup_names_gap=None,
):
    written = ["a bridge:PathEntry"] if typed else []
    written += [
        f"{predicate} {value}"
        for predicate, value in (
            ("bridge:sourcePath", path),
            ("bridge:verdict", verdict),
            ("bridge:namesGap", names_gap),
            ("bridge:sameFactAs", same_fact_as),
            ("bridge:because", because),
            ("bridge:lookupIn", lookup_in),
            ("bridge:lookupNamesGap", lookup_names_gap),
        )
        if value is not None
    ]
    return PREFIXES + "\n[] " + " ;\n  ".join(written) + " .\n"


def said_about(turtle):
    return "\n".join(
        unmet(
            Graph().parse(data=turtle, format="turtle", publicID=BASE),
            Graph().parse(SHAPES, format="turtle"),
        )
    )


def test_rejects_an_entry_carrying_no_verdict():
    assert ONE_VERDICT in said_about(entry(verdict=None))
    assert not said_about(entry())


def test_rejects_an_entry_carrying_two_verdicts():
    assert ONE_VERDICT in said_about(entry(verdict=f"{CARRIED}, {CONSUMED}"))
    assert not said_about(entry())


def test_rejects_an_entry_whose_verdict_is_outside_the_scheme_of_the_six():
    assert ONE_VERDICT in said_about(entry(verdict="ex:mostly-carried"))
    assert not said_about(entry())


def test_rejects_an_entry_carrying_no_source_path():
    assert ONE_SOURCE_PATH in said_about(entry(path=None))
    assert not said_about(entry())


def test_rejects_an_entry_carrying_two_source_paths():
    assert ONE_SOURCE_PATH in said_about(entry(path=f"{A_PATH}, {THE_PATH_THAT_CARRIES_THE_FACT}"))
    assert not said_about(entry())


def test_rejects_an_entry_whose_source_path_is_an_iri_rather_than_a_string():
    assert ONE_SOURCE_PATH in said_about(entry(path="<https://example.org/synthetic-adapter/paths/Label>"))
    assert not said_about(entry())


def test_rejects_a_subject_of_a_source_path_that_is_no_path_entry():
    assert AN_ENTRY_IS_TYPED in said_about(entry(typed=False))
    assert not said_about(entry())


def test_rejects_a_carried_entry_that_names_a_gap():
    assert "An entry whose verdict is bridge:carried names no bridge:namesGap." in said_about(
        entry(verdict=CARRIED, names_gap=A_GAP)
    )
    assert not said_about(entry(verdict=CARRIED))


def test_rejects_a_carried_entry_that_names_the_path_carrying_the_same_fact():
    assert "An entry whose verdict is bridge:carried names no bridge:sameFactAs." in said_about(
        entry(verdict=CARRIED, same_fact_as=THE_PATH_THAT_CARRIES_THE_FACT)
    )
    assert not said_about(entry(verdict=CARRIED))


def test_rejects_a_carried_entry_that_gives_a_reason():
    assert "An entry whose verdict is bridge:carried gives no bridge:because." in said_about(
        entry(verdict=CARRIED, because=A_REASON)
    )
    assert not said_about(entry(verdict=CARRIED))


def test_rejects_a_carried_in_part_entry_that_names_no_gap():
    assert (
        "An entry whose verdict is bridge:carriedInPart names exactly one bridge:namesGap, the gap the loss opens."
    ) in said_about(entry(verdict=CARRIED_IN_PART))
    assert not said_about(entry(verdict=CARRIED_IN_PART, names_gap=A_GAP))


def test_rejects_a_carried_in_part_entry_that_names_two_gaps():
    assert (
        "An entry whose verdict is bridge:carriedInPart names exactly one bridge:namesGap, the gap the loss opens."
    ) in said_about(entry(verdict=CARRIED_IN_PART, names_gap=f"{A_GAP}, {ANOTHER_GAP}"))
    assert not said_about(entry(verdict=CARRIED_IN_PART, names_gap=A_GAP))


def test_rejects_a_carried_in_part_entry_that_names_the_path_carrying_the_same_fact():
    assert "An entry whose verdict is bridge:carriedInPart names no bridge:sameFactAs." in said_about(
        entry(verdict=CARRIED_IN_PART, names_gap=A_GAP, same_fact_as=THE_PATH_THAT_CARRIES_THE_FACT)
    )
    assert not said_about(entry(verdict=CARRIED_IN_PART, names_gap=A_GAP))


def test_rejects_a_carried_in_part_entry_that_gives_a_reason():
    assert "An entry whose verdict is bridge:carriedInPart gives no bridge:because." in said_about(
        entry(verdict=CARRIED_IN_PART, names_gap=A_GAP, because=A_REASON)
    )
    assert not said_about(entry(verdict=CARRIED_IN_PART, names_gap=A_GAP))


def test_rejects_a_redundant_with_entry_that_names_no_path_carrying_the_same_fact():
    assert (
        "An entry whose verdict is bridge:redundantWith names exactly one bridge:sameFactAs, "
        "the bridge:sourcePath that carries the fact instead."
    ) in said_about(entry(verdict=REDUNDANT_WITH))
    assert not said_about(entry(verdict=REDUNDANT_WITH, same_fact_as=THE_PATH_THAT_CARRIES_THE_FACT))


def test_rejects_a_redundant_with_entry_that_names_two_paths_carrying_the_same_fact():
    assert (
        "An entry whose verdict is bridge:redundantWith names exactly one bridge:sameFactAs, "
        "the bridge:sourcePath that carries the fact instead."
    ) in said_about(
        entry(
            verdict=REDUNDANT_WITH,
            same_fact_as=f"{THE_PATH_THAT_CARRIES_THE_FACT}, {ANOTHER_PATH_THAT_CARRIES_IT}",
        )
    )
    assert not said_about(entry(verdict=REDUNDANT_WITH, same_fact_as=THE_PATH_THAT_CARRIES_THE_FACT))


def test_rejects_a_redundant_with_entry_that_names_a_gap():
    assert "An entry whose verdict is bridge:redundantWith names no bridge:namesGap." in said_about(
        entry(verdict=REDUNDANT_WITH, same_fact_as=THE_PATH_THAT_CARRIES_THE_FACT, names_gap=A_GAP)
    )
    assert not said_about(entry(verdict=REDUNDANT_WITH, same_fact_as=THE_PATH_THAT_CARRIES_THE_FACT))


def test_rejects_a_redundant_with_entry_that_gives_a_reason():
    assert "An entry whose verdict is bridge:redundantWith gives no bridge:because." in said_about(
        entry(verdict=REDUNDANT_WITH, same_fact_as=THE_PATH_THAT_CARRIES_THE_FACT, because=A_REASON)
    )
    assert not said_about(entry(verdict=REDUNDANT_WITH, same_fact_as=THE_PATH_THAT_CARRIES_THE_FACT))


def test_rejects_a_consumed_entry_that_names_a_gap():
    assert "An entry whose verdict is bridge:consumed names no bridge:namesGap." in said_about(
        entry(verdict=CONSUMED, names_gap=A_GAP)
    )
    assert not said_about(entry(verdict=CONSUMED))


def test_rejects_a_consumed_entry_that_names_the_path_carrying_the_same_fact():
    assert "An entry whose verdict is bridge:consumed names no bridge:sameFactAs." in said_about(
        entry(verdict=CONSUMED, same_fact_as=THE_PATH_THAT_CARRIES_THE_FACT)
    )
    assert not said_about(entry(verdict=CONSUMED))


def test_rejects_a_consumed_entry_that_gives_a_reason():
    assert "An entry whose verdict is bridge:consumed gives no bridge:because." in said_about(
        entry(verdict=CONSUMED, because=A_REASON)
    )
    assert not said_about(entry(verdict=CONSUMED))


def test_rejects_a_no_home_entry_that_names_no_gap():
    assert (
        "An entry whose verdict is bridge:noHome names exactly one bridge:namesGap, "
        "the gap the missing predicate opens."
    ) in said_about(entry(verdict=NO_HOME))
    assert not said_about(entry(verdict=NO_HOME, names_gap=A_GAP))


def test_rejects_a_no_home_entry_that_names_two_gaps():
    assert (
        "An entry whose verdict is bridge:noHome names exactly one bridge:namesGap, "
        "the gap the missing predicate opens."
    ) in said_about(entry(verdict=NO_HOME, names_gap=f"{A_GAP}, {ANOTHER_GAP}"))
    assert not said_about(entry(verdict=NO_HOME, names_gap=A_GAP))


def test_rejects_a_no_home_entry_that_names_the_path_carrying_the_same_fact():
    assert "An entry whose verdict is bridge:noHome names no bridge:sameFactAs." in said_about(
        entry(verdict=NO_HOME, names_gap=A_GAP, same_fact_as=THE_PATH_THAT_CARRIES_THE_FACT)
    )
    assert not said_about(entry(verdict=NO_HOME, names_gap=A_GAP))


def test_rejects_a_no_home_entry_that_gives_a_reason():
    assert "An entry whose verdict is bridge:noHome gives no bridge:because." in said_about(
        entry(verdict=NO_HOME, names_gap=A_GAP, because=A_REASON)
    )
    assert not said_about(entry(verdict=NO_HOME, names_gap=A_GAP))


def test_rejects_an_ignored_entry_that_gives_no_reason():
    assert (
        "An entry whose verdict is bridge:ignored gives exactly one bridge:because, "
        "why the path is deliberately not carried."
    ) in said_about(entry(verdict=IGNORED))
    assert not said_about(entry(verdict=IGNORED, because=A_REASON))


def test_rejects_an_ignored_entry_that_gives_two_reasons():
    assert (
        "An entry whose verdict is bridge:ignored gives exactly one bridge:because, "
        "why the path is deliberately not carried."
    ) in said_about(entry(verdict=IGNORED, because=f"{A_REASON}, {ANOTHER_REASON}"))
    assert not said_about(entry(verdict=IGNORED, because=A_REASON))


def test_rejects_an_ignored_entry_that_names_a_gap():
    assert "An entry whose verdict is bridge:ignored names no bridge:namesGap." in said_about(
        entry(verdict=IGNORED, because=A_REASON, names_gap=A_GAP)
    )
    assert not said_about(entry(verdict=IGNORED, because=A_REASON))


def test_rejects_an_ignored_entry_that_names_the_path_carrying_the_same_fact():
    assert "An entry whose verdict is bridge:ignored names no bridge:sameFactAs." in said_about(
        entry(verdict=IGNORED, because=A_REASON, same_fact_as=THE_PATH_THAT_CARRIES_THE_FACT)
    )
    assert not said_about(entry(verdict=IGNORED, because=A_REASON))


def looks_up(verdict=CONSUMED, lookup_in=A_CONCEPT_MAP, lookup_names_gap=A_GAP_OF_A_VALUE_NOT_MAPPED, **rest):
    return entry(verdict=verdict, lookup_in=lookup_in, lookup_names_gap=lookup_names_gap, **rest)


def test_rejects_an_entry_naming_a_concept_map_and_no_gap_for_a_value_outside_it():
    assert "bridge:lookupNamesGap" in said_about(looks_up(lookup_names_gap=None))
    assert not said_about(looks_up())


def test_rejects_an_entry_naming_a_gap_for_a_value_outside_a_concept_map_it_names_nowhere():
    assert "bridge:lookupIn" in said_about(looks_up(lookup_in=None))
    assert not said_about(looks_up())


def test_rejects_an_entry_naming_two_concept_maps():
    assert "bridge:lookupIn" in said_about(looks_up(lookup_in=f"{A_CONCEPT_MAP}, {ANOTHER_CONCEPT_MAP}"))
    assert not said_about(looks_up())


def test_rejects_an_entry_naming_two_gaps_for_a_value_outside_its_concept_map():
    assert "bridge:lookupNamesGap" in said_about(looks_up(lookup_names_gap=f"{A_GAP_OF_A_VALUE_NOT_MAPPED}, {A_GAP}"))
    assert not said_about(looks_up())


def test_rejects_a_concept_map_named_as_a_string_rather_than_by_iri():
    assert "bridge:lookupIn" in said_about(looks_up(lookup_in='"vocab/example-statuses.ttl"'))
    assert not said_about(looks_up())


def test_rejects_half_a_lookup_on_an_entry_of_every_verdict_and_accepts_both_halves_there():
    for verdict, rest in (
        (CARRIED, {}),
        (CARRIED_IN_PART, {"names_gap": A_GAP}),
        (REDUNDANT_WITH, {"same_fact_as": THE_PATH_THAT_CARRIES_THE_FACT}),
        (CONSUMED, {}),
        (NO_HOME, {"names_gap": A_GAP}),
        (IGNORED, {"because": A_REASON}),
    ):
        assert "bridge:lookupIn" in said_about(looks_up(verdict=verdict, lookup_in=None, **rest)), verdict
        assert "bridge:lookupNamesGap" in said_about(looks_up(verdict=verdict, lookup_names_gap=None, **rest)), verdict
        assert not said_about(looks_up(verdict=verdict, **rest)), verdict
