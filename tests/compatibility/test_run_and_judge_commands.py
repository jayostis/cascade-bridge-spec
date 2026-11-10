"""Each engine on each adapter, judged by its EARL report."""

import sys

import pytest

from compatibility_world import engine_document


class TestRunningAnAdapterOnEveryHostOfAnEngine:
    """Running an adapter on every host of an engine · host, mustPassWith

    A host is one way an engine is built and run, such as natively or under Node. A counterpart is run and judged on
    every host, and one host on which it does not hold fails the run.
    """

    class TestGivenAnEntryWhoseEnginePassesItsAdapter:
        def test_holds(self, world):
            said = world.tool(world.engine_beside_adapter())
            assert "fake engine: testing" in said
            assert "holds; 1 cantTell, 8 passed, 1 untested" in said
            assert "does not hold" not in said
            assert "1 counterpart: 1 hold" in said
            assert "a result produced from uncommitted edits is feedback, never evidence" not in said

    class TestGivenAnEntryWhoseReportDoesNotHold:
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
        def test_does_not_hold_saying_what_its_report_says(self, world, canned, says):
            """does not hold, saying what its report says"""
            said = world.tool(world.engine_beside_adapter(canned), 1)
            for fragment in says:
                assert fragment in said

    class TestGivenAnEntryWhoseEnginesSetupFailed:
        """given an entry whose engine's setup failed"""

        def test_says_so_rather_than_that_it_wrote_no_report(self, world):
            engine = world.engine_beside_adapter(setup=[sys.executable, "-c", "raise SystemExit(1)"])
            said = world.tool(engine, 1)
            assert "does not hold; it was not run" in said
            assert "it wrote no report" not in said

    class TestGivenACounterpartEngineStatingNoCommand:
        def test_is_not_run_rather_than_refused(self, world):
            """is not run rather than refused

            A counterpart's files are read for what running it needs, never validated.
            """
            said = world.tool(world.adapter_beside_engine(engine_document([], command=None)), 1)
            assert "states no setup and command" in said
            assert "does not hold; it was not run" in said
