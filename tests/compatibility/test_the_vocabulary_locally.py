"""A local run reads an adapter's vocabularies from the spec sibling, as it is on disk."""

from compatibility_world import (
    CRATE,
    VOCABULARY,
    VOCABULARY_FILES,
    VOCABULARY_NAMESPACE,
    VOCABULARY_URL,
    name_vocabulary,
)

AN_EDIT = "# an edit the sibling has not committed\n"
A_COMMIT_THE_SIBLING_DOES_NOT_HOLD = "0" * 40


def adapter_naming(world, files):
    adapter = world.adapter_beside_engine()
    name_vocabulary(adapter / CRATE, VOCABULARY_URL, world.commits[VOCABULARY], files)
    return adapter


def test_the_vocabulary_sibling_is_used_as_it_is_on_disk_and_the_row_names_the_file_differing_from_the_pin(world):
    engine = world.engine_beside_adapter()
    spec = world.workspace / VOCABULARY
    (spec / VOCABULARY_FILES[0]).write_text(AN_EDIT, encoding="utf-8")

    said = world.tool(engine)

    assert f"fake engine: vocabularies {spec}" in said
    assert world.record()["repositories"][VOCABULARY]["how"] == "the sibling's working tree, on main"
    assert world.record()["repositories"][VOCABULARY]["uncommittedEdits"] is True
    assert VOCABULARY_FILES[0] in said
    assert VOCABULARY_FILES[1] not in said
    assert "1 counterpart: 1 hold" in said


def test_a_local_run_stops_with_the_git_command_for_a_missing_vocabulary_sibling(world):
    engine = world.engine([world.url("adapter")])
    world.clone("adapter")
    world.offline()

    said = world.tool(engine, 1)

    assert f"git clone {VOCABULARY_URL}" in said
    assert "Traceback" not in said


def test_the_row_says_the_comparison_was_not_made_where_the_pinned_commit_is_absent(world):
    engine = world.engine_beside_adapter()
    name_vocabulary(world.workspace / "adapter" / CRATE, VOCABULARY_URL, A_COMMIT_THE_SIBLING_DOES_NOT_HOLD)

    said = world.tool(engine)

    assert "the comparison was not made" in said
    assert "1 counterpart: 1 hold" in said


def test_the_run_refuses_an_adapter_naming_a_path_that_is_no_file_of_the_vocabulary(world):
    adapter = adapter_naming(world, ("ontologies/example/v1/absent.ttl",))

    said = world.tool(adapter, 1)

    assert "ontologies/example/v1/absent.ttl" in said


def test_the_run_refuses_an_adapter_whose_named_files_declare_none_of_its_vocabulary(world):
    adapter = adapter_naming(world, (VOCABULARY_FILES[1],))

    said = world.tool(adapter, 1)

    assert VOCABULARY_NAMESPACE in said
