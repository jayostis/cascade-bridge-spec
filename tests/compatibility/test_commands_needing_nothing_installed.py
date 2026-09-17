"""Picking a version runs before anything is installed."""

import subprocess
import sys

from test_picking_versions import depends_on, engine_under_test

WITHOUT_SITE_PACKAGES = (sys.executable, "-S")


def test_the_interpreter_without_site_packages_cannot_import_rdflib():
    run = subprocess.run([*WITHOUT_SITE_PACKAGES, "-c", "import rdflib"], capture_output=True)
    assert run.returncode != 0


def test_the_merge_gate_runs_with_no_package_installed(world):
    world.pull_request("adapter", 7, state="closed", merged=True)
    engine, event = engine_under_test(world, body=depends_on("adapter", 7))

    said = world.tool(
        engine, check="ready-to-merge", interpreter=WITHOUT_SITE_PACKAGES, **world.ci(event=event)
    )

    assert "Traceback" not in said


def test_a_check_with_the_validators_missing_names_what_is_missing(world):
    engine, event = engine_under_test(world)

    said = world.tool(engine, 1, interpreter=WITHOUT_SITE_PACKAGES, **world.ci(event=event))

    assert "rdflib" in said
    assert "Traceback" not in said
