"""Picking a version runs before anything is installed."""

import subprocess
import sys

from compatibility_world import depends_on

WITHOUT_SITE_PACKAGES = (sys.executable, "-S")


class TestRunningTheChecksFromTheVersionARunPicked:
    """Running the checks from the version a run picked · scripts/compatibility.py

    A caller fetches the default branch's tooling, which picks a version of the specification and hands the run to it.
    Picking happens before anything is installed.
    """

    class TestGivenTheMergeGate:
        def test_runs_with_no_package_installed(self, world):
            world.pull_request("adapter", 7, state="closed", merged=True)
            engine, event = world.engine_under_test(body=depends_on("adapter", 7))

            said = world.tool(
                engine, check="ready-to-merge", interpreter=WITHOUT_SITE_PACKAGES, **world.ci(event=event)
            )

            assert "Traceback" not in said

    class TestGivenACheckWithTheValidatorsMissing:
        def test_names_what_is_missing(self, world):
            said = world.tool(world.engine_beside_adapter(), 1, interpreter=WITHOUT_SITE_PACKAGES)

            assert "rdflib is not installed" in said
            assert "Traceback" not in said


class TestChecksOfTheSuitesOwnChecks:
    """Checks of the suite's own checks · tests/compatibility/"""

    class TestGivenTheInterpreterRunWithoutItsSitePackages:
        def test_imports_no_rdflib(self):
            run = subprocess.run([*WITHOUT_SITE_PACKAGES, "-c", "import rdflib"], capture_output=True)
            assert run.returncode != 0
