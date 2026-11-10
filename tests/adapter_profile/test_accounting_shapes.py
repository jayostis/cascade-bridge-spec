import pytest

from _findings import SHAPES
from adapter_profile_world import (
    CARRIED,
    CARRIED_IN_PART,
    CONSUMED,
    IGNORED,
    NO_HOME,
    PREFIXES_OF_AN_ACCOUNTING,
    REDUNDANT_WITH,
    said_over,
)

BASE = "https://example.org/synthetic-adapter/vocab/example-accounting.ttl"

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
    carried_as=None,
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
            ("bridge:carriedAs", carried_as),
        )
        if value is not None
    ]
    return PREFIXES_OF_AN_ACCOUNTING + "\n[] " + " ;\n  ".join(written) + " .\n"


def said_about(turtle):
    return said_over(turtle, SHAPES, BASE)


A_MINIMAL_ENTRY_OF_EACH_VERDICT = {
    CARRIED: {},
    CARRIED_IN_PART: {"names_gap": A_GAP},
    REDUNDANT_WITH: {"same_fact_as": THE_PATH_THAT_CARRIES_THE_FACT},
    CONSUMED: {},
    NO_HOME: {"names_gap": A_GAP},
    IGNORED: {"because": A_REASON},
}


def minimal(verdict, **changed):
    return entry(verdict=verdict, **{**A_MINIMAL_ENTRY_OF_EACH_VERDICT[verdict], **changed})


def looks_up(verdict=CONSUMED, **changed):
    return minimal(verdict, **{"lookup_in": A_CONCEPT_MAP, "lookup_names_gap": A_GAP_OF_A_VALUE_NOT_MAPPED, **changed})


AS_THE_ACCESSION = "bridge:asProperty ex:accession"
ON_A_RECORD = "bridge:inRecordClass ex:Record"
IN_AN_EXAMPLE_RECORD = 'bridge:inSourceRecordType "ExampleRecord"'


def carried_as(*stated, verdict=CARRIED):
    return minimal(verdict, carried_as=f"[ {' ; '.join(stated)} ]")


ONE_PROPERTY = (
    "A bridge:carriedAs names exactly one bridge:asProperty, the Cascade property the path's value becomes, by IRI."
)
ONE_RECORD_CLASS = (
    "A bridge:carriedAs names exactly one bridge:inRecordClass, the Cascade class of the record the value is "
    "written on, by IRI."
)
ONE_SOURCE_RECORD_TYPE = (
    "A bridge:carriedAs names at most one bridge:inSourceRecordType, a string: the source's own name for the "
    "kind of record the path is read in, a FHIR resource type or a C-CDA templateId's root."
)


