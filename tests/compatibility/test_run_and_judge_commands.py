"""Each engine on each adapter, judged by its EARL report."""

import sys

import pytest

from compatibility_world import engine_document


def test_an_entry_whose_engine_passes_its_adapter_holds(world):
    said = world.tool(world.engine_beside_adapter())
    assert "fake engine: testing" in said
    assert "holds; 1 cantTell, 8 passed, 1 untested" in said
    assert "does not hold" not in said
    assert "1 counterpart: 1 hold" in said
    assert "a result produced from uncommitted edits is feedback, never evidence" not in said


@pytest.mark.parametrize(
    "canned, says",
    [
        pytest.param(
            "failed",
            ["does not hold; 1 cantTell, 1 failed, 7 passed, 1 untested"],
            id="a report with a failure, though the engine exits 0",
        ),
        pytest.param(
            "none",
            ["it wrote no report", "does not hold; it wrote no report"],
            id="a run that wrote no report",
        ),
    ],
)
def test_an_entry_does_not_hold_on_what_its_report_says(world, canned, says):
    said = world.tool(world.engine_beside_adapter(canned), 1)
    for fragment in says:
        assert fragment in said


def test_an_entry_whose_engines_setup_failed_says_so_rather_than_that_it_wrote_no_report(world):
    engine = world.engine_beside_adapter(setup=[sys.executable, "-c", "raise SystemExit(1)"])
    said = world.tool(engine, 1)
    assert "does not hold; it was not run" in said
    assert "it wrote no report" not in said


def test_a_counterpart_engine_stating_no_command_is_not_run_rather_than_refused(world):
    """A counterpart's files are read for what running it needs, never validated."""
    said = world.tool(world.adapter_beside_engine(engine_document([], command=None)), 1)
    assert "states no setup and command" in said
    assert "does not hold; it was not run" in said
