"""What a description can name, and what a run may not let that do to its record."""

from compatibility_world import MATCHING, depends_on


def test_a_named_pull_request_in_the_repository_under_test_leaves_its_own_row_alone_and_is_listed_as_not_used(world):
    """The pull request under test is what the run tests; the named one is merged into nothing."""
    world.pull_request("engine", 2)
    engine, event = world.engine_under_test(body=depends_on("engine", 2))

    world.tool(engine, **world.ci(event=event))

    row = world.record()["repositories"]["jayostis/engine"]
    assert row["role"] == "under test"
    assert row["how"] == "pull request #1 merged into main"
    table = world.table()
    assert "engine/pull/2" in table
    assert "not used" in table


def test_a_cycle_between_two_named_pull_requests_picks_both(world):
    world.pull_request("adapter", 7, body=depends_on("cascade-bridge-spec", 3))
    world.pull_request("cascade-bridge-spec", 3, body=depends_on("adapter", 7))
    engine, event = world.engine_under_test(body=depends_on("cascade-bridge-spec", 3) + depends_on("adapter", 7))

    world.tool(engine, **world.ci(event=event))

    repositories = world.record()["repositories"]
    assert repositories["adapter"]["how"] == "pull request #7 merged into main"
    assert repositories["cascade-bridge-spec"]["how"] == "pull request #3 merged into main"


def test_the_branch_a_pull_request_targets_is_read_when_the_job_runs(world):
    """An event file is frozen at the event that started the run; the API is not."""
    world.branch("adapter", "stable/x", fill=lambda path: (path / "STABLE").write_text("stable\n"))
    world.branch("cascade-bridge-spec", "stable/x")
    engine, event = world.engine_under_test()
    world.pull_requests.get("engine", 1)["base"]["ref"] = "stable/x"

    world.tool(engine, **world.ci(event=event, branch="main"))

    assert world.record()["repositories"]["adapter"]["how"] == "stable/x, the branch matching the pull request's target"


def test_a_closed_pull_request_in_a_repository_the_run_checks_nothing_out_from_never_fails_the_check(world):
    world.pull_request("cascade-cli", 4, state="closed")
    engine, event = world.engine_under_test(body=depends_on("cascade-cli", 4))

    said = world.tool(engine, **world.ci(event=event))

    assert "cascade-cli" in world.table()
    assert world.record()["repositories"]["adapter"]["how"] == MATCHING
    assert "closed without merging" not in said


def test_a_pull_request_the_api_does_not_serve_in_such_a_repository_never_fails_the_check(world):
    engine, event = world.engine_under_test(body=depends_on("cascade-cli", 404))

    world.tool(engine, **world.ci(event=event))

    assert "cascade-cli" in world.table()


def test_two_repositories_of_one_name_each_keep_their_row(world):
    world.pull_request("adapter", 7)
    engine, event = world.engine_under_test(body=depends_on("adapter", 9, owner="elsewhere"))
    world.pull_requests.open("adapter", 9, base="main")

    world.tool(engine, **world.ci(event=event))

    repositories = world.record()["repositories"]
    assert len([name for name in repositories if name.endswith("adapter")]) == 2


def test_an_unreadable_pull_request_in_a_counterpart_repository_fails_the_check(world):
    """A typo or a deleted pull request names a version the run cannot have."""
    engine, event = world.engine_under_test(body=depends_on("adapter", 404))

    said = world.tool(engine, 1, **world.ci(event=event))

    assert "adapter/pull/404 could not be read" in said


def test_a_spent_rate_limit_says_so_rather_than_reading_like_a_wrong_pull_request_number(world):
    world.pull_requests.refuse("adapter", 7, 403, {"x-ratelimit-remaining": "0"})
    engine, event = world.engine_under_test(body=depends_on("adapter", 7))

    said = world.tool(engine, 1, **world.ci(event=event))

    assert "adapter/pull/7 could not be read" in said
    assert "rate limit" in said


def test_an_error_of_githubs_own_says_so_rather_than_reading_like_a_wrong_pull_request_number(world):
    world.pull_requests.refuse("adapter", 7, 502)
    engine, event = world.engine_under_test(body=depends_on("adapter", 7))

    said = world.tool(engine, 1, **world.ci(event=event))

    assert "adapter/pull/7 could not be read" in said
    assert "GitHub answered with an error of its own" in said


def test_a_named_specification_pull_request_is_used_rather_than_listed_as_not_used(world):
    world.pull_request("cascade-bridge-spec", 3)
    engine, event = world.engine_under_test(body=depends_on("cascade-bridge-spec", 3))

    world.tool(engine, **world.ci(event=event))

    specification = world.record()["repositories"]["cascade-bridge-spec"]
    assert specification["role"] == "specification"
    assert specification["how"] == "pull request #3 merged into main"
    assert "not used" not in world.table()
