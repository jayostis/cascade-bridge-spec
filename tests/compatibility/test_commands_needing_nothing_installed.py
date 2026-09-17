import subprocess
import sys

WITHOUT_SITE_PACKAGES = (sys.executable, "-S")


def test_the_interpreter_without_site_packages_cannot_import_rdflib():
    run = subprocess.run([*WITHOUT_SITE_PACKAGES, "-c", "import rdflib"], capture_output=True)
    assert run.returncode != 0


def test_spec_pin_and_ready_run_with_no_package_installed(world):
    engine = world.engine(world.adapter_pin(branch="main"))
    said = world.tool(engine, ("spec-pin", 0), ("ready", 0), interpreter=WITHOUT_SITE_PACKAGES)
    said += world.tool(world.clone("adapter"), ("spec-pin", 0), interpreter=WITHOUT_SITE_PACKAGES)
    assert "Error" not in said
