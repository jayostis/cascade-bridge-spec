"""What a run records: a row per repository it used, on the summary page and as a comment."""

from compatibility_world import git
from test_picking_versions import depends_on, engine_under_test


def test_the_table_has_a_row_for_the_repository_under_test_the_specification_and_each_counterpart(world):
    engine, event = engine_under_test(world)

    world.tool(engine, **world.ci(event=event))

    table = world.table()
    for repository in ("engine", "cascade-bridge-spec", "adapter"):
        assert f"| [{repository}]" in table
    assert "pull request #1 merged into main" in table


def test_only_a_counterparts_row_says_whether_it_holds(world):
    engine, event = engine_under_test(world)

    world.tool(engine, **world.ci(event=event))

    rows = {line.split("|")[1].strip(): line for line in world.table().splitlines() if line.startswith("|")}
    assert "holds" in rows["[adapter](" + world.url("adapter") + ")"]
    assert "holds" not in rows["[engine](" + world.url("engine") + ")"]
    assert "holds" not in rows["[cascade-bridge-spec](" + world.url("cascade-bridge-spec") + ")"]


def test_the_table_is_posted_as_a_new_comment_on_the_pull_request(world):
    engine, event = engine_under_test(world)

    world.tool(engine, **world.ci(event=event))

    (repository, number, body) = world.pull_requests.comments[-1]
    assert (repository, number) == ("engine", 1)
    assert "| adapter |" in body or "[adapter]" in body


def test_a_run_that_used_a_named_pull_request_says_the_pass_is_as_fresh_as_it_is(world):
    """There is no gate queue: whoever merges has to rerun once the named one has merged."""
    world.pull_request("adapter", 7)
    engine, event = engine_under_test(world, body=depends_on("adapter", 7))

    world.tool(engine, **world.ci(event=event))

    assert "rerun" in world.table()
    assert "before merging" in world.table()


def test_a_run_that_used_no_named_pull_request_says_nothing_about_rerunning(world):
    engine, event = engine_under_test(world)

    world.tool(engine, **world.ci(event=event))

    assert "rerun" not in world.table()


def test_the_pull_request_under_test_is_not_a_named_pull_request(world):
    """The specification's own CI: its row is the pull request under test, which needs no rerun."""
    world.pull_request("cascade-bridge-spec", 1)
    subject = world.clone("cascade-bridge-spec") / "fixtures" / "synthetic-adapter"

    world.tool(subject, **world.ci(repository="cascade-bridge-spec", event=world.event(1, "cascade-bridge-spec")))

    assert "pull request #1 merged into main" in world.table()
    assert "rerun" not in world.table()


def test_a_comment_the_api_refuses_is_said_and_leaves_the_exit_status_unchanged(world):
    engine, event = engine_under_test(world)
    world.pull_requests.refuse_comments = True

    said = world.tool(engine, **world.ci(event=event))

    assert "no comment was posted" in said
    assert world.pull_requests.comments == []


def test_a_counterpart_in_the_form_this_epic_removes_is_run_and_judged(world):
    """Rule: a counterpart's files are read for what running it needs, never validated."""
    crate = world.origin("adapter") / "ro-crate-metadata.json"
    crate.write_text(crate.read_text(encoding="utf-8").replace('"@id": "./"', '"bridge:specPin": "old", "@id": "./"'))
    git("commit", "-qam", "the form this epic removes", cwd=world.origin("adapter"))
    engine, event = engine_under_test(world)

    said = world.tool(engine, **world.ci(event=event))

    assert "holds" in said
    assert "does not hold" not in said
