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


class TestPickingTheVersionOfEachRepositoryARunUses:
    """Picking the version of each repository a run uses · Depends-On:

    Nothing pins one repository to a commit of another. A run picks each: the pull requests named on `Depends-On:` lines
    merged into the branch they target, else the branch named like the one the run is on, else the default branch.
    """

    class TestGivenARepositoryNamedInAnotherCase:
        def test_is_the_same_repository(self, world):
            """is the same repository

            GitHub reads owner and repository names whatever their case, so a line naming one so is the same line.
            """
            world.pull_request("engine", 2, body=depends_on("ENGINE", 1, owner="JAYOSTIS"), fill=writing("TWO"))
            engine, event = engine_checked_out_as_ci_does(world, depends_on("Engine", 2, owner="JayOstis"))

            world.tool(engine, **world.ci(event=event))

            assert (engine / "TWO").is_file()
            assert (
                world.record()["repositories"]["engine"]["how"]
                == "pull request #1 merged into main, and #2 merged into it"
            )

    class TestGivenACycleBetweenTwoNamedPullRequests:
        def test_picks_both(self, world):
            world.pull_request("adapter", 7, body=depends_on("cascade-bridge-spec", 3))
            world.pull_request("cascade-bridge-spec", 3, body=depends_on("adapter", 7))
            engine, event = world.engine_under_test(
                body=depends_on("cascade-bridge-spec", 3) + depends_on("adapter", 7)
            )

            world.tool(engine, **world.ci(event=event))

            repositories = world.record()["repositories"]
            assert repositories["adapter"]["how"] == "pull request #7 merged into main"
            assert repositories["cascade-bridge-spec"]["how"] == "pull request #3 merged into main"

    class TestGivenTheBranchAPullRequestTargets:
        def test_is_read_when_the_job_runs(self, world):
            """is read when the job runs

            An event file is frozen at the event that started the run; the API is not.
            """
            world.branch("adapter", "stable/x", fill=lambda path: (path / "STABLE").write_text("stable\n"))
            engine, event = world.engine_under_test()
            world.pull_requests.get("engine", 1)["base"]["ref"] = "stable/x"

            world.tool(engine, **world.ci(event=event, branch="main"))

            assert (
                world.record()["repositories"]["adapter"]["how"]
                == "stable/x, the branch matching the pull request's target"
            )

    class TestGivenTwoRepositoriesOfOneName:
        def test_keeps_a_row_for_each(self, world):
            engine, event = world.engine_under_test(body=depends_on("adapter", 9, owner="elsewhere"))
            world.pull_requests.open("adapter", 9, base="main")

            world.tool(engine, **world.ci(event=event))

            repositories = world.record()["repositories"]
            assert len([name for name in repositories if name.endswith("adapter")]) == 2

    class TestGivenANamedSpecificationPullRequest:
        def test_is_used_rather_than_listed_as_not_used(self, world):
            world.pull_request("cascade-bridge-spec", 3)
            engine, event = world.engine_under_test(body=depends_on("cascade-bridge-spec", 3))

            world.tool(engine, **world.ci(event=event))

            specification = world.record()["repositories"]["cascade-bridge-spec"]
            assert specification["role"] == "specification"
            assert specification["how"] == "pull request #3 merged into main"
            assert "not used" not in world.table()

    class TestGivenTheVersionPicked:
        def test_says_what_was_merged_in_before_it_was_handed_the_run(self, world):
            """says what was merged in before it was handed the run

            The run merges before it hops, and the version it hops to runs again on that checkout, finding its merges.
            """
            world.pull_request("engine", 2, fill=writing("TWO"))
            engine, event = engine_checked_out_as_ci_does(world, depends_on("engine", 2))
            world.tool(engine, **world.ci(event=event))

            world.tool(engine, **world.ci(event=event))

            assert (
                world.record()["repositories"]["engine"]["how"]
                == "pull request #1 merged into main, and #2 merged into it"
            )


