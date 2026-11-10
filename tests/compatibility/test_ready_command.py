"""The merge gate: a pull request merges only after the pull requests it names have merged."""

import pytest

from compatibility_tool import ready
from compatibility_world import (
    depends_on,
)

GATE = "ready-to-merge"


@pytest.fixture(autouse=True)
def no_time_passes_but_what_the_gate_sleeps(monkeypatch):
    now = [0]
    monkeypatch.setattr(ready, "monotonic", lambda: now[0])
    monkeypatch.setattr(ready, "sleep", lambda seconds: now.__setitem__(0, now[0] + seconds))


def adapter_naming_the_engine_back(world, *runs, merged=False):
    state = "closed" if merged else "open"
    head = world.pull_request("adapter", 7, body=depends_on("engine", 1), state=state, merged=merged)
    for name, status, conclusion in runs:
        world.pull_requests.check_run("adapter", head, name, status=status, conclusion=conclusion)
    return world.engine_under_test(body=depends_on("adapter", 7))


class TestTheMergeGate:
    """The merge gate · --check ready-to-merge

    A pull request merges only once every pull request it names has merged, or names it back and has passed every check
    but its own gate.
    """

    class TestGivenCheckReadyToMerge:
        """given `--check ready-to-merge`"""

        def test_fails_while_a_named_pull_request_is_open_naming_it(self, world):
            """fails while a named pull request is open, naming it"""
            head = world.pull_request("adapter", 7)
            world.pull_requests.check_run("adapter", head, "compatibility")
            engine, event = world.engine_under_test(body=depends_on("adapter", 7))

            said = world.tool(engine, 1, check="ready-to-merge", **world.ci(event=event, gate=GATE))

            assert "adapter/pull/7" in said
            assert "has not merged" in said

        def test_passes_once_the_named_pull_request_has_merged(self, world):
            world.pull_request("adapter", 7, state="closed", merged=True)
            engine, event = world.engine_under_test(body=depends_on("adapter", 7))

            said = world.tool(engine, check="ready-to-merge", **world.ci(event=event))

            assert "adapter/pull/7" in said
            assert "has merged" in said

        def test_tells_a_pull_request_closed_without_merging_to_cut_the_line_naming_it(self, world):
            world.pull_request("adapter", 7, state="closed")
            world.pull_request("adapter", 8)
            engine, event = world.engine_under_test(body=depends_on("adapter", 7) + depends_on("adapter", 8))

            said = world.tool(engine, 1, check="ready-to-merge", **world.ci(event=event))

            assert "adapter/pull/7 is closed without merging: cut the Depends-On: line naming it" in said
            assert "adapter/pull/8 has not merged" in said

        def test_passes_a_pull_request_naming_nothing(self, world):
            engine, event = world.engine_under_test()

            said = world.tool(engine, check="ready-to-merge", **world.ci(event=event))

            assert "names no pull request" in said

        def test_passes_a_push(self, world):
            said = world.tool(world.engine([world.url("adapter")]), check="ready-to-merge", **world.ci())

            assert "no pull request is under test" in said

        def test_reads_only_the_pull_requests_named_directly(self, world):
            world.pull_request("cascade-bridge-spec", 3)
            world.pull_request("adapter", 7, body=depends_on("cascade-bridge-spec", 3), state="closed", merged=True)
            engine, event = world.engine_under_test(body=depends_on("adapter", 7))

            said = world.tool(engine, check="ready-to-merge", **world.ci(event=event))

            assert "cascade-bridge-spec/pull/3" not in said

    class TestGivenACycleOfPullRequestsNamingEachOther:
        def test_passes_a_cycle_member_whose_checks_succeeded_apart_from_its_own_gate(self, world):
            engine, event = adapter_naming_the_engine_back(
                world,
                ("compatibility", "completed", "success"),
                ("ruff and pytest", "completed", "success"),
                (GATE, "in_progress", None),
            )

            said = world.tool(engine, check="ready-to-merge", **world.ci(event=event, gate=GATE))

            assert "adapter/pull/7" in said

        def test_fails_a_member_naming_its_failed_check_without_waiting_for_the_rest(self, world):
            """fails a member naming its failed check, without waiting for the rest"""
            engine, event = adapter_naming_the_engine_back(
                world,
                ("compatibility", "in_progress", None),
                ("the adapter's own tests", "completed", "failure"),
                (GATE, "in_progress", None),
            )

            said = world.tool(engine, 1, check="ready-to-merge", **world.ci(event=event, gate=GATE))

            assert "its the adapter's own tests has not succeeded: failure" in said
            assert "waiting" not in said

        def test_waits_for_a_cycle_member_whose_check_is_still_running(self, world, monkeypatch):
            engine, event = adapter_naming_the_engine_back(world, ("compatibility", "in_progress", None))
            [running] = world.pull_requests.check_runs_by_commit[
                ("adapter", world.pull_requests.get("adapter", 7)["head"]["sha"])
            ]
            monkeypatch.setattr(
                ready, "sleep", lambda seconds: running.update(status="completed", conclusion="success")
            )

            said = world.tool(engine, check="ready-to-merge", **world.ci(event=event, gate=GATE))

            assert "waiting" in said
            assert "adapter/pull/7 names this pull request back, and its checks have succeeded" in said

        def test_fails_naming_the_check_it_waited_for_when_it_stops_waiting(self, world):
            engine, event = adapter_naming_the_engine_back(
                world, ("compatibility", "completed", "success"), ("the adapter's own tests", "in_progress", None)
            )

            said = world.tool(engine, 1, check="ready-to-merge", **world.ci(event=event, gate=GATE))

            assert "have not finished after waiting 45 minutes: the adapter's own tests is in_progress" in said

        def test_takes_the_latest_run_of_a_cycle_members_check(self, world):
            """takes the latest run of a cycle member's check"""
            engine, event = adapter_naming_the_engine_back(
                world, ("compatibility", "completed", "failure"), ("compatibility", "completed", "success")
            )

            said = world.tool(engine, check="ready-to-merge", **world.ci(event=event, gate=GATE))

            assert "adapter/pull/7 names this pull request back, and its checks have succeeded" in said

        def test_passes_a_cycle_member_that_has_merged(self, world):
            engine, event = adapter_naming_the_engine_back(world, merged=True)

            said = world.tool(engine, check="ready-to-merge", **world.ci(event=event, gate=GATE))

            assert "adapter/pull/7" in said

        def test_counts_a_pull_request_naming_it_back_through_another_as_a_cycle_member(self, world):
            head = world.pull_request("adapter", 7, body=depends_on("cascade-bridge-spec", 3))
            world.pull_requests.check_run("adapter", head, "compatibility")
            spec = world.pull_request("cascade-bridge-spec", 3, body=depends_on("engine", 1))
            world.pull_requests.check_run("cascade-bridge-spec", spec, "ruff and pytest")
            engine, event = world.engine_under_test(body=depends_on("adapter", 7))

            said = world.tool(engine, check="ready-to-merge", **world.ci(event=event, gate=GATE))

            assert "adapter/pull/7" in said

        @pytest.mark.parametrize("runs", [(), ((GATE, "in_progress", None),)], ids=["no check runs", "only its gate"])
        def test_fails_a_cycle_member_with_no_checks_on_its_head_commit(self, world, runs):
            engine, event = adapter_naming_the_engine_back(world, *runs)

            said = world.tool(engine, 1, check="ready-to-merge", **world.ci(event=event, gate=GATE))

            assert "adapter/pull/7" in said
            assert "no checks" in said

        def test_discounts_the_gate_by_its_check_name_not_its_job_id(self, world):
            """discounts the gate by its check name, not its job id"""
            gate = "checks / Ready to merge"
            engine, event = adapter_naming_the_engine_back(
                world, ("compatibility", "completed", "success"), (gate, "in_progress", None)
            )

            said = world.tool(engine, check="ready-to-merge", **world.ci(event=event, gate=gate))

            assert "adapter/pull/7" in said

        def test_says_in_a_cycle_that_it_cannot_tell_its_own_gate_without_its_check_run(self, world):
            engine, event = adapter_naming_the_engine_back(world, ("compatibility", "completed", "success"))

            said = world.tool(engine, 1, check="ready-to-merge", **world.ci(event=event))

            assert "CASCADE_CHECK_RUN_ID" in said

        @pytest.mark.parametrize("conclusion", ["skipped", "neutral"])
        def test_passes_a_cycle_member_whose_check_concluded_as_github_passes_it(self, world, conclusion):
            """passes a cycle member whose check concluded as GitHub passes it"""
            engine, event = adapter_naming_the_engine_back(
                world,
                ("compatibility", "completed", "success"),
                ("deploy", "completed", conclusion),
                (GATE, "in_progress", None),
            )

            said = world.tool(engine, check="ready-to-merge", **world.ci(event=event, gate=GATE))

            assert "adapter/pull/7" in said

        def test_fails_a_cycle_whose_member_names_a_pull_request_outside_it(self, world):
            world.pull_request("cascade-bridge-spec", 3)
            head = world.pull_request("adapter", 7, body=depends_on("engine", 1) + depends_on("cascade-bridge-spec", 3))
            world.pull_requests.check_run("adapter", head, "compatibility")
            engine, event = world.engine_under_test(body=depends_on("adapter", 7))

            said = world.tool(engine, 1, check="ready-to-merge", **world.ci(event=event, gate=GATE))

            assert "cascade-bridge-spec/pull/3" in said

        def test_passes_a_cycle_whose_member_names_a_merged_pull_request_outside_it(self, world):
            world.pull_request("cascade-bridge-spec", 3, state="closed", merged=True)
            head = world.pull_request("adapter", 7, body=depends_on("engine", 1) + depends_on("cascade-bridge-spec", 3))
            world.pull_requests.check_run("adapter", head, "compatibility")
            engine, event = world.engine_under_test(body=depends_on("adapter", 7))

            said = world.tool(engine, check="ready-to-merge", **world.ci(event=event, gate=GATE))

            assert "adapter/pull/7" in said

        def test_finds_no_cycle_through_a_merged_pull_request(self, world):
            world.pull_request("adapter", 7, body=depends_on("cascade-bridge-spec", 3))
            world.pull_request("cascade-bridge-spec", 3, body=depends_on("engine", 1), state="closed", merged=True)
            engine, event = world.engine_under_test(body=depends_on("adapter", 7))

            said = world.tool(engine, 1, check="ready-to-merge", **world.ci(event=event, gate=GATE))

            assert "adapter/pull/7 has not merged" in said

        def test_passes_a_cycle_in_the_repository_under_test_once_the_others_checks_have(self, world):
            """passes a cycle in the repository under test once the others' checks have"""
            head = world.pull_request("engine", 2, body=depends_on("engine", 1))
            world.pull_requests.check_run("engine", head, "compatibility")
            world.pull_requests.check_run("engine", head, GATE, status="in_progress")
            engine, event = world.engine_under_test(body=depends_on("engine", 2))

            said = world.tool(engine, check="ready-to-merge", **world.ci(event=event, gate=GATE))

            assert "engine/pull/2 names this pull request back, and its checks have succeeded" in said