REJECTED = {
    "an entry carrying no verdict": (ONE_VERDICT, entry(verdict=None)),
    "an entry carrying two verdicts": (ONE_VERDICT, entry(verdict=f"{CARRIED}, {CONSUMED}")),
    "an entry whose verdict is outside the scheme of the six": (ONE_VERDICT, entry(verdict="ex:mostly-carried")),
    "an entry carrying no source path": (ONE_SOURCE_PATH, entry(path=None)),
    "an entry carrying two source paths": (
        ONE_SOURCE_PATH,
        entry(path=f"{A_PATH}, {THE_PATH_THAT_CARRIES_THE_FACT}"),
    ),
    "an entry whose source path is an iri rather than a string": (
        ONE_SOURCE_PATH,
        entry(path="<https://example.org/synthetic-adapter/paths/Label>"),
    ),
    "a subject of a source path that is no path entry": (AN_ENTRY_IS_TYPED, entry(typed=False)),
    "a carried entry that names a gap": (
        "An entry whose verdict is bridge:carried names no bridge:namesGap.",
        minimal(CARRIED, names_gap=A_GAP),
    ),
    "a carried entry that names the path carrying the same fact": (
        "An entry whose verdict is bridge:carried names no bridge:sameFactAs.",
        minimal(CARRIED, same_fact_as=THE_PATH_THAT_CARRIES_THE_FACT),
    ),
    "a carried entry that gives a reason": (
        "An entry whose verdict is bridge:carried gives no bridge:because.",
        minimal(CARRIED, because=A_REASON),
    ),
    "a carried in part entry that names no gap": (
        "An entry whose verdict is bridge:carriedInPart names exactly one bridge:namesGap, the gap the loss opens.",
        minimal(CARRIED_IN_PART, names_gap=None),
    ),
    "a carried in part entry that names two gaps": (
        "An entry whose verdict is bridge:carriedInPart names exactly one bridge:namesGap, the gap the loss opens.",
        minimal(CARRIED_IN_PART, names_gap=f"{A_GAP}, {ANOTHER_GAP}"),
    ),
    "a carried in part entry that names the path carrying the same fact": (
        "An entry whose verdict is bridge:carriedInPart names no bridge:sameFactAs.",
        minimal(CARRIED_IN_PART, same_fact_as=THE_PATH_THAT_CARRIES_THE_FACT),
    ),
    "a carried in part entry that gives a reason": (
        "An entry whose verdict is bridge:carriedInPart gives no bridge:because.",
        minimal(CARRIED_IN_PART, because=A_REASON),
    ),
    "a redundant with entry that names no path carrying the same fact": (
        "An entry whose verdict is bridge:redundantWith names exactly one bridge:sameFactAs, "
        "the bridge:sourcePath that carries the fact instead.",
        minimal(REDUNDANT_WITH, same_fact_as=None),
    ),
    "a redundant with entry that names two paths carrying the same fact": (
        "An entry whose verdict is bridge:redundantWith names exactly one bridge:sameFactAs, "
        "the bridge:sourcePath that carries the fact instead.",
        minimal(REDUNDANT_WITH, same_fact_as=f"{THE_PATH_THAT_CARRIES_THE_FACT}, {ANOTHER_PATH_THAT_CARRIES_IT}"),
    ),
    "a redundant with entry that names a gap": (
        "An entry whose verdict is bridge:redundantWith names no bridge:namesGap.",
        minimal(REDUNDANT_WITH, names_gap=A_GAP),
    ),
    "a redundant with entry that gives a reason": (
        "An entry whose verdict is bridge:redundantWith gives no bridge:because.",
        minimal(REDUNDANT_WITH, because=A_REASON),
    ),
    "a consumed entry that names a gap": (
        "An entry whose verdict is bridge:consumed names no bridge:namesGap.",
        minimal(CONSUMED, names_gap=A_GAP),
    ),
    "a consumed entry that names the path carrying the same fact": (
        "An entry whose verdict is bridge:consumed names no bridge:sameFactAs.",
        minimal(CONSUMED, same_fact_as=THE_PATH_THAT_CARRIES_THE_FACT),
    ),
    "a consumed entry that gives a reason": (
        "An entry whose verdict is bridge:consumed gives no bridge:because.",
        minimal(CONSUMED, because=A_REASON),
    ),
    "a no home entry that names no gap": (
        "An entry whose verdict is bridge:noHome names exactly one bridge:namesGap, the gap the missing predicate opens.",
        minimal(NO_HOME, names_gap=None),
    ),
    "a no home entry that names two gaps": (
        "An entry whose verdict is bridge:noHome names exactly one bridge:namesGap, the gap the missing predicate opens.",
        minimal(NO_HOME, names_gap=f"{A_GAP}, {ANOTHER_GAP}"),
    ),
    "a no home entry that names the path carrying the same fact": (
        "An entry whose verdict is bridge:noHome names no bridge:sameFactAs.",
        minimal(NO_HOME, same_fact_as=THE_PATH_THAT_CARRIES_THE_FACT),
    ),
    "a no home entry that gives a reason": (
        "An entry whose verdict is bridge:noHome gives no bridge:because.",
        minimal(NO_HOME, because=A_REASON),
    ),
    "an ignored entry that gives no reason": (
        "An entry whose verdict is bridge:ignored gives exactly one bridge:because, "
        "why the path is deliberately not carried.",
        minimal(IGNORED, because=None),
    ),
    "an ignored entry that gives two reasons": (
        "An entry whose verdict is bridge:ignored gives exactly one bridge:because, "
        "why the path is deliberately not carried.",
        minimal(IGNORED, because=f"{A_REASON}, {ANOTHER_REASON}"),
    ),
    "an ignored entry that names a gap": (
        "An entry whose verdict is bridge:ignored names no bridge:namesGap.",
        minimal(IGNORED, names_gap=A_GAP),
    ),
    "an ignored entry that names the path carrying the same fact": (
        "An entry whose verdict is bridge:ignored names no bridge:sameFactAs.",
        minimal(IGNORED, same_fact_as=THE_PATH_THAT_CARRIES_THE_FACT),
    ),
    "an entry naming a concept map and no gap for a value outside it": (
        "bridge:lookupNamesGap",
        looks_up(lookup_names_gap=None),
    ),
    "an entry naming a gap for a value outside a concept map it names nowhere": (
        "bridge:lookupIn",
        looks_up(lookup_in=None),
    ),
    "an entry naming two concept maps": (
        "bridge:lookupIn",
        looks_up(lookup_in=f"{A_CONCEPT_MAP}, {ANOTHER_CONCEPT_MAP}"),
    ),
    "an entry naming two gaps for a value outside its concept map": (
        "bridge:lookupNamesGap",
        looks_up(lookup_names_gap=f"{A_GAP_OF_A_VALUE_NOT_MAPPED}, {A_GAP}"),
    ),
    "a concept map named as a string rather than by iri": (
        "bridge:lookupIn",
        looks_up(lookup_in='"vocab/example-statuses.ttl"'),
    ),
    "a gap for a value outside a concept map named as a string rather than by iri": (
        "bridge:lookupNamesGap",
        looks_up(lookup_names_gap='"a-status-outside-the-set-the-vocabulary-fixes"'),
    ),
    "a carried as naming no property": (ONE_PROPERTY, carried_as(ON_A_RECORD)),
    "a carried as naming its property as a string": (
        ONE_PROPERTY,
        carried_as('bridge:asProperty "ex:accession"', ON_A_RECORD),
    ),
    "a carried as naming no record class": (ONE_RECORD_CLASS, carried_as(AS_THE_ACCESSION)),
    "a carried as naming two record classes": (
        ONE_RECORD_CLASS,
        carried_as(AS_THE_ACCESSION, "bridge:inRecordClass ex:Record, ex:Note"),
    ),
    "a carried as naming its source record type by iri": (
        ONE_SOURCE_RECORD_TYPE,
        carried_as(AS_THE_ACCESSION, ON_A_RECORD, "bridge:inSourceRecordType ex:ExampleRecord"),
    ),
    "an entry whose path reaches no graph naming what it is carried as": (
        "An entry whose verdict is not bridge:carried or bridge:carriedInPart names no bridge:carriedAs: "
        "its path's value reaches no graph.",
        carried_as(AS_THE_ACCESSION, ON_A_RECORD, verdict=NO_HOME),
    ),
}


