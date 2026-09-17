import sys

import pytest


def engine_beside_adapter(world, canned="passed", **overrides):
    engine = world.engine(world.adapter_pin(branch="main"), canned, **overrides)
    world.clone("adapter")
    return engine


def test_judge_holds_an_entry_whose_engine_passes_its_adapter(world):
    said = world.tool(engine_beside_adapter(world), ("checkout", 0), ("run", 0), ("judge", 0))
    assert "fake engine: testing" in said
    assert "branch main): holds; 1 cantTell, 1 passed, 1 untested" in said
    assert "judge: ok" in said
    assert "does not hold" not in said


@pytest.mark.parametrize(
    "canned, says",
    [
        pytest.param(
            "failed", ["does not hold; 1 cantTell, 1 failed, 1 untested"],
            id="judge fails an entry whose report has a failure, though the engine exits 0",
        ),
        pytest.param(
            "none", ["it wrote no report", "does not hold; it wrote no report"],
            id="judge fails an entry whose run wrote no report",
        ),
        pytest.param(
            "garbled", ["does not hold; its report does not parse as Turtle"],
            id="judge fails an entry whose report is not Turtle",
        ),
        pytest.param(
            "partial",
            [
                "does not hold; 1 passed; 2 of the manifest's 3 tests have no outcome: "
                "example-0002, example-release-2026-01"
            ],
            id="judge fails a report missing entries of the manifest, though none failed",
        ),
    ],
)
def test_judge_fails_an_entry_on_what_its_report_says(world, canned, says):
    said = world.tool(engine_beside_adapter(world, canned), ("checkout", 0), ("run", 0), ("judge", 1))
    for fragment in says:
        assert fragment in said


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param(
            {"command": None},
            id="judge says an entry whose engine states no command was not run, not that it wrote no report",
        ),
        pytest.param(
            {"setup": [sys.executable, "-c", "raise SystemExit(1)"]},
            id="judge says an entry whose engine's setup failed was not run, not that it wrote no report",
        ),
    ],
)
def test_judge_says_an_entry_never_run_was_not_run(world, overrides):
    engine = engine_beside_adapter(world, **overrides)
    said = world.tool(engine, ("checkout", 0), ("run", 1), ("judge", 1))
    assert "does not hold; it was not run" in said
    assert "it wrote no report" not in said


def test_judge_holds_an_entry_run_on_a_siblings_uncommitted_edits_and_flags_it(world):
    engine = engine_beside_adapter(world)
    (world.workspace / "adapter" / "README.md").write_text("an uncommitted edit\n", encoding="utf-8")
    said = world.tool(engine, ("checkout", 0), ("run", 0), ("judge", 0))
    assert "(branch main, with uncommitted edits): holds" in said
    assert "a result produced from uncommitted edits is feedback, never evidence" in said
