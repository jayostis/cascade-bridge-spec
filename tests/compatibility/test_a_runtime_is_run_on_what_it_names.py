"""A runtime: handed the repositories cascade-runtime.json names, each picked as a counterpart is, and judged by its report."""

import json
from pathlib import Path

from compatibility_world import (
    ADAPTER_URL,
    BRIDGE,
    BRIDGE_OWNER,
    CRATE,
    OWNER,
    VOCABULARY,
    VOCABULARY_OWNER,
    VOCABULARY_URL,
    depends_on,
    git,
    write_compatibility,
)

HANDED = "fake runtime: folder "


def handed(said):
    return dict(
        (repository, Path(folder))
        for repository, _, folder in (
            line.split(HANDED, 1)[1].strip().partition(" ") for line in said.splitlines() if HANDED in line
        )
    )


def a_local_run_of_a_runtime_whose_report_failed(world):
    world.clone("adapter")
    (world.clone(VOCABULARY) / "NOTICE").write_text("an uncommitted edit\n", encoding="utf-8")
    world.offline()
    return world.tool(world.runtime(canned="failed"), 1)


def a_vocabulary_and_a_bridge_pull_request_named(world):
    world.pull_request(VOCABULARY, 5, fill=lambda path: (path / "NOTICE").write_text("five\n"))
    world.pull_request(BRIDGE, 3)
    body = depends_on(VOCABULARY, 5, owner=VOCABULARY_OWNER) + depends_on(BRIDGE, 3, owner=BRIDGE_OWNER)
    runtime, ci = world.runtime_under_test(body=body)
    return world.tool(runtime, **ci), body


class TestRunningARuntimeOnTheRepositoriesItNames:
    """Running a runtime on the repositories it names · cascade-runtime.json, --folder, --checkout-only

    A runtime names its vocabulary and adapters in `cascade-runtime.json`. A run picks each, hands it to the runtime's
    conformance command by folder, and judges the report the command writes.
    """

    class TestGivenARuntimeWhoseReportHolds:
        def test_is_handed_each_repository_it_names_at_the_head_of_its_default_branch(self, world):
            """is handed each repository it names, at the head of its default branch"""
            runtime, ci = world.runtime_under_test()

            said = world.tool(runtime, **ci)

            folders = handed(said)
            assert git("rev-parse", "HEAD", cwd=folders[VOCABULARY_URL]) == world.commits[VOCABULARY]
            assert git("rev-parse", "HEAD", cwd=folders[ADAPTER_URL]) == world.commits["adapter"]
            assert "the runtime on 1 host: 1 hold, 0 do not" in said

    class TestGivenACheckoutOnlyRun:
        """given a checkout-only run"""

        def test_places_each_repository_a_depends_on_line_picks_running_nothing(self, world):
            """places each repository a `Depends-On:` line picks, running nothing"""
            world.pull_request(VOCABULARY, 5, fill=lambda path: (path / "NOTICE").write_text("five\n"))
            runtime, ci = world.runtime_under_test(body=depends_on(VOCABULARY, 5, owner=VOCABULARY_OWNER))

            said = world.tool(runtime, CASCADE_CHECKOUT_ONLY="true", **ci)

            assert world.record()["repositories"][VOCABULARY]["how"] == "pull request #5 merged into main"
            assert (runtime.parent / VOCABULARY / "NOTICE").read_text() == "five\n"
            assert HANDED not in said
            assert not (world.results / "earl").exists()

    class TestGivenACheckoutOnlyRunOfTheMergeGate:
        """given a checkout-only run of the merge gate"""

        def test_is_refused(self, world):
            runtime, ci = world.runtime_under_test()

            said = world.tool(runtime, 1, check="ready-to-merge", checkout_only=True, **ci)

            assert "--checkout-only places the counterparts of compatibility" in said

    class TestGivenALocalRunWhoseReportHasAFailure:
        def test_does_not_hold(self, world):
            said = a_local_run_of_a_runtime_whose_report_failed(world)

            assert "rule-2 is reported failed" in said
            assert "the runtime on 1 host: 0 hold, 1 do not" in said

        def test_says_a_failure_is_feedback_where_a_named_sibling_has_uncommitted_edits(self, world):
            said = a_local_run_of_a_runtime_whose_report_failed(world)

            assert "a result produced from uncommitted edits is feedback, never evidence" in said

    class TestGivenAVocabularyPullRequestNamedOnADependsOnLine:
        """given a vocabulary pull request named on a `Depends-On:` line"""

        def test_is_handed_in_to_the_runtime(self, world):
            said, body = a_vocabulary_and_a_bridge_pull_request_named(world)

            assert (handed(said)[VOCABULARY_URL] / "NOTICE").read_text() == "five\n"
            assert world.record()["repositories"][VOCABULARY]["how"] == "pull request #5 merged into main"

    class TestGivenABridgePullRequestNamedOnADependsOnLine:
        """given a Bridge pull request named on a `Depends-On:` line"""

        def test_is_listed_as_not_used_and_is_in_the_pull_requests_the_command_is_given_to_read(self, world):
            """is listed as not used, and is in the pull requests the command is given to read"""
            said, body = a_vocabulary_and_a_bridge_pull_request_named(world)

            assert world.record()["repositories"][BRIDGE]["role"] == "not used"
            read = json.loads(Path(said.split("fake runtime: pull requests ", 1)[1].splitlines()[0]).read_text())
            assert read[f"{BRIDGE_OWNER}/{BRIDGE}/pull/3"]["state"] == "open"
            assert read[f"{OWNER}/runtime/pull/1"]["body"] == body

    class TestGivenAVocabularyUnderTest:
        def test_is_handed_the_vocabulary_the_adapter_at_its_commit_and_the_runtime_its_depends_on_line_picks(
            self, world
        ):
            """is handed the vocabulary, the adapter at its commit and the runtime its `Depends-On:` line picks"""
            world.runtime_origin()
            world.pull_request("runtime", 2)
            world.pull_request(VOCABULARY, 1, body=depends_on("runtime", 2, owner=OWNER))
            vocabulary = world.clone(VOCABULARY)
            (vocabulary / CRATE).write_text('{"@graph": [{"@id": "./", "@type": "Dataset"}]}', encoding="utf-8")
            write_compatibility(vocabulary, {"mustPassWith": [world.url("runtime")]})

            said = world.tool(
                vocabulary, **world.ci(repository=VOCABULARY, event=world.event(1, repository=VOCABULARY))
            )

            folders = handed(said)
            assert folders[VOCABULARY_URL] == vocabulary
            assert git("rev-parse", "HEAD", cwd=folders[ADAPTER_URL]) == world.commits["adapter"]
            assert world.record()["repositories"]["runtime"]["how"] == "pull request #2 merged into main"
            assert "the runtime on 1 host: 1 hold, 0 do not" in said
