"""Which version of each repository a run uses: #32's model, as Zuul checks out a required project."""

from compatibility_world import git


def depends_on(repository, number):
    return f"Some description.\n\nDepends-On: https://github.com/jayostis/{repository}/pull/{number}\n"


def engine_under_test(world, number=1, body="", base="main"):
    world.pull_request("engine", number, body=body, base=base)
    return world.engine([world.url("adapter")]), world.event(number)


def test_a_named_pull_request_is_merged_into_the_branch_it_targets(world):
    head = world.pull_request("adapter", 7, fill=lambda path: (path / "NOTICE").write_text("named\n"))
    engine, event = engine_under_test(world, body=depends_on("adapter", 7))

    world.tool(engine, **world.ci(event=event))

    adapter = world.record()["repositories"]["adapter"]
    assert adapter["how"] == "pull request #7 merged into main"
    assert (world.workspace / "adapter" / "NOTICE").read_text() == "named\n"
    assert adapter["commit"] != head, "the run uses the merge, not the pull request's head"


def test_a_pull_request_named_by_a_named_pull_request_is_followed(world):
    world.pull_request("cascade-bridge-spec", 3)
    world.pull_request("adapter", 7, body=depends_on("cascade-bridge-spec", 3))
    engine, event = engine_under_test(world, body=depends_on("adapter", 7))

    world.tool(engine, **world.ci(event=event))

    specification = world.record()["repositories"]["cascade-bridge-spec"]
    assert specification["how"] == "pull request #3 merged into main"


def test_two_named_pull_requests_targeting_one_branch_are_both_merged_in(world):
    world.pull_request("adapter", 7, fill=lambda path: (path / "SEVEN").write_text("seven\n"))
    world.pull_request("adapter", 8, fill=lambda path: (path / "EIGHT").write_text("eight\n"))
    engine, event = engine_under_test(world, body=depends_on("adapter", 7) + depends_on("adapter", 8))

    world.tool(engine, **world.ci(event=event))

    assert world.record()["repositories"]["adapter"]["how"] == "pull requests #7 and #8 merged into main"
    assert (world.workspace / "adapter" / "SEVEN").exists()
    assert (world.workspace / "adapter" / "EIGHT").exists()


def test_two_named_pull_requests_targeting_different_branches_fail_the_check_naming_them(world):
    world.branch("adapter", "stable/x")
    world.pull_request("adapter", 7)
    world.pull_request("adapter", 8, base="stable/x")
    engine, event = engine_under_test(world, body=depends_on("adapter", 7) + depends_on("adapter", 8))

    said = world.tool(engine, 1, **world.ci(event=event))

    assert "adapter/pull/7" in said and "adapter/pull/8" in said
    assert "target one branch" in said


def test_a_named_pull_request_that_conflicts_fails_the_check_naming_it(world):
    world.pull_request("adapter", 7, fill=lambda path: (path / "README.md").write_text("seven\n"))
    world.pull_request("adapter", 8, fill=lambda path: (path / "README.md").write_text("eight\n"))
    engine, event = engine_under_test(world, body=depends_on("adapter", 7) + depends_on("adapter", 8))

    said = world.tool(engine, 1, **world.ci(event=event))

    assert "adapter/pull/8" in said
    assert "conflict" in said


def test_a_named_pull_request_closed_without_merging_fails_the_check_naming_it(world):
    world.pull_request("adapter", 7, state="closed")
    engine, event = engine_under_test(world, body=depends_on("adapter", 7))

    said = world.tool(engine, 1, **world.ci(event=event))

    assert "adapter/pull/7" in said
    assert "closed without merging" in said


def test_a_cycle_of_named_pull_requests_fails_the_check_naming_them(world):
    world.pull_request("adapter", 7, body=depends_on("engine", 1))
    engine, event = engine_under_test(world, body=depends_on("adapter", 7))

    said = world.tool(engine, 1, **world.ci(event=event))

    assert "adapter/pull/7" in said
    assert "cycle" in said


def test_a_merged_named_pull_request_adds_nothing_and_the_matching_branch_is_used(world):
    world.pull_request("adapter", 7, state="closed", merged=True)
    world.branch("adapter", "stable/x", fill=lambda path: (path / "STABLE").write_text("stable\n"))
    world.branch("cascade-bridge-spec", "stable/x")
    engine, event = engine_under_test(world, body=depends_on("adapter", 7), base="stable/x")

    world.tool(engine, **world.ci(event=event, branch="stable/x"))

    repositories = world.record()["repositories"]
    assert repositories["adapter"]["how"] == "stable/x, the branch matching the pull request's target"
    assert repositories["cascade-bridge-spec"]["how"] == "stable/x, the branch matching the pull request's target"
    assert (world.workspace / "adapter" / "STABLE").exists()


def test_a_repository_without_the_matching_branch_is_used_at_its_default_branch(world):
    engine, event = engine_under_test(world, base="stable/x")

    world.tool(engine, **world.ci(event=event, branch="stable/x"))

    assert world.record()["repositories"]["adapter"]["how"] == "main, the default branch"


def test_a_named_pull_request_in_a_repository_the_run_checks_nothing_out_from_is_listed_as_not_used(world):
    world.pull_request("cascade-cli", 4)
    engine, event = engine_under_test(world, body=depends_on("cascade-cli", 4))

    said = world.tool(engine, **world.ci(event=event))

    assert "cascade-cli" in world.table()
    assert "not used" in world.table()
    assert "does not hold" not in said


def test_a_description_changed_between_runs_is_read_again_by_the_second_run(world):
    world.pull_request("adapter", 7, fill=lambda path: (path / "NOTICE").write_text("named\n"))
    engine, event = engine_under_test(world)

    world.tool(engine, **world.ci(event=event))
    assert world.record()["repositories"]["adapter"]["how"] == "main, the default branch"

    world.pull_requests.get("engine", 1)["body"] = depends_on("adapter", 7)
    world.tool(engine, **world.ci(event=event))
    assert world.record()["repositories"]["adapter"]["how"] == "pull request #7 merged into main"


def test_a_push_run_uses_the_branch_it_runs_on_and_reads_no_description(world):
    engine = world.engine([world.url("adapter")])

    world.tool(engine, **world.ci())

    repositories = world.record()["repositories"]
    assert repositories["adapter"]["how"] == "main, the branch this run is on"
    assert repositories["engine"]["commit"] == git("rev-parse", "HEAD", cwd=engine)
