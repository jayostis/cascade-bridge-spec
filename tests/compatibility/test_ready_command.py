"""The merge gate: a pull request merges only after the pull requests it names have merged."""

from test_picking_versions import depends_on, engine_under_test


def test_ready_to_merge_fails_while_a_named_pull_request_is_open_naming_it(world):
    world.pull_request("adapter", 7)
    engine, event = engine_under_test(world, body=depends_on("adapter", 7))

    said = world.tool(engine, 1, check="ready-to-merge", **world.ci(event=event))

    assert "adapter/pull/7" in said
    assert "has not merged" in said


def test_ready_to_merge_passes_once_the_named_pull_request_has_merged(world):
    world.pull_request("adapter", 7, state="closed", merged=True)
    engine, event = engine_under_test(world, body=depends_on("adapter", 7))

    said = world.tool(engine, check="ready-to-merge", **world.ci(event=event))

    assert "adapter/pull/7" in said
    assert "has merged" in said


def test_ready_to_merge_passes_a_pull_request_naming_nothing(world):
    engine, event = engine_under_test(world)

    said = world.tool(engine, check="ready-to-merge", **world.ci(event=event))

    assert "names no pull request" in said


def test_ready_to_merge_passes_a_push(world):
    said = world.tool(world.engine([world.url("adapter")]), check="ready-to-merge", **world.ci())

    assert "no pull request is under test" in said


def test_ready_to_merge_reads_only_the_pull_requests_named_directly(world):
    world.pull_request("cascade-bridge-spec", 3)
    world.pull_request("adapter", 7, body=depends_on("cascade-bridge-spec", 3), state="closed", merged=True)
    engine, event = engine_under_test(world, body=depends_on("adapter", 7))

    said = world.tool(engine, check="ready-to-merge", **world.ci(event=event))

    assert "cascade-bridge-spec/pull/3" not in said
