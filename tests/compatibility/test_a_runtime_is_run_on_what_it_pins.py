"""A runtime: handed the repositories cascade-runtime.json pins, each picked as a counterpart is, and judged by its report."""

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


def test_a_runtime_whose_report_holds_is_handed_each_pin_at_its_commit_and_names_the_bridge_release_it_pins(world):
    runtime, ci = world.runtime_under_test()

    said = world.tool(runtime, **ci)

    folders = handed(said)
    assert git("rev-parse", "HEAD", cwd=folders[VOCABULARY_URL]) == world.commits[VOCABULARY]
    assert git("rev-parse", "HEAD", cwd=folders[ADAPTER_URL]) == world.commits["adapter"]
    assert "the runtime on 1 host: 1 hold, 0 do not" in said
    assert "build-1" in world.record()["repositories"][BRIDGE]["how"]


def test_a_local_run_whose_report_has_a_failure_does_not_hold_and_a_pinned_siblings_edits_make_it_feedback(world):
    world.clone("adapter")
    (world.clone(VOCABULARY) / "NOTICE").write_text("an uncommitted edit\n", encoding="utf-8")
    world.offline()

    said = world.tool(world.runtime(canned="failed"), 1)

    assert "rule-2 is reported failed" in said
    assert "the runtime on 1 host: 0 hold, 1 do not" in said
    assert "a result produced from uncommitted edits is feedback, never evidence" in said


def test_a_vocabulary_pull_request_named_on_a_depends_on_line_is_handed_in_and_a_bridge_one_is_not_used(world):
    world.pull_request(VOCABULARY, 5, fill=lambda path: (path / "NOTICE").write_text("five\n"))
    world.pull_request(BRIDGE, 3)
    body = depends_on(VOCABULARY, 5, owner=VOCABULARY_OWNER) + depends_on(BRIDGE, 3, owner=BRIDGE_OWNER)
    runtime, ci = world.runtime_under_test(body=body)

    said = world.tool(runtime, **ci)

    assert (handed(said)[VOCABULARY_URL] / "NOTICE").read_text() == "five\n"
    repositories = world.record()["repositories"]
    assert repositories[VOCABULARY]["how"] == "pull request #5 merged into main"
    assert repositories[f"{BRIDGE_OWNER}/{BRIDGE}/pull/3"]["role"] == "not used"


def test_a_vocabulary_is_handed_in_for_the_vocabulary_of_each_runtime_it_names_picked_by_a_depends_on_line(world):
    world.runtime_origin()
    world.pull_request("runtime", 2)
    world.pull_request(VOCABULARY, 1, body=depends_on("runtime", 2, owner=OWNER))
    vocabulary = world.clone(VOCABULARY)
    (vocabulary / CRATE).write_text('{"@graph": [{"@id": "./", "@type": "Dataset"}]}', encoding="utf-8")
    write_compatibility(vocabulary, {"mustPassWith": [world.url("runtime")]})

    said = world.tool(vocabulary, **world.ci(repository=VOCABULARY, event=world.event(1, repository=VOCABULARY)))

    folders = handed(said)
    assert folders[VOCABULARY_URL] == vocabulary
    assert git("rev-parse", "HEAD", cwd=folders[ADAPTER_URL]) == world.commits["adapter"]
    assert world.record()["repositories"]["runtime"]["how"] == "pull request #2 merged into main"
    assert "the runtime on 1 host: 1 hold, 0 do not" in said
