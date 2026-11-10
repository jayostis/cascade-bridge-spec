import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "bench" / "result.schema.json").read_text(encoding="utf-8"))
EXAMPLE = json.loads((ROOT / "fixtures" / "bench" / "result.json").read_text(encoding="utf-8"))
VALIDATOR = Draft202012Validator(SCHEMA)


def at(document, name):
    return next(index for index, entry in enumerate(document["results"]) if entry["name"] == name)


def renamed(name, validator="anyOf"):
    def edit(document):
        document["results"][0]["name"] = name
        return ("results", 0, "name"), validator

    return edit


def a_clock_without(member):
    def edit(document):
        del document["results"][0][member]
        return ("results", 0), "required", member

    return edit


def kind_removed(document):
    del document["results"][0]["kind"]
    return ("results", 0), "required", "kind"


def kind_time(document):
    document["results"][0]["kind"] = "time"
    return ("results", 0, "kind"), "enum"


def unit_ms(document):
    document["results"][0]["unit"] = "ms"
    return ("results", 0, "unit"), "enum"


def negative_value(document):
    document["results"][0]["value"] = -1
    return ("results", 0, "value"), "minimum"


def range_with_an_exponent(document):
    document["results"][0]["range"] = "5e-7-1e-6"
    return ("results", 0, "range"), "pattern"


def no_results(document):
    document["results"] = []
    return ("results",), "minItems"


def commit_as_a_string(document):
    document["commit"] = document["commit"]["an-engine"]
    return ("commit",), "type"


def short_sha(document):
    document["commit"]["an-engine"] = "0123456"
    return ("commit", "an-engine"), "pattern"


def profile_removed(document):
    del document["env"]["profile"]
    return ("env",), "required", "profile"


def native_with_a_node_version(document):
    document["env"]["host"] = "native"
    return ("env", "node"), "type"


def node_without_a_node_version(document):
    document["env"]["node"] = None
    return ("env", "node"), "type"


def unknown_top_level_member(document):
    document["version"] = 1
    return tuple(), "additionalProperties"


def timeout_as_a_clock(document):
    index = at(document, "entries-x50/timeout/convert")
    document["results"][index].update(kind="clock", samples=1, range="1800-1800")
    return ("results", index, "kind"), "const"


def refusal_in_seconds(document):
    index = at(document, "hostile-deep/refused/documentFailure")
    document["results"][index]["unit"] = "s"
    return ("results", index, "unit"), "const"


def timeout_as_a_plain_measure(document):
    document["results"][0]["name"] = "entries-x10/timeout"
    return ("results", 0), "not"


def refusal_of_an_unlisted_kind(document):
    index = at(document, "hostile-deep/refused/documentFailure")
    document["results"][index]["name"] = "hostile-deep/refused/document"
    return ("results", index, "name"), "pattern"


def refusal_of_a_miscased_kind(document):
    index = at(document, "hostile-deep/refused/documentFailure")
    document["results"][index]["name"] = "hostile-deep/refused/documentfailure"
    return ("results", index, "name"), "pattern"


def refusal_counted_twice(document):
    index = at(document, "hostile-deep/refused/documentFailure")
    document["results"][index]["value"] = 2
    return ("results", index, "value"), "const"


def refusal_as_a_cost(document):
    index = at(document, "hostile-deep/refused/documentFailure")
    document["results"][index]["kind"] = "cost"
    return ("results", index, "kind"), "const"


def timeout_in_a_count(document):
    index = at(document, "entries-x50/timeout/convert")
    document["results"][index]["unit"] = "{count}"
    return ("results", index, "unit"), "const"


def commit_keyed_by_a_record_key(document):
    document["commit"]["owner/name"] = document["commit"]["an-engine"]
    return ("commit",), "pattern"


def unknown_entry_member(document):
    document["results"][0]["note"] = "x"
    return ("results", 0), "additionalProperties"


