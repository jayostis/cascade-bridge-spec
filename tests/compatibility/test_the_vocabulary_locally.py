"""A local run reads an adapter's vocabularies from the sibling named as the repository it names, as it is on disk."""

from compatibility_world import (
    CRATE,
    VOCABULARY,
    VOCABULARY_FILES,
    VOCABULARY_NAMESPACE,
    VOCABULARY_URL,
    name_another_vocabulary,
    name_vocabulary,
)

AN_EDIT = "# an edit the sibling has not committed\n"


def adapter_naming(world, files):
    adapter = world.adapter_beside_engine()
    name_vocabulary(adapter / CRATE, VOCABULARY_URL, files)
    return adapter


def test_the_vocabulary_sibling_is_used_as_it_is_on_disk(world):
    engine = world.engine_beside_adapter()
    spec = world.workspace / VOCABULARY
    (spec / VOCABULARY_FILES[0]).write_text(AN_EDIT, encoding="utf-8")

    said = world.tool(engine)

    assert f"fake engine: vocabularies {spec}" in said
    assert world.record()["repositories"][VOCABULARY]["how"] == "the sibling's working tree, on main"
    assert world.record()["repositories"][VOCABULARY]["uncommittedEdits"] is True
    assert "1 counterpart: 1 hold" in said


def test_a_local_run_stops_with_the_git_command_for_a_missing_vocabulary_sibling(world):
    engine = world.engine([world.url("adapter")])
    world.clone("adapter")
    world.offline()

    said = world.tool(engine, 1)

    assert f"git clone {VOCABULARY_URL}" in said
    assert "Traceback" not in said


def test_the_run_refuses_an_adapter_naming_a_path_that_is_no_file_of_the_vocabulary(world):
    adapter = adapter_naming(world, ("ontologies/example/v1/absent.ttl",))

    said = world.tool(adapter, 1)

    assert "ontologies/example/v1/absent.ttl" in said


def test_the_run_refuses_an_adapter_whose_named_files_declare_none_of_its_vocabulary(world):
    adapter = adapter_naming(world, (VOCABULARY_FILES[1],))

    said = world.tool(adapter, 1)

    assert VOCABULARY_NAMESPACE in said


def test_another_vocabulary_repository_an_adapter_names_is_read_from_the_sibling_named_as_it(world):
    name_another_vocabulary(world, "cascade-vocabulary")
    engine = world.engine([world.url("adapter")])
    world.clone("adapter")
    sibling = world.clone("cascade-vocabulary")
    world.offline()

    said = world.tool(engine)

    assert f"fake engine: vocabularies {sibling}" in said
    assert "1 counterpart: 1 hold" in said
