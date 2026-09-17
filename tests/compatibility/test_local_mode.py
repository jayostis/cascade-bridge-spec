"""A local run uses every sibling as it is on disk, fetching nothing."""

from compatibility_world import git, sibling_state, write_compatibility


def nowhere(world):
    """Every origin URL points nowhere: a local run reaches no network."""
    for name in ("engine", "adapter"):
        git("remote", "set-url", "origin", "https://example.invalid/gone.git", cwd=world.workspace / name)


def test_a_sibling_on_another_branch_with_uncommitted_edits_is_used_as_it_is(world):
    engine = world.engine([world.url("adapter")])
    adapter = world.clone("adapter")
    git("checkout", "-q", "-b", "feat/next", cwd=adapter)
    (adapter / "README.md").write_text("an uncommitted edit\n", encoding="utf-8")
    nowhere(world)

    said = world.tool(engine)

    assert "feat/next" in said
    assert "uncommitted edits" in said
    assert sibling_state(adapter)[1] == "feat/next"
    assert world.record()["repositories"]["adapter"]["how"] == "the sibling's working tree, on feat/next"


def test_a_local_run_judges_the_sibling_it_used(world):
    engine = world.engine([world.url("adapter")])
    world.clone("adapter")
    nowhere(world)

    said = world.tool(engine)

    assert "holds" in said
    assert "a result produced from uncommitted edits is feedback, never evidence" not in said


def test_a_local_run_stops_with_the_git_clone_command_for_a_missing_sibling(world):
    said = world.tool(world.engine([world.url("adapter")]), 1)

    assert f"clone it with: git clone {world.url('adapter')}" in said
    assert "Traceback" not in said


def test_a_local_run_writes_no_comment_and_no_table(world):
    engine = world.engine([world.url("adapter")])
    world.clone("adapter")
    nowhere(world)

    world.tool(engine)

    assert world.pull_requests.comments == []
    assert world.table() == ""


def test_an_adapter_is_run_by_the_engine_beside_it(world):
    adapter = world.clone("adapter")
    write_compatibility(adapter, {"mustPassWith": [world.url("engine")]})
    world.clone("engine")
    nowhere(world)

    said = world.tool(adapter)

    assert "fake engine: testing" in said
    assert "holds" in said