class TestPullRequestsNamedInTheRepositoryUnderTest:
    """Pull requests named in the repository under test · Depends-On:

    A pull request may name others of its own repository; they are merged into its checkout in the order of their
    numbers, so a set that will land together is tested together.
    """

    class TestGivenAPullRequestNamingOneInItsOwnRepository:
        def test_is_tested_with_it_merged_in(self, world):
            """is tested with it merged in

            The pull request named in the repository under test is merged into the checkout under test, as Zuul does.
            """
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

    class TestGivenACycleOfThreeInTheRepositoryUnderTest:
        def test_merges_the_other_two_in_in_the_order_of_their_numbers(self, world):
            """merges the other two in, in the order of their numbers

            Reached through #3's own line, and merged in by number whichever line named it first.
            """
            two = world.pull_request("engine", 2, body=depends_on("engine", 1), fill=writing("TWO"))
            three = world.pull_request("engine", 3, body=depends_on("engine", 2), fill=writing("THREE"))
            engine, event = engine_checked_out_as_ci_does(world, depends_on("engine", 3))

            world.tool(engine, **world.ci(event=event))

            assert git("rev-parse", "HEAD^1^2", "HEAD^2", cwd=engine).split() == [two, three]
            assert world.record()["repositories"]["engine"]["how"] == (
                "pull request #1 merged into main, and #2 and #3 merged into it"
            )

    class TestGivenANamedPullRequestInTheRepositoryUnderTestMergedSinceTheRunsEvent:
        """given a named pull request in the repository under test, merged since the run's event"""

        def test_is_merged_in(self, world):
            """is merged in

            A rerun keeps the commit its event checked out, which a pull request that merged since does not hold.
            """
            world.pull_request("engine", 2, fill=writing("TWO"), state="closed", merged=True)
            engine, event = engine_checked_out_as_ci_does(world, depends_on("engine", 2))

            world.tool(engine, **world.ci(event=event))

            assert (engine / "TWO").is_file()

    class TestGivenANamedPullRequestAlreadyInTheCheckout:
        def test_is_not_said_to_be_merged_in(self, world):
            world.pull_request("engine", 2, fill=writing("TWO"), state="closed", merged=True)
            git("merge", "-q", "--no-ff", "--no-edit", "pull/2", cwd=world.origin("engine"))
            engine, event = engine_checked_out_as_ci_does(world, depends_on("engine", 2))

            world.tool(engine, **world.ci(event=event))

            assert world.record()["repositories"]["engine"]["how"] == "pull request #1 merged into main"
            assert "rerun it once" not in world.table()

    class TestGivenANamedPullRequestInTheRepositoryUnderTest:
        def test_is_merged_in_at_the_head_the_run_read(self, world):
            """is merged in at the head the run read

            A push after the run read the pull request is not tested unannounced.
            """
            world.pull_request("engine", 2, fill=writing("TWO"))
            later = world.branch("engine", "later", fill=writing("LATER"))
            git("update-ref", "refs/pull/2/head", later, cwd=world.origin("engine"))
            engine, event = engine_checked_out_as_ci_does(world, depends_on("engine", 2))

            world.tool(engine, **world.ci(event=event))

            assert (engine / "TWO").is_file()
            assert not (engine / "LATER").exists()

    class TestGivenANamedOpenPullRequestFromAFork:
        def test_is_not_merged_into_the_checkout_under_test(self, world):
            """is not merged into the checkout under test

            The checkout under test runs with the job's token, which a fork's code is not handed.
            """
            world.pull_request("engine", 2, fill=writing("TWO"), fork=True)
            engine, event = engine_checked_out_as_ci_does(world, depends_on("engine", 2))

            said = world.tool(engine, 1, **world.ci(event=event))

            assert "jayostis/engine/pull/2 is from a-fork-owner/engine" in said
            assert not (engine / "TWO").exists()

    class TestGivenAPullRequestOfTheEngineReachedOnlyThroughAnotherRepository:
        @pytest.mark.parametrize("state", ["open", "closed"], ids=["while open", "once closed"])
        def test_is_not_merged_in(self, world, state):
            """is not merged in

            Two pull requests of this engine that follow one vocabulary pull request are not bundled by it: each names the other.
            """
            world.pull_request("engine", 2, fill=writing("TWO"), state=state)
            world.pull_request("adapter", 7, body=depends_on("engine", 1) + depends_on("engine", 2))
            engine, event = engine_checked_out_as_ci_does(world, depends_on("adapter", 7))

            world.tool(engine, **world.ci(event=event))

            assert not (engine / "TWO").exists()
            [under_test] = [row for row in world.record()["repositories"].values() if row["role"] == "under test"]
            assert under_test["how"] == "pull request #1 merged into main"
            assert "jayostis/engine/pull/2, reached only through another repository's pull request" in world.table()

    class TestGivenTwoNamedPullRequestsInTheRepositoryUnderTestThatConflict:
        def test_fails_the_check_naming_them(self, world):
            """fails the check, naming them"""
            world.pull_request("engine", 2, fill=writing("SHARED", "two"))
            world.pull_request("engine", 3, fill=writing("SHARED", "three"))
            engine, event = engine_checked_out_as_ci_does(world, depends_on("engine", 2) + depends_on("engine", 3))

            said = world.tool(engine, 1, **world.ci(event=event))

            assert (
                "jayostis/engine/pull/3 does not merge cleanly into pull request #1 merged into main, and #2 merged into it"
                in said
            )

    class TestGivenANamedPullRequestInTheRepositoryUnderTestLandingOnAnotherBranch:
        def test_fails_the_check(self, world):
            world.branch("engine", "stable/x")
            world.pull_request("engine", 2, base="stable/x", fill=writing("TWO"))
            engine, event = engine_checked_out_as_ci_does(world, depends_on("engine", 2))

            said = world.tool(engine, 1, **world.ci(event=event))

            assert "jayostis/engine/pull/2 targets stable/x, and the pull request under test main" in said

    class TestGivenANamedPullRequestInTheRepositoryUnderTestClosedWithoutMerging:
        def test_fails_the_check_naming_the_line_to_cut(self, world):
            """fails the check, naming the line to cut"""
            world.pull_request("engine", 2, state="closed", fill=writing("TWO"))
            world.pull_request("engine", 3, body=depends_on("engine", 2), fill=writing("THREE"))
            engine, event = engine_checked_out_as_ci_does(world, depends_on("engine", 3))

            said = world.tool(engine, 1, **world.ci(event=event))

            assert (
                "jayostis/engine/pull/2 is closed without merging: cut the Depends-On: line naming it in jayostis/engine/pull/3"
                in said
            )


