"""What a caller's workflow starts: it fetches a version, and the checks run from the one picked."""

from test_picking_versions import depends_on, engine_under_test


def test_a_run_says_one_verdict(world):
    engine, event = engine_under_test(world)

    said = world.tool(engine, **world.ci(event=event))

    assert said.count("compatibility: ") == 1


def test_nothing_to_check_is_not_reported_as_a_pass(world):
    engine = world.engine([])
    world.pull_request("engine", 1)

    said = world.tool(engine, **world.ci(event=world.event(1)))

    assert "nothing to check" in said
    assert "\nPASS\n" not in said


def test_the_checks_run_from_the_version_picked_not_the_one_fetched_to_start(world):
    engine, event = engine_under_test(world)

    said = world.tool(engine, **world.ci(event=event))

    assert "the checks run from" in said
    assert str(world.workspace / "cascade-bridge-spec") in said


def test_the_merge_gate_runs_from_the_version_picked_too(world):
    """A pull request here that changes the gate is tried the same way as one that changes a check."""
    world.pull_request("cascade-bridge-spec", 3)
    engine, event = engine_under_test(world, body=depends_on("cascade-bridge-spec", 3))

    said = world.tool(engine, 1, check="ready-to-merge", **world.ci(event=event))

    assert "the checks run from" in said
    assert "cascade-bridge-spec/pull/3 has not merged" in said
