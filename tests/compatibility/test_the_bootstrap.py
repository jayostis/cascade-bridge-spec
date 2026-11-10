"""What a caller's workflow starts: it fetches a version, and the checks run from the one picked."""

from compatibility_world import TOKEN, depends_on, git


class TestRunningTheChecksFromTheVersionARunPicked:
    """Running the checks from the version a run picked · scripts/compatibility.py

    A caller fetches the default branch's tooling, which picks a version of the specification and hands the run to it.
    Picking happens before anything is installed.
    """

    class TestGivenARepositoryWithNothingToCheck:
        def test_is_not_reported_as_a_pass(self, world):
            adapter = world.clone("adapter")
            world.pull_request("adapter", 1)

            said = world.tool(adapter, **world.ci(repository="adapter", event=world.event(1, "adapter")))

            assert "nothing to check" in said
            assert "\nPASS\n" not in said

    class TestGivenAVersionPicked:
        def test_runs_the_checks_not_the_version_fetched_to_start(self, world):
            """runs the checks, not the version fetched to start"""
            engine, event = world.engine_under_test()

            said = world.tool(engine, in_a_process=True, **world.ci(event=event))

            assert "the checks run from" in said
            assert str(world.workspace / "cascade-bridge-spec") in said
            assert said.count("compatibility: ") == 1

        def test_runs_the_merge_gate_too(self, world):
            """runs the merge gate too

            A pull request here that changes the gate is tried the same way as one that changes a check.
            """
            world.pull_request("cascade-bridge-spec", 3)
            engine, event = world.engine_under_test(body=depends_on("cascade-bridge-spec", 3))

            said = world.tool(engine, 1, check="ready-to-merge", in_a_process=True, **world.ci(event=event))

            assert "the checks run from" in said
            assert "cascade-bridge-spec/pull/3 has not merged" in said
            assert set(world.pull_requests.authorizations) == {f"Bearer {TOKEN}"}

    class TestGivenAVersionPickedThatPredatesCheckoutOnly:
        """given a version picked that predates `--checkout-only`"""

        def test_runs_the_whole_check_quietly(self, world):
            origin = world.origin("cascade-bridge-spec")
            cli = origin / "scripts" / "compatibility_tool" / "cli.py"
            text = cli.read_text(encoding="utf-8")
            flag, variable = '"--checkout-only",', 'os.environ.get("CASCADE_CHECKOUT_ONLY") == "true"'
            assert flag in text and variable in text
            cli.write_text(
                text.replace(flag, '"--not-yet-a-flag", dest="checkout_only",').replace(variable, "False"),
                encoding="utf-8",
            )
            git("commit", "-q", "-am", "a version before checkout-only", cwd=origin)
            engine, event = world.engine_under_test()

            said = world.tool(engine, in_a_process=True, checkout_only=True, **world.ci(event=event))

            assert "the checks run from" in said
            assert "did not run the check" not in said
            assert said.count("compatibility: ") == 1
