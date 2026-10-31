"""What a description can name, and what a run may not let that do to its record."""

import pytest

from compatibility_world import MATCHING, depends_on, engine_document, git, write_compatibility


def writing(name, text=None):
    return lambda path: (path / name).write_text(f"{text or name}\n", encoding="utf-8")


def engine_checked_out_as_ci_does(world, body):
    """Pull request #1 under test, in a checkout of one commit, as actions/checkout leaves it."""
    world.pull_request("engine", 1, body=body)
    engine = world.workspace / "engine"
    git("clone", "-q", "--depth", "1", world.url("engine"), str(engine))
    write_compatibility(engine, engine_document([world.url("adapter")]))
    return engine, world.event(1)


def test_a_pull_request_naming_one_in_its_own_repository_is_tested_with_it_merged_in(world):
    """The pull request named in the repository under test is merged into the checkout under test, as Zuul does."""
    head = world.pull_request("engine", 2, body=depends_on("engine", 1), fill=writing("TWO"))
    world.commit_on_main("engine", "MOVED")  # the base the two meet at is below the one commit checked out
    engine, event = engine_checked_out_as_ci_does(world, depends_on("engine", 2))

    world.tool(engine, **world.ci(event=event))

    assert (engine / "TWO").is_file()
    git("merge-base", "--is-ancestor", head, "HEAD", cwd=engine)
    row = world.record()["repositories"]["engine"]
    assert row["role"] == "under test"
    assert row["how"] == "pull request #1 merged into main, and #2 merged into it"
    assert row["commit"] == git("rev-parse", "HEAD", cwd=engine)
    assert "not used" not in world.table()


def test_a_repository_named_in_another_case_is_the_same_repository(world):
    """GitHub reads owner and repository names whatever their case, so a line naming one so is the same line."""
    world.pull_request("engine", 2, body=depends_on("ENGINE", 1, owner="JAYOSTIS"), fill=writing("TWO"))
    engine, event = engine_checked_out_as_ci_does(world, depends_on("Engine", 2, owner="JayOstis"))

    world.tool(engine, **world.ci(event=event))

    assert (engine / "TWO").is_file()
    assert world.record()["repositories"]["engine"]["how"] == "pull request #1 merged into main, and #2 merged into it"


def test_a_cycle_of_three_in_the_repository_under_test_merges_the_other_two_in_the_order_of_their_numbers(world):
    """Reached through #3's own line, and merged in by number whichever line named it first."""
    two = world.pull_request("engine", 2, body=depends_on("engine", 1), fill=writing("TWO"))
    three = world.pull_request("engine", 3, body=depends_on("engine", 2), fill=writing("THREE"))
    engine, event = engine_checked_out_as_ci_does(world, depends_on("engine", 3))

    world.tool(engine, **world.ci(event=event))

    assert git("rev-parse", "HEAD^1^2", "HEAD^2", cwd=engine).split() == [two, three]
    assert world.record()["repositories"]["engine"]["how"] == (
        "pull request #1 merged into main, and #2 and #3 merged into it"
    )


def test_a_named_pull_request_in_the_repository_under_test_merged_since_the_runs_event_is_merged_in(world):
    """A rerun keeps the commit its event checked out, which a pull request that merged since does not hold."""
    world.pull_request("engine", 2, fill=writing("TWO"), state="closed", merged=True)
    engine, event = engine_checked_out_as_ci_does(world, depends_on("engine", 2))

    world.tool(engine, **world.ci(event=event))

    assert (engine / "TWO").is_file()


def test_a_named_pull_request_already_in_the_checkout_is_not_said_to_be_merged_in(world):
    world.pull_request("engine", 2, fill=writing("TWO"), state="closed", merged=True)
    git("merge", "-q", "--no-ff", "--no-edit", "pull/2", cwd=world.origin("engine"))
    engine, event = engine_checked_out_as_ci_does(world, depends_on("engine", 2))

    world.tool(engine, **world.ci(event=event))

    assert world.record()["repositories"]["engine"]["how"] == "pull request #1 merged into main"
    assert "rerun it once" not in world.table()


