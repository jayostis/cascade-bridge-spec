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
A_PATH_BELOW_THE_RECORD = (
    "A bridge:sourcePath starts at the record element and names a node below it: a step for the record "
    "element, then one for each element down to the node, an attribute's last step written @name, and no "
    "step carrying a position. It is not rooted at the document, and the record element alone is no path."
)


def entry(path=A_PATH, verdict=CARRIED, names_gap=None, same_fact_as=None, because=None):
    written = ["[] a bridge:PathEntry"]
    written += [
        f"{predicate} {value}"
        for predicate, value in (
            ("bridge:sourcePath", path),
            ("bridge:verdict", verdict),
            ("bridge:namesGap", names_gap),
            ("bridge:sameFactAs", same_fact_as),
            ("bridge:because", because),
        )
        if value is not None
    ]
    return PREFIXES + "\n" + " ;\n  ".join(written) + " .\n"


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


def test_rejects_an_entry_whose_source_path_is_the_record_element_rather_than_a_node_below_it():
    assert A_PATH_BELOW_THE_RECORD in said_about(entry(path='"/ExampleRecord"'))
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