class TestPullRequestsARunCannotRead:
    """Pull requests a run cannot read · GITHUB_TOKEN

    A named pull request the run cannot read fails the check where the run would have used it, and is passed over where
    it would not. A failure of GitHub's own is said as that.
    """

    class TestGivenAClosedPullRequestInARepositoryTheRunChecksNothingOutFrom:
        def test_never_fails_the_check(self, world):
            world.pull_request("cascade-cli", 4, state="closed")
            engine, event = world.engine_under_test(body=depends_on("cascade-cli", 4))

            said = world.tool(engine, **world.ci(event=event))

            assert "cascade-cli" in world.table()
            assert world.record()["repositories"]["adapter"]["how"] == MATCHING
            assert "closed without merging" not in said

    class TestGivenAPullRequestTheAPIDoesNotServeInARepositoryTheRunChecksNothingOutFrom:
        """given a pull request the API does not serve, in a repository the run checks nothing out from"""

        def test_never_fails_the_check(self, world):
            engine, event = world.engine_under_test(body=depends_on("cascade-cli", 404))

            world.tool(engine, **world.ci(event=event))

            assert "cascade-cli" in world.table()

    class TestGivenAnUnreadablePullRequestInACounterpartRepository:
        def test_fails_the_check(self, world):
            """fails the check

            A typo or a deleted pull request names a version the run cannot have.
            """
            engine, event = world.engine_under_test(body=depends_on("adapter", 404))

            said = world.tool(engine, 1, **world.ci(event=event))

            assert "adapter/pull/404 could not be read" in said

    class TestGivenASpentRateLimit:
        def test_says_the_pull_request_could_not_be_read_naming_the_rate_limit(self, world):
            world.pull_requests.refuse("adapter", 7, 403, {"x-ratelimit-remaining": "0"})
            engine, event = world.engine_under_test(body=depends_on("adapter", 7))

            said = world.tool(engine, 1, **world.ci(event=event))

            assert "adapter/pull/7 could not be read" in said
            assert "rate limit" in said

    class TestGivenAnErrorOfGitHubsOwn:
        """given an error of GitHub's own"""

        def test_says_the_pull_request_could_not_be_read_naming_a_server_error(self, world):
            world.pull_requests.refuse("adapter", 7, 502)
            engine, event = world.engine_under_test(body=depends_on("adapter", 7))

            said = world.tool(engine, 1, **world.ci(event=event))

            assert "adapter/pull/7 could not be read" in said
            assert "GitHub answered with an error of its own" in said
