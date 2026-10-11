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


def renamed(name):
    def edit(document):
        document["results"][0]["name"] = name
        return ("results", 0, "name"), "does not match"

    return edit


def a_clock_without(member):
    def edit(document):
        del document["results"][0][member]
        return ("results", 0), f"'{member}' is a required property"

    return edit


def kind_removed(document):
    del document["results"][0]["kind"]
    return ("results", 0), "'kind' is a required property"


def kind_time(document):
    document["results"][0]["kind"] = "time"
    return ("results", 0, "kind"), "is not one of"


def unit_ms(document):
    document["results"][0]["unit"] = "ms"
    return ("results", 0, "unit"), "is not one of"


def negative_value(document):
    document["results"][0]["value"] = -1
    return ("results", 0, "value"), "less than the minimum"


def range_with_an_exponent(document):
    document["results"][0]["range"] = "5e-7-1e-6"
    return ("results", 0, "range"), "does not match"


def no_results(document):
    document["results"] = []
    return ("results",), "non-empty"


def commit_as_a_string(document):
    document["commit"] = document["commit"]["an-engine"]
    return ("commit",), "is not of type 'object'"


def short_sha(document):
    document["commit"]["an-engine"] = "0123456"
    return ("commit", "an-engine"), "does not match"


def profile_removed(document):
    del document["env"]["profile"]
    return ("env",), "'profile' is a required property"


def native_with_a_node_version(document):
    document["env"]["host"] = "native"
    return ("env", "node"), "is not of type 'null'"


def node_without_a_node_version(document):
    document["env"]["node"] = None
    return ("env", "node"), "is not of type 'string'"


def unknown_top_level_member(document):
    document["version"] = 1
    return tuple(), "Additional properties are not allowed"


def timeout_as_a_clock(document):
    index = at(document, "entries-x50/timeout/convert")
    document["results"][index].update(kind="clock", samples=1, range="1800-1800")
    return ("results", index, "kind"), "'output' was expected"


def refusal_in_seconds(document):
    index = at(document, "hostile-deep/refused/depth-limit")
    document["results"][index]["unit"] = "s"
    return ("results", index, "unit"), "'{count}' was expected"


def timeout_as_a_plain_measure(document):
    document["results"][0]["name"] = "entries-x10/timeout"
    return ("results", 0), "should not be valid under"


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
}


def test_the_schema_is_valid_json_schema():
    Draft202012Validator.check_schema(SCHEMA)


def test_the_example_conforms_and_holds_the_rules_the_schema_cannot_say():
    assert not list(VALIDATOR.iter_errors(EXAMPLE))
    names = [entry["name"] for entry in EXAMPLE["results"]]
    assert len(names) == len(set(names))
    for entry in EXAMPLE["results"]:
        if "range" in entry:
            low, high = (float(end) for end in entry["range"].split("-"))
            assert low <= entry["value"] <= high, entry["name"]


@pytest.mark.parametrize("case", REFUSED)
def test_the_result_schema_refuses(case):
    document = copy.deepcopy(EXAMPLE)
    path, said = REFUSED[case](document)
    refusals = [(tuple(error.absolute_path), error.message) for error in VALIDATOR.iter_errors(document)]
    assert any(where == path and said in message for where, message in refusals), refusals