REFUSED = {
    "a kind removed": kind_removed,
    "a kind of time": kind_time,
    "a clock without samples": a_clock_without("samples"),
    "a clock without a range": a_clock_without("range"),
    "a unit of ms": unit_ms,
    "a one-segment name": renamed("convert"),
    "a four-segment name": renamed("entries-x10/convert/first/again"),
    "an upper-case segment": renamed("entries-x10/Convert/first"),
    "a negative value": negative_value,
    "a range with an exponent": range_with_an_exponent,
    "no results": no_results,
    "a commit as a bare string": commit_as_a_string,
    "a 7-hex commit": short_sha,
    "an env without a profile": profile_removed,
    "a native host with a node version": native_with_a_node_version,
    "a node host without a node version": node_without_a_node_version,
    "an unknown top-level member": unknown_top_level_member,
    "a timeout written as a clock": timeout_as_a_clock,
    "a refusal in seconds": refusal_in_seconds,
    "a timeout as a plain measure": timeout_as_a_plain_measure,
    "a refusal of a kind the library does not define": refusal_of_an_unlisted_kind,
    "a refusal of a kind in the wrong case": refusal_of_a_miscased_kind,
    "a refusal counted twice": refusal_counted_twice,
    "a refusal that is a cost": refusal_as_a_cost,
    "a timeout in a count": timeout_in_a_count,
    "a commit keyed by a record key": commit_keyed_by_a_record_key,
    "an unknown entry member": unknown_entry_member,
}


class TestResultsABenchmarkHarnessWrites:
    """Results a benchmark harness writes · bench/result.schema.json, fixtures/bench/result.json

    A benchmark harness times an engine on the benchmark inputs and writes one JSON file: each result with its name,
    kind, unit and value, the commit of each repository measured, and the machine. The schema refuses a file a reader
    could misread, and the example beside it is a file that passes.
    """

    class TestGivenTheSchemasPatternForTheNameOfARefusedInputsResult:
        """given the schema's pattern for the name of a refused input's result"""

        def test_lists_exactly_the_failure_kinds_of_the_library_result_schema_in_its_order(self):
            """lists exactly the failure kinds of `engine/library-result.schema.json`, in its order"""
            library = json.loads((ROOT / "engine" / "library-result.schema.json").read_text(encoding="utf-8"))
            failing = next(branch for branch in library["oneOf"] if "failure" in branch["properties"])
            kinds = failing["properties"]["failure"]["properties"]["kind"]["enum"]
            refused = next(
                branch["then"]["properties"]["name"]["pattern"]
                for branch in SCHEMA["$defs"]["result"]["allOf"]
                if "then" in branch and "refused" in json.dumps(branch)
            )
            assert refused.endswith("/refused/(" + "|".join(kinds) + ")$")

    class TestGivenTheExample:
        """given the example

        A schema cannot say that each result has a name of its own, or that a value lies within its range.
        """

        def test_conforms_to_the_schema(self):
            assert not list(VALIDATOR.iter_errors(EXAMPLE))

        def test_gives_every_result_a_name_of_its_own(self):
            names = [entry["name"] for entry in EXAMPLE["results"]]
            assert len(names) == len(set(names))

        def test_keeps_each_value_that_has_a_range_within_it(self):
            for entry in EXAMPLE["results"]:
                if "range" in entry:
                    low, high = (float(end) for end in entry["range"].split("-"))
                    assert low <= entry["value"] <= high, entry["name"]

    class TestGivenTheExampleChangedInOneWay:
        """given the example changed in one way

        A result's kind is `clock` (a time, which carries its samples and their range), `cost` or `output`; its unit is
        `s`, `By` or `{count}`. An input that timed out is an output in seconds named `<input>/timeout/<what>`, and an
        input the engine refused is an output counted once, named `<input>/refused/<failure kind>`. A keyword is the
        word of JSON Schema that states a rule, such as `enum`, `required` or `pattern`.
        """

        @pytest.mark.parametrize("case", REFUSED)
        def test_is_refused_at_the_member_changed_by_the_keyword_that_forbids_it(self, case):
            """refuses it at the member changed, by the keyword that forbids it"""
            document = copy.deepcopy(EXAMPLE)
            path, keyword, *member = REFUSED[case](document)
            member = member[0] if member else None
            refusals = [
                (tuple(error.absolute_path), error.validator, error.message)
                for error in VALIDATOR.iter_errors(document)
            ]
            assert any(
                where == path and validator == keyword and (not member or f"'{member}'" in message)
                for where, validator, message in refusals
            ), refusals


class TestFilesOfTheSpecificationThatParse:
    """Files of the specification that parse · **/*.ttl, **/*.nt, shapes/, bench/result.schema.json"""

    class TestGivenTheResultSchema:
        """given `bench/result.schema.json`"""

        def test_is_valid_json_schema(self):
            """is valid JSON Schema"""
            Draft202012Validator.check_schema(SCHEMA)
