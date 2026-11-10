"""A local run uses every sibling as it is on disk, fetching nothing."""

from compatibility_world import git


class TestRunningOnADevelopersMachine:
    """Running on a developer's machine · python3 scripts/compatibility.py <dir>

    A local run reads no pull request: it uses every sibling checkout as it is on disk, uncommitted edits included.
    """

    class TestGivenASiblingOnAnotherBranchWithUncommittedEdits:
        def test_is_used_as_it_is(self, world):
            engine = world.engine_beside_adapter()
            adapter = world.workspace / "adapter"
            git("checkout", "-q", "-b", "feat/next", cwd=adapter)
            (adapter / "README.md").write_text("an uncommitted edit\n", encoding="utf-8")

            said = world.tool(engine)

            assert "feat/next" in said
            assert "uncommitted edits): holds" in said
            assert "a result produced from uncommitted edits is feedback, never evidence" in said
            assert git("symbolic-ref", "--short", "HEAD", cwd=adapter) == "feat/next"
            assert world.record()["repositories"]["adapter"]["how"] == "the sibling's working tree, on feat/next"

    class TestGivenAMissingSibling:
        def test_stops_with_the_git_clone_command_for_it(self, world):
            """stops with the `git clone` command for it"""
            said = world.tool(world.engine([world.url("adapter")]), 1)

            assert f"clone it with: git clone {world.url('adapter')}" in said
            assert "Traceback" not in said

    class TestGivenAnAdapterWithAnEngineBesideIt:
        def test_is_run_by_that_engine(self, world):
            said = world.tool(world.adapter_beside_engine(), in_a_process=True)

            assert "rocrate-validator" in said
            assert "fake engine: testing" in said
            assert "1 counterpart: 1 hold" in said

    class TestGivenALocalRun:
        def test_names_the_repository_each_line_is_about_writing_no_table(self, world):
            """names the repository each line is about, writing no table

            Locally there is no URL for the repository under test or the specification; a line still names one.
            """
            said = world.tool(world.engine_beside_adapter())

            assert "engine is" in said
            assert "cascade-bridge-spec is" in said
            assert world.table() == ""
