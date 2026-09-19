"""Each engine on each adapter, judged by its EARL report."""

import sys

import pytest

from compatibility_world import engine_document, git, write_compatibility


def engine_beside_adapter(world, canned="passed", **overrides):
    engine = world.engine([world.url("adapter")], canned, **overrides)
    world.clone("adapter")
    git("remote", "set-url", "origin", "https://example.invalid/gone.git", cwd=world.workspace / "adapter")
    return engine


def test_an_entry_whose_engine_passes_its_adapter_holds(world):
    said = world.tool(engine_beside_adapter(world))
    assert "fake engine: testing" in said
    assert "holds; 1 cantTell, 2 passed, 1 untested" in said
    assert "does not hold" not in said


@pytest.mark.parametrize(
    "canned, says",
    [
        pytest.param(
            "failed",
            ["does not hold; 1 cantTell, 1 failed, 1 passed, 1 untested"],
            id="a report with a failure, though the engine exits 0",
        ),
        pytest.param(
            "none",
            ["it wrote no report", "does not hold; it wrote no report"],
            id="a run that wrote no report",
        ),
        pytest.param(
            "garbled",
            ["does not hold; its report does not parse as Turtle"],
            id="a report that is not Turtle",
        ),
        pytest.param(
            "partial",
            [
                "does not hold; 1 passed; 3 of the manifest's 4 tests have no outcome: "
                "example-0002, example-0003, example-release-2026-01"
            ],
            id="a report missing entries of the manifest, though none failed",
        ),
    ],
)
def test_an_entry_does_not_hold_on_what_its_report_says(world, canned, says):
    said = world.tool(engine_beside_adapter(world, canned), 1)
    for fragment in says:
        assert fragment in said


def test_an_entry_whose_engines_setup_failed_says_so_rather_than_that_it_wrote_no_report(world):
    engine = engine_beside_adapter(world, setup=[sys.executable, "-c", "raise SystemExit(1)"])
    said = world.tool(engine, 1)
    assert "does not hold; it was not run" in said
    assert "it wrote no report" not in said


def test_a_counterpart_engine_stating_no_command_is_not_run_rather_than_refused(world):
    """A counterpart's files are read for what running it needs, never validated."""
    adapter = world.clone("adapter")
    write_compatibility(adapter, {"mustPassWith": [world.url("engine")]})
    engine = world.clone("engine")
    write_compatibility(engine, engine_document([], command=None))
    said = world.tool(adapter, 1)
    assert "states no setup and command" in said
    assert "does not hold; it was not run" in said


def test_an_entry_run_on_a_siblings_uncommitted_edits_is_flagged(world):
    engine = engine_beside_adapter(world)
    (world.workspace / "adapter" / "README.md").write_text("an uncommitted edit\n", encoding="utf-8")
    said = world.tool(engine)
    assert "uncommitted edits): holds" in said
    assert "a result produced from uncommitted edits is feedback, never evidence" in said
