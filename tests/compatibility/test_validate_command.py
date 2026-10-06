"""compatibility.json's form: what a run refuses before it picks anything."""

import json

import pytest

from compatibility_tool.console import Stop
from compatibility_tool.document import named_repositories, problems
from compatibility_world import CONTEXT_IRI, CRATE, VOCABULARY, engine_document

PICKED_WHEN_THE_CHECK_RUNS = "picked when the check runs"
ADAPTER = "https://github.com/jayostis/adapter"


def refused(directory, **document):
    return "\n".join(problems(directory, {"@context": CONTEXT_IRI, **engine_document([ADAPTER], **document)}))


def test_an_adapter_with_no_compatibility_json_is_nothing_to_check_not_a_pass(world):
    adapter = world.clone("adapter")
    world.clone(VOCABULARY)
    said = world.tool(adapter)
    assert "lists no counterpart: nothing to check" in said
    assert "\nPASS\n" not in said


def test_a_key_the_context_does_not_define_is_refused_naming_it(world):
    engine = world.engine([world.url("adapter")], specVersion="v1-draft")
    said = world.tool(engine, 1)
    assert "specVersion is not a key the context defines" in said


def test_an_entry_written_as_an_object_is_refused_saying_the_version_is_picked_when_the_check_runs(tmp_path):
    assert PICKED_WHEN_THE_CHECK_RUNS in refused(tmp_path, mustPassWith=[{"codeRepository": ADAPTER, "tag": "v1"}])


@pytest.mark.parametrize(
    "overrides, says",
    [
        pytest.param({"setup": None}, "carries setup and command", id="a host carrying no setup"),
        pytest.param({"command": None}, "carries setup and command", id="a host carrying no command"),
        pytest.param({"setup": "cargo build"}, "argument vector", id="an argument vector written as a string"),
        pytest.param({"mustPassWith": "https://example.org/x"}, "written as a JSON array", id="entries not a list"),
    ],
)
def test_a_file_of_neither_form_is_refused(tmp_path, overrides, says):
    assert says in refused(tmp_path, **overrides)


@pytest.mark.parametrize(
    "host",
    [pytest.param(None, id="no host key"), pytest.param([], id="an empty list of hosts")],
)
def test_an_engines_file_naming_no_host_is_refused_saying_an_engine_names_one(tmp_path, host):
    said = refused(tmp_path, host=host)
    assert "names at least one host" in said
    assert "not a key the context defines" not in said


def test_an_adapters_file_carrying_setup_or_command_is_refused(tmp_path):
    (tmp_path / CRATE).write_text("{}", encoding="utf-8")
    document = {"@context": CONTEXT_IRI, "mustPassWith": [ADAPTER], "command": ["node", "cli.js"]}
    assert "an adapter's compatibility.json carries no" in "\n".join(problems(tmp_path, document))


def test_a_file_whose_context_is_not_the_specifications_is_refused(tmp_path):
    assert "its @context is" in "\n".join(problems(tmp_path, {"@context": "https://example.org/other"}))


def test_two_counterparts_whose_repositories_share_a_name_are_refused(tmp_path):
    assert "at most once" in refused(tmp_path, mustPassWith=[ADAPTER, "https://example.org/elsewhere/adapter"])


def test_a_counterpart_named_cascade_bridge_spec_is_refused(tmp_path):
    said = refused(tmp_path, mustPassWith=["https://github.com/jayostis/cascade-bridge-spec"])
    assert "No repository in mustPassWith is named cascade-bridge-spec" in said


@pytest.mark.parametrize(
    "document, named, says",
    [
        pytest.param({"mustPassWith": [ADAPTER]}, ADAPTER, "names no mustPassWith", id="mustPassWith"),
        pytest.param(
            {"mustPassWith": None},
            "https://github.com/jayostis/cascade-bridge-spec",
            "is named cascade-bridge-spec",
            id="a repository",
        ),
    ],
)
def test_a_runtimes_file_is_refused_where_it_names_counterparts_or_a_repository_clashes(
    tmp_path, document, named, says
):
    entry = {"repository": named}
    (tmp_path / "cascade-runtime.json").write_text(json.dumps({"vocabulary": entry, "adapters": []}), encoding="utf-8")
    assert says in "\n".join(problems(tmp_path, {"@context": CONTEXT_IRI, **engine_document([], **document)}))


def test_a_runtimes_adapters_written_as_an_object_stop_the_run(tmp_path):
    entry = {"repository": ADAPTER}
    (tmp_path / "cascade-runtime.json").write_text(
        json.dumps({"vocabulary": entry, "adapters": entry}), encoding="utf-8"
    )
    with pytest.raises(Stop, match="adapters"):
        named_repositories(tmp_path)


@pytest.mark.parametrize("must_pass_with", [None, []], ids=["no mustPassWith", "an empty one"])
def test_a_vocabulary_naming_no_runtime_is_refused_so_an_adapter_typed_wrongly_is_not_passed(tmp_path, must_pass_with):
    (tmp_path / CRATE).write_text('{"@graph": [{"@id": "./", "@type": "Dataset"}]}', encoding="utf-8")
    document = {"@context": CONTEXT_IRI} if must_pass_with is None else {"@context": CONTEXT_IRI, "mustPassWith": []}
    assert "names a runtime in mustPassWith" in "\n".join(problems(tmp_path, document))
