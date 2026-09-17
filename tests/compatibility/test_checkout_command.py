from pathlib import Path

from compatibility_world import git, sibling_state, write_compatibility


def test_checkout_reports_nothing_to_check_not_a_pass_for_an_engine_listing_no_counterpart(world):
    said = world.tool(world.clone("engine"), ("checkout", 0))
    assert "lists no counterpart: nothing to check" in said
    assert "checkout: nothing to check" in said
    assert "\nPASS\n" not in said


def test_checkout_stops_in_a_sentence_not_a_traceback_on_must_pass_with_written_as_one_object(world):
    said = world.tool(world.engine(world.adapter_pin(branch="main")[0]), ("checkout", 1))
    assert "mustPassWith is not a pin; run validate first" in said
    assert "Traceback" not in said


def test_checkout_stops_with_the_git_clone_command_for_a_missing_sibling(world):
    said = world.tool(world.engine(world.adapter_pin(branch="main")), ("checkout", 1))
    assert f"has no clone beside engine; clone it with: git clone {world.url('adapter')}" in said
    assert "Traceback" not in said


def test_resolve_uses_a_branch_pins_sibling_with_its_uncommitted_edits_and_flags_them(world):
    engine = world.engine(world.adapter_pin(branch="main"))
    (world.clone("adapter") / "README.md").write_text("an uncommitted edit\n", encoding="utf-8")
    said = world.tool(engine, ("resolve", 0))
    assert f"branch main is {world.commits['adapter']} (the sibling's working tree, with uncommitted edits)" in said
    assert "a result produced from uncommitted edits is feedback, never evidence" in said


def test_resolve_stops_in_a_sentence_on_a_counterpart_that_cannot_be_reached(world):
    unreachable = (world.origins / "renamed-away").as_uri()
    said = world.tool(world.engine([{"codeRepository": unreachable, "tag": "v1"}]), ("resolve", 1))
    assert "renamed-away could not be reached: it may be private, renamed or deleted" in said
    assert "Traceback" not in said


def test_checkout_runs_a_commit_pin_from_a_worktree_leaving_the_sibling_untouched(world):
    adapter = world.clone("adapter")
    pin = {"codeRepository": world.url("engine"), "commit": world.commits["engine"]}
    write_compatibility(adapter, {"mustPassWith": [pin]})
    engine = world.clone("engine")
    (engine / "work-in-progress.txt").write_text("not committed\n", encoding="utf-8")
    before = sibling_state(engine)

    said = world.tool(adapter, ("checkout", 0), ("run", 0), ("judge", 0))

    assert f"commit {world.commits['engine']} is {world.commits['engine']} (the commit pinned)" in said
    assert "holds" in said
    assert sibling_state(engine) == before
    checkout = Path(world.record(adapter)["pins"][0]["path"]).resolve()
    assert world.temporary.resolve() in checkout.parents


def test_checkout_in_ci_clones_the_counterpart_at_the_resolved_commit(world):
    engine = world.engine(world.adapter_pin(tag="v1"))
    said = world.tool(engine, ("checkout", 0), ("run", 0), ("judge", 0), mode="ci")
    assert f"tag v1 is {world.commits['adapter']} (the tag)" in said
    assert "holds" in said
    assert git("rev-parse", "HEAD", cwd=world.workspace / "adapter") == world.commits["adapter"]


def test_run_and_judge_refuse_an_earlier_checkout_once_a_later_one_fails_to_place_its_counterpart(world):
    world.own_origins()
    engine = world.engine(world.adapter_pin(tag="v1"))
    world.clone("adapter")
    said = world.tool(engine, ("checkout", 0), ("run", 0))

    origin = world.origins / "adapter"
    (origin / "LATER").write_text("committed after the sibling was cloned\n", encoding="utf-8")
    git("add", "-A", cwd=origin)
    git("commit", "-q", "-m", "feat: later", cwd=origin)
    write_compatibility(engine, world.engine_file(world.adapter_pin(commit=git("rev-parse", "HEAD", cwd=origin))))
    said += world.tool(engine, ("checkout", 1), ("run", 1), ("judge", 1))

    assert "does not hold " in said
    assert "the record holds no checkout: run checkout first" in said
    assert "holds;" not in said


def test_run_and_judge_refuse_an_earlier_checkout_once_a_later_one_fails_to_resolve_its_counterpart(world):
    engine = world.engine(world.adapter_pin(tag="v1"))
    world.clone("adapter")
    said = world.tool(engine, ("checkout", 0), ("run", 0))

    write_compatibility(engine, world.engine_file([{"codeRepository": world.url("specification"), "branch": "main"}]))
    said += world.tool(engine, ("checkout", 1), ("run", 1), ("judge", 1))

    assert "has no clone beside engine" in said
    assert "the record holds no checkout: run checkout first" in said
    assert "holds;" not in said
