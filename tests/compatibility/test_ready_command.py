"""The merge gate: a pull request merges only after the pull requests it names have merged."""

import pytest

from test_picking_versions import depends_on, engine_under_test

GATE = "ready-to-merge"


def test_ready_to_merge_fails_while_a_named_pull_request_is_open_naming_it(world):
    head = world.pull_request("adapter", 7)
    world.pull_requests.check_run("adapter", head, "compatibility")
    engine, event = engine_under_test(world, body=depends_on("adapter", 7))

    said = world.tool(engine, 1, check="ready-to-merge", **world.ci(event=event, gate=GATE))

    assert "adapter/pull/7" in said
    assert "has not merged" in said


def test_ready_to_merge_passes_once_the_named_pull_request_has_merged(world):
    world.pull_request("adapter", 7, state="closed", merged=True)
    engine, event = engine_under_test(world, body=depends_on("adapter", 7))

    said = world.tool(engine, check="ready-to-merge", **world.ci(event=event))

    assert "adapter/pull/7" in said
    assert "has merged" in said


def test_ready_to_merge_tells_a_pull_request_closed_without_merging_to_cut_the_line_naming_it(world):
    world.pull_request("adapter", 7, state="closed")
    world.pull_request("adapter", 8)
    engine, event = engine_under_test(world, body=depends_on("adapter", 7) + depends_on("adapter", 8))

    said = world.tool(engine, 1, check="ready-to-merge", **world.ci(event=event))

    assert "adapter/pull/7 is closed without merging: cut the Depends-On: line naming it" in said
    assert "adapter/pull/8 has not merged" in said


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


def adapter_naming_the_engine_back(world, *runs, merged=False):
    state = "closed" if merged else "open"
    head = world.pull_request("adapter", 7, body=depends_on("engine", 1), state=state, merged=merged)
    for name, status, conclusion in runs:
        world.pull_requests.check_run("adapter", head, name, status=status, conclusion=conclusion)
    return engine_under_test(world, body=depends_on("adapter", 7))


@pytest.mark.parametrize(
    "gate", [("in_progress", None), ("queued", None), ("completed", "failure")], ids=lambda gate: gate[0]
)
def test_ready_to_merge_passes_a_cycle_member_whose_checks_succeeded_apart_from_its_own_gate(world, gate):
    engine, event = adapter_naming_the_engine_back(
        world, ("compatibility", "completed", "success"), ("ruff and pytest", "completed", "success"), (GATE, *gate)
    )

    said = world.tool(engine, check="ready-to-merge", **world.ci(event=event, gate=GATE))

    assert "adapter/pull/7" in said


@pytest.mark.parametrize(
    "run", [("completed", "failure"), ("in_progress", None), ("queued", None)], ids=lambda run: run[1] or run[0]
)
def test_ready_to_merge_fails_a_cycle_member_naming_its_check_that_did_not_succeed(world, run):
    engine, event = adapter_naming_the_engine_back(
        world, ("compatibility", "completed", "success"), ("the adapter's own tests", *run), (GATE, "in_progress", None)
    )

    said = world.tool(engine, 1, check="ready-to-merge", **world.ci(event=event, gate=GATE))

    failing = [line for line in said.splitlines() if "the adapter's own tests" in line]
    assert failing, said
    assert "adapter/pull/7" in said


def test_ready_to_merge_passes_a_cycle_member_that_has_merged(world):
    engine, event = adapter_naming_the_engine_back(world, merged=True)

    said = world.tool(engine, check="ready-to-merge", **world.ci(event=event, gate=GATE))

    assert "adapter/pull/7" in said


def test_ready_to_merge_counts_a_pull_request_naming_it_back_through_another_as_a_cycle_member(world):
    head = world.pull_request("adapter", 7, body=depends_on("cascade-bridge-spec", 3))
    world.pull_requests.check_run("adapter", head, "compatibility")
    spec = world.pull_request("cascade-bridge-spec", 3, body=depends_on("engine", 1))
    world.pull_requests.check_run("cascade-bridge-spec", spec, "ruff and pytest")
    engine, event = engine_under_test(world, body=depends_on("adapter", 7))

    said = world.tool(engine, check="ready-to-merge", **world.ci(event=event, gate=GATE))

    assert "adapter/pull/7" in said


