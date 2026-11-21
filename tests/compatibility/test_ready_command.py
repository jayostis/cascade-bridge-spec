"""The merge gate: a pull request merges only after the pull requests it names have merged."""

import pytest

from compatibility_tool import breaking, ready
from compatibility_world import (
    NOTHING_BREAKS,
    depends_on,
)

GATE = "ready-to-merge"
PULL_7 = "https://github.com/the-cascade-protocol/adapter/pull/7"
BOM = chr(0xFEFF)
LS = chr(0x2028)
PS = chr(0x2029)
NEL = chr(0x85)
NBSP = chr(0xA0)


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

    class TestGivenTheReadyToMergeCheckIsAskedFor:
        """given the ready-to-merge check is asked for"""

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

        @pytest.mark.parametrize("status", [404, 403], ids=["not found", "forbidden"])
        def test_passes_with_a_warning_for_a_named_pull_request_it_cannot_see(self, world, status):
            world.pull_requests.refuse("private", 123, status)
            engine, event = world.engine_under_test(body=depends_on("private", 123))

            said = world.tool(engine, check="ready-to-merge", **world.ci(event=event))

            assert "private/pull/123 could not be read" in said
            assert "not checked" in said
            assert "FAIL" not in said

        def test_fails_an_unknown_pull_request_number_in_a_repository_it_can_read(self, world):
            world.pull_request("adapter", 8)
            engine, event = world.engine_under_test(body=depends_on("adapter", 99))

            said = world.tool(engine, 1, check="ready-to-merge", **world.ci(event=event))

            assert "adapter/pull/99 could not be read: 404" in said

        @pytest.mark.parametrize(
            ("headers", "message"),
            [
                ({"retry-after": "60", "x-ratelimit-remaining": "4999"}, "You have exceeded a secondary rate limit"),
                ({}, "You have triggered an abuse detection mechanism"),
                ({"x-ratelimit-remaining": "4999"}, "API rate limit exceeded"),
            ],
            ids=["retry-after", "abuse", "rate limit message"],
        )
        def test_fails_a_forbidden_read_that_is_a_limit_not_a_missing_access(self, world, headers, message):
            world.pull_requests.refuse("private", 123, 403, headers, message)
            engine, event = world.engine_under_test(body=depends_on("private", 123))

            said = world.tool(engine, 1, check="ready-to-merge", **world.ci(event=event))

            assert "private/pull/123 could not be read: 403" in said

        def test_says_the_merge_does_not_wait_on_a_pull_request_it_cannot_see(self, world):
            world.pull_requests.refuse("private", 123, 404)
            engine, event = world.engine_under_test(body=depends_on("private", 123))

            said = world.tool(engine, check="ready-to-merge", **world.ci(event=event))

            assert "the merge does not wait on it" in said

        def test_still_fails_a_pull_request_it_cannot_see_when_another_named_one_has_not_merged(self, world):
            world.pull_requests.refuse("private", 123, 404)
            world.pull_request("adapter", 8)
            engine, event = world.engine_under_test(body=depends_on("private", 123) + depends_on("adapter", 8))

            said = world.tool(engine, 1, check="ready-to-merge", **world.ci(event=event))

            assert "private/pull/123 could not be read" in said
            assert "adapter/pull/8 has not merged" in said

        def test_fails_a_named_pull_request_whose_read_failed_for_any_other_reason(self, world):
            world.pull_requests.refuse("private", 123, 500)
            engine, event = world.engine_under_test(body=depends_on("private", 123))

            said = world.tool(engine, 1, check="ready-to-merge", **world.ci(event=event))

            assert "private/pull/123 could not be read: 500" in said

        def test_fails_a_named_pull_request_refused_for_the_rate_limit(self, world):
            world.pull_requests.refuse("private", 123, 403, {"x-ratelimit-remaining": "0"})
            engine, event = world.engine_under_test(body=depends_on("private", 123))

            said = world.tool(engine, 1, check="ready-to-merge", **world.ci(event=event))

            assert "private/pull/123 could not be read: 403" in said

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

        @pytest.mark.parametrize("conclusion", ["skipped", "neutral"], ids=["a skipped check", "a neutral check"])
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

        def test_passes_with_a_warning_for_a_pull_request_outside_a_cycle_that_it_cannot_see(self, world):
            world.pull_requests.refuse("private", 123, 404)
            head = world.pull_request("adapter", 7, body=depends_on("engine", 1) + depends_on("private", 123))
            world.pull_requests.check_run("adapter", head, "compatibility")
            engine, event = world.engine_under_test(body=depends_on("adapter", 7))

            said = world.tool(engine, check="ready-to-merge", **world.ci(event=event, gate=GATE))

            assert "private/pull/123 could not be read" in said
            assert "FAIL" not in said

        def test_fails_a_cycle_whose_outside_pull_request_failed_to_read_for_any_other_reason(self, world):
            world.pull_requests.refuse("private", 123, 502)
            head = world.pull_request("adapter", 7, body=depends_on("engine", 1) + depends_on("private", 123))
            world.pull_requests.check_run("adapter", head, "compatibility")
            engine, event = world.engine_under_test(body=depends_on("adapter", 7))

            said = world.tool(engine, 1, check="ready-to-merge", **world.ci(event=event, gate=GATE))

            assert "private/pull/123 could not be read: 502" in said

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

    class TestGivenThePullRequestUnderTest:
        """given the pull request under test"""

        def test_fails_with_no_breaking_section_and_still_checks_what_it_names(self, world):
            world.pull_request("adapter", 7)
            engine, event = world.engine_under_test(body="Some description.\n\nDepends-On: " + PULL_7)

            said = world.tool(engine, 1, check="ready-to-merge", **world.ci(event=event))

            assert "the body has no `## Breaking` section" in said
            assert "adapter/pull/7 has not merged" in said

        def test_fails_with_no_breaking_section_and_nothing_named(self, world):
            engine, event = world.engine_under_test(body="Some description.\n")

            said = world.tool(engine, 1, check="ready-to-merge", **world.ci(event=event))

            assert "the body has no `## Breaking` section" in said

        def test_passes_with_a_breaking_section_saying_none_and_nothing_named(self, world):
            engine, event = world.engine_under_test(body=NOTHING_BREAKS)

            said = world.tool(engine, check="ready-to-merge", **world.ci(event=event))

            assert "FAIL" not in said