def test_a_named_pull_request_in_the_repository_under_test_is_merged_in_at_the_head_the_run_read(world):
    """A push after the run read the pull request is not tested unannounced."""
    world.pull_request("engine", 2, fill=writing("TWO"))
    later = world.branch("engine", "later", fill=writing("LATER"))
    git("update-ref", "refs/pull/2/head", later, cwd=world.origin("engine"))
    engine, event = engine_checked_out_as_ci_does(world, depends_on("engine", 2))

    world.tool(engine, **world.ci(event=event))

    assert (engine / "TWO").is_file()
    assert not (engine / "LATER").exists()


def test_a_named_open_pull_request_from_a_fork_is_not_merged_into_the_checkout_under_test(world):
    """The checkout under test runs with the job's token, which a fork's code is not handed."""
    world.pull_request("engine", 2, fill=writing("TWO"), fork=True)
    engine, event = engine_checked_out_as_ci_does(world, depends_on("engine", 2))

    said = world.tool(engine, 1, **world.ci(event=event))

    assert "jayostis/engine/pull/2 is from a-fork-owner/engine" in said
    assert not (engine / "TWO").exists()


@pytest.mark.parametrize("state", ["open", "closed"])
def test_a_pull_request_here_reached_only_through_another_repository_is_not_merged_in(world, state):
    """Two pull requests here that follow one vocabulary pull request are not bundled by it: each names the other."""
    world.pull_request("engine", 2, fill=writing("TWO"), state=state)
    world.pull_request("adapter", 7, body=depends_on("engine", 1) + depends_on("engine", 2))
    engine, event = engine_checked_out_as_ci_does(world, depends_on("adapter", 7))

    world.tool(engine, **world.ci(event=event))

    assert not (engine / "TWO").exists()
    [under_test] = [row for row in world.record()["repositories"].values() if row["role"] == "under test"]
    assert under_test["how"] == "pull request #1 merged into main"
    assert "jayostis/engine/pull/2, reached only through another repository's pull request" in world.table()


def test_two_named_pull_requests_in_the_repository_under_test_that_conflict_fail_the_check_naming_them(world):
    world.pull_request("engine", 2, fill=writing("SHARED", "two"))
    world.pull_request("engine", 3, fill=writing("SHARED", "three"))
    engine, event = engine_checked_out_as_ci_does(world, depends_on("engine", 2) + depends_on("engine", 3))

    said = world.tool(engine, 1, **world.ci(event=event))

    assert (
        "jayostis/engine/pull/3 does not merge cleanly into pull request #1 merged into main, and #2 merged into it"
        in said
    )


def test_a_named_pull_request_in_the_repository_under_test_landing_on_another_branch_fails_the_check(world):
    world.branch("engine", "stable/x")
    world.pull_request("engine", 2, base="stable/x", fill=writing("TWO"))
    engine, event = engine_checked_out_as_ci_does(world, depends_on("engine", 2))

    said = world.tool(engine, 1, **world.ci(event=event))

    assert "jayostis/engine/pull/2 targets stable/x, and the pull request under test main" in said


def test_a_named_pull_request_in_the_repository_under_test_closed_without_merging_fails_naming_the_line(world):
    world.pull_request("engine", 2, state="closed", fill=writing("TWO"))
    world.pull_request("engine", 3, body=depends_on("engine", 2), fill=writing("THREE"))
    engine, event = engine_checked_out_as_ci_does(world, depends_on("engine", 3))

    said = world.tool(engine, 1, **world.ci(event=event))

    assert (
        "jayostis/engine/pull/2 is closed without merging: cut the Depends-On: line naming it in jayostis/engine/pull/3"
        in said
    )


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


def test_the_version_picked_says_what_was_merged_in_before_it_was_handed_the_run(world):
    """The run merges before it hops, and the version it hops to runs again on that checkout, finding its merges."""
    world.pull_request("engine", 2, fill=writing("TWO"))
    engine, event = engine_checked_out_as_ci_does(world, depends_on("engine", 2))
    world.tool(engine, **world.ci(event=event))

    world.tool(engine, **world.ci(event=event))

    assert world.record()["repositories"]["engine"]["how"] == "pull request #1 merged into main, and #2 merged into it"