@pytest.mark.parametrize("runs", [(), ((GATE, "in_progress", None),)], ids=["no check runs", "only its gate"])
def test_ready_to_merge_fails_a_cycle_member_with_no_checks_on_its_head_commit(world, runs):
    engine, event = adapter_naming_the_engine_back(world, *runs)

    said = world.tool(engine, 1, check="ready-to-merge", **world.ci(event=event, gate=GATE))

    assert "adapter/pull/7" in said
    assert "no checks" in said


def test_ready_to_merge_discounts_the_gate_by_its_check_name_not_its_job_id(world):
    gate = "checks / Ready to merge"
    engine, event = adapter_naming_the_engine_back(
        world, ("compatibility", "completed", "success"), (gate, "in_progress", None)
    )

    said = world.tool(engine, check="ready-to-merge", **world.ci(event=event, gate=gate))

    assert "adapter/pull/7" in said


def test_ready_to_merge_in_a_cycle_says_it_cannot_tell_its_own_gate_without_its_check_run(world):
    engine, event = adapter_naming_the_engine_back(world, ("compatibility", "completed", "success"))

    said = world.tool(engine, 1, check="ready-to-merge", **world.ci(event=event))

    assert "CASCADE_CHECK_RUN_ID" in said


@pytest.mark.parametrize("conclusion", ["skipped", "neutral"])
def test_ready_to_merge_passes_a_cycle_member_whose_check_concluded_as_github_passes_it(world, conclusion):
    engine, event = adapter_naming_the_engine_back(
        world,
        ("compatibility", "completed", "success"),
        ("deploy", "completed", conclusion),
        (GATE, "in_progress", None),
    )

    said = world.tool(engine, check="ready-to-merge", **world.ci(event=event, gate=GATE))

    assert "adapter/pull/7" in said


@pytest.mark.parametrize("state", ["open", "closed"])
def test_ready_to_merge_fails_a_cycle_whose_member_names_a_pull_request_outside_it(world, state):
    world.pull_request("cascade-bridge-spec", 3, state=state)
    head = world.pull_request("adapter", 7, body=depends_on("engine", 1) + depends_on("cascade-bridge-spec", 3))
    world.pull_requests.check_run("adapter", head, "compatibility")
    engine, event = engine_under_test(world, body=depends_on("adapter", 7))

    said = world.tool(engine, 1, check="ready-to-merge", **world.ci(event=event, gate=GATE))

    assert "cascade-bridge-spec/pull/3" in said


def test_ready_to_merge_passes_a_cycle_whose_member_names_a_merged_pull_request_outside_it(world):
    world.pull_request("cascade-bridge-spec", 3, state="closed", merged=True)
    head = world.pull_request("adapter", 7, body=depends_on("engine", 1) + depends_on("cascade-bridge-spec", 3))
    world.pull_requests.check_run("adapter", head, "compatibility")
    engine, event = engine_under_test(world, body=depends_on("adapter", 7))

    said = world.tool(engine, check="ready-to-merge", **world.ci(event=event, gate=GATE))

    assert "adapter/pull/7" in said


def test_ready_to_merge_finds_no_cycle_through_a_merged_pull_request(world):
    world.pull_request("adapter", 7, body=depends_on("cascade-bridge-spec", 3))
    world.pull_request("cascade-bridge-spec", 3, body=depends_on("engine", 1), state="closed", merged=True)
    engine, event = engine_under_test(world, body=depends_on("adapter", 7))

    said = world.tool(engine, 1, check="ready-to-merge", **world.ci(event=event, gate=GATE))

    assert "adapter/pull/7 has not merged" in said


def test_ready_to_merge_fails_a_cycle_member_named_through_another_whose_check_did_not_succeed(world):
    head = world.pull_request("adapter", 7, body=depends_on("cascade-bridge-spec", 3))
    world.pull_requests.check_run("adapter", head, "compatibility")
    spec = world.pull_request("cascade-bridge-spec", 3, body=depends_on("engine", 1))
    world.pull_requests.check_run("cascade-bridge-spec", spec, "ruff and pytest", conclusion="failure")
    engine, event = engine_under_test(world, body=depends_on("adapter", 7))

    said = world.tool(engine, 1, check="ready-to-merge", **world.ci(event=event, gate=GATE))

    failing = [line for line in said.splitlines() if "ruff and pytest" in line]
    assert failing, said
    assert "cascade-bridge-spec/pull/3" in said
