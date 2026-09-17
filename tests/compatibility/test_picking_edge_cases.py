"""What a description can name, and what a run may not let that do to its record."""

from test_picking_versions import MATCHING, depends_on, engine_under_test


def test_a_named_pull_request_in_the_repository_under_test_leaves_its_own_row_alone(world):
    """It is checked out already: the pull request under test is what the run tests."""
    world.pull_request("engine", 2)
    engine, event = engine_under_test(world, body=depends_on("engine", 2))

    world.tool(engine, **world.ci(event=event))

    row = world.record()["repositories"]["engine"]
    assert row["role"] == "under test"
    assert row["how"] == "pull request #1 merged into main"


def test_a_cycle_between_two_named_pull_requests_fails_the_check(world):
    """Both are reached from the pull request under test, and the cycle is the edge between them."""
    world.pull_request("adapter", 7, body=depends_on("cascade-bridge-spec", 3))
    world.pull_request("cascade-bridge-spec", 3, body=depends_on("adapter", 7))
    engine, event = engine_under_test(
        world, body=depends_on("cascade-bridge-spec", 3) + depends_on("adapter", 7)
    )

    said = world.tool(engine, 1, **world.ci(event=event))

    assert "cycle" in said
    assert "adapter/pull/7" in said and "cascade-bridge-spec/pull/3" in said


def test_the_branch_a_pull_request_targets_is_read_when_the_job_runs(world):
    """An event file is frozen at the event that started the run; the API is not."""
    world.branch("adapter", "stable/x", fill=lambda path: (path / "STABLE").write_text("stable\n"))
    world.branch("cascade-bridge-spec", "stable/x")
    engine, event = engine_under_test(world)
    world.pull_requests.get("engine", 1)["base"]["ref"] = "stable/x"

    world.tool(engine, **world.ci(event=event, branch="main"))

    assert world.record()["repositories"]["adapter"]["how"] == "stable/x, the branch matching the pull request's target"


def test_a_closed_pull_request_in_a_repository_the_run_checks_nothing_out_from_never_fails_the_check(world):
    world.pull_request("cascade-cli", 4, state="closed")
    engine, event = engine_under_test(world, body=depends_on("cascade-cli", 4))

    said = world.tool(engine, **world.ci(event=event))

    assert "cascade-cli" in world.table()
    assert world.record()["repositories"]["adapter"]["how"] == MATCHING
    assert "closed without merging" not in said


def test_a_pull_request_the_api_does_not_serve_in_such_a_repository_never_fails_the_check(world):
    engine, event = engine_under_test(world, body=depends_on("cascade-cli", 404))

    world.tool(engine, **world.ci(event=event))

    assert "cascade-cli" in world.table()


def test_two_repositories_of_one_name_each_keep_their_row(world):
    world.pull_request("adapter", 7)
    engine, event = engine_under_test(world, body="Depends-On: https://github.com/elsewhere/adapter/pull/9\n")
    world.pull_requests.open("adapter", 9, base="main")

    world.tool(engine, **world.ci(event=event))

    repositories = world.record()["repositories"]
    assert len([name for name in repositories if name.endswith("adapter")]) == 2
