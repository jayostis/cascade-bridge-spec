"""compatibility.json's form: what a run refuses before it picks anything."""

import pytest

from compatibility_world import write_compatibility

PICKED_WHEN_THE_CHECK_RUNS = "picked when the check runs"


def adapter_naming_engine(world):
    adapter = world.clone("adapter")
    write_compatibility(adapter, {"mustPassWith": [world.url("engine")]})
    world.clone("engine")
    return adapter


def test_an_engines_file_naming_its_counterpart_by_repository_url_passes(world):
    world.clone("adapter")
    said = world.tool(world.engine([world.url("adapter")]))
    assert "1 counterpart: 1 hold" in said


def test_an_adapters_file_naming_its_counterpart_by_repository_url_passes(world):
    said = world.tool(adapter_naming_engine(world))
    assert "1 counterpart: 1 hold" in said


def test_an_adapter_with_no_compatibility_json_is_nothing_to_check_not_a_pass(world):
    said = world.tool(world.clone("adapter"))
    assert "lists no counterpart: nothing to check" in said
    assert "\nPASS\n" not in said


def test_an_entry_written_as_an_object_is_refused_saying_the_version_is_picked_when_the_check_runs(world):
    entry = {"codeRepository": world.url("adapter"), "tag": "v1"}
    said = world.tool(world.engine([entry]), 1)
    assert PICKED_WHEN_THE_CHECK_RUNS in said


def test_a_key_the_context_does_not_define_is_refused_naming_it(world):
    engine = world.engine([world.url("adapter")], specVersion="v1-draft")
    said = world.tool(engine, 1)
    assert "specVersion is not a key the context defines" in said


@pytest.mark.parametrize(
    "overrides, says",
    [
        pytest.param({"setup": None}, "carries setup and command", id="an engine's file carrying no setup"),
        pytest.param({"command": None}, "carries setup and command", id="an engine's file carrying no command"),
        pytest.param({"setup": "cargo build"}, "argument vector", id="an argument vector written as a string"),
        pytest.param({"mustPassWith": "https://example.org/x"}, "written as a JSON array", id="entries not a list"),
    ],
)
def test_a_file_of_neither_form_is_refused(world, overrides, says):
    said = world.tool(world.engine([world.url("adapter")], **overrides), 1)
    assert says in said


def test_an_adapters_file_carrying_setup_or_command_is_refused(world):
    adapter = adapter_naming_engine(world)
    write_compatibility(adapter, {"mustPassWith": [world.url("engine")], "command": ["node", "cli.js"]})
    said = world.tool(adapter, 1)
    assert "an adapter's compatibility.json carries no" in said


def test_a_file_whose_context_is_not_the_specifications_is_refused(world):
    engine = world.engine([world.url("adapter")])
    (engine / "compatibility.json").write_text('{"@context": "https://example.org/other"}', encoding="utf-8")
    said = world.tool(engine, 1)
    assert "its @context is" in said


def test_two_counterparts_whose_repositories_share_a_name_are_refused(world):
    twice = [world.url("adapter"), "https://example.org/elsewhere/adapter"]
    said = world.tool(world.engine(twice), 1)
    assert "at most once" in said


def test_a_counterpart_named_cascade_bridge_spec_is_refused(world):
    said = world.tool(world.engine([world.url("cascade-bridge-spec")]), 1)
    assert "No repository in mustPassWith is named cascade-bridge-spec" in said