class TestTheFormOfAnAccountingEntry:
    """The form of an accounting entry · shapes/bridge.shapes.ttl

    Each verdict of an entry allows and requires different things beside it: a gap, the path carrying the same fact, a
    reason, a lookup. These are the shapes that say so.
    """

    class TestGivenAnEntryThatBreaksOneConstraint:
        @pytest.mark.parametrize(("message", "turtle"), REJECTED.values(), ids=list(REJECTED))
        def test_says_which_constraint_it_breaks(self, message, turtle):
            assert message in said_about(turtle)

    class TestGivenAMinimalEntry:
        @pytest.mark.parametrize("verdict", A_MINIMAL_ENTRY_OF_EACH_VERDICT)
        def test_conforms_under_each_of_the_six_verdicts(self, verdict):
            assert not said_about(minimal(verdict))

    class TestGivenACarriedEntryNamingWhatItIsCarriedAs:
        @pytest.mark.parametrize("verdict", [CARRIED, CARRIED_IN_PART])
        def test_conforms_with_and_without_a_source_record_type(
            self,
            verdict,
        ):
            assert not said_about(carried_as(AS_THE_ACCESSION, ON_A_RECORD, IN_AN_EXAMPLE_RECORD, verdict=verdict))
            assert not said_about(carried_as(AS_THE_ACCESSION, ON_A_RECORD, verdict=verdict))

    class TestGivenHalfALookup:
        @pytest.mark.parametrize("verdict", A_MINIMAL_ENTRY_OF_EACH_VERDICT)
        def test_breaks_a_constraint_under_every_verdict_for_either_half_alone_and_conforms_with_both(self, verdict):
            """breaks a constraint under every verdict for either half alone, and conforms with both"""
            assert "bridge:lookupIn" in said_about(looks_up(verdict, lookup_in=None))
            assert "bridge:lookupNamesGap" in said_about(looks_up(verdict, lookup_names_gap=None))
            assert not said_about(looks_up(verdict))
