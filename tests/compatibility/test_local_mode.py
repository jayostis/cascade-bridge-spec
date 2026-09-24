"""A local run uses every sibling as it is on disk, fetching nothing."""

from compatibility_world import git


def test_a_sibling_on_another_branch_with_uncommitted_edits_is_used_as_it_is(world):
    engine = world.engine_beside_adapter()
    adapter = world.workspace / "adapter"
    git("checkout", "-q", "-b", "feat/next", cwd=adapter)
    (adapter / "README.md").write_text("an uncommitted edit\n", encoding="utf-8")

    said = world.tool(engine)

    assert "feat/next" in said
    assert "uncommitted edits" in said
    assert git("symbolic-ref", "--short", "HEAD", cwd=adapter) == "feat/next"
    assert world.record()["repositories"]["adapter"]["how"] == "the sibling's working tree, on feat/next"


def test_a_local_run_stops_with_the_git_clone_command_for_a_missing_sibling(world):
    said = world.tool(world.engine([world.url("adapter")]), 1)

    assert f"clone it with: git clone {world.url('adapter')}" in said
    assert "Traceback" not in said


def test_an_adapter_is_run_by_the_engine_beside_it(world):
    said = world.tool(world.adapter_beside_engine(), in_a_process=True)

    assert "rocrate-validator" in said
    assert "fake engine: testing" in said
    assert "1 counterpart: 1 hold" in said


def test_a_local_run_names_the_repository_each_line_is_about_and_writes_no_table(world):
    """Locally there is no URL for the repository under test or the specification; a line still names one."""
    said = world.tool(world.engine_beside_adapter())

    assert "engine is" in said
    assert "cascade-bridge-spec is" in said
    assert world.table() == ""