class TestTheBreakingSection:
    """The `## Breaking` section of a pull request's description · compatibility_tool/breaking.py

    A section lists each `old -> new` or `old -> removed` a caller sees, or says None.
    """

    @pytest.mark.parametrize(
        "section",
        [
            "None",
            "none.",
            "- None",
            "* NONE",
            "- `a.b` -> `c.d`",
            "1. a -> b\n2. c -> removed",
            "- a -> b\n\n- c -> d",
            "-\nNone",
            "None\n\n---\nanything after the rule",
            "None\nDepends-On: https://github.com/the-cascade-protocol/engine/pull/1",
            "None\n\n## Verification\n\nnot an arrow",
            "None <!-- a -> b -->",
            "<!-- - old -> new -->\nNone",
            "None\r\n",
            "None\r",
            "- a -> b\r- c -> d",
            "- a -> b" + LS + "- c -> d" + PS,
            "- a -> b" + NBSP,
            "- " + NBSP + "a -> b",
            "- a ->->b",
            "a ->" + NEL,
            NEL + "-> b",
            "１. a -> b",
        ],
        ids=lambda section: repr(section)[:40],
    )
    def test_is_read(self, section):
        assert breaking.problem_in("## Breaking\n\n" + section) is None

    def test_is_read_after_a_byte_order_mark_and_other_sections(self):
        body = BOM + "## Summary\n\nwords\n\n## Breaking\t\n\n- a -> b\n\n## Tests\n"

        assert breaking.problem_in(body) is None

    def test_is_read_with_a_depends_on_line_after_none(self):
        assert (
            breaking.problem_in(
                "## Breaking\n\nNone\n\nDepends-On: https://github.com/the-cascade-protocol/engine/pull/1"
            )
            is None
        )

    @pytest.mark.parametrize(
        "body",
        [None, "", "Some description.", "## Breaking changes\n\nNone", "### Breaking\n\nNone", "#Breaking\nNone"],
        ids=["null", "empty", "no heading", "another heading", "a deeper heading", "no space"],
    )
    def test_is_refused_when_missing(self, body):
        assert breaking.problem_in(body) == "the body has no `## Breaking` section"

    @pytest.mark.parametrize(
        "after",
        [
            "",
            "\n\n",
            "\n- \n",
            "\n## Next\n",
            "\n---\n",
            "\nDepends-On: https://github.com/the-cascade-protocol/engine/pull/1",
            "\n<!-- None -->",
        ],
        ids=["end", "blank", "bare bullet", "next heading", "rule", "depends on", "comment"],
    )
    def test_is_refused_when_empty(self, after):
        said = breaking.problem_in("## Breaking" + after)

        assert said == "the `## Breaking` section is empty: list each `old -> new` or `old -> removed`, or write None"

    def test_is_refused_with_none_beside_lines(self):
        assert breaking.problem_in("## Breaking\n\nNone\n- a -> b") == "the `## Breaking` section has None beside lines"

    @pytest.mark.parametrize(
        "line",
        [
            "renamed a to b",
            "a - b",
            "a => b",
            "a > b",
            "a \u2192 b",
            "->",
            "- ->",
            "a ->",
            "-> b",
            "a ->" + NBSP,
            NBSP + "-> b",
            "None" + NEL,
            "\uff11. None",
        ],
        ids=lambda line: repr(line)[:30],
    )
    def test_is_refused_with_a_line_that_is_not_old_to_new(self, line):
        said = breaking.problem_in("## Breaking\n\n" + line + "\n")

        assert said.endswith("is not `old -> new` or `old -> removed`"), said
