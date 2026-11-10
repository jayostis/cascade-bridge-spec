"""The start action's outputs: the one report a run wrote, the case report, and the artifact the case report goes in."""

import os
import re
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

ACTION = Path(__file__).resolve().parents[2] / ".github" / "actions" / "start" / "action.yml"


def bash():
    """Git's bash where there is one: on Windows, `bash` on the path may be WSL's, which cannot read these paths."""
    git = shutil.which("git")
    beside_git = Path(git).parents[1] / "bin" / "bash.exe" if git and os.name == "nt" else None
    return str(beside_git) if beside_git and beside_git.is_file() else shutil.which("bash")


pytestmark = pytest.mark.skipif(bash() is None, reason="the step is bash")


def outputs_of_the_step(tmp_path, name, **environment):
    """What the action's step of this name writes to its outputs, run in bash with only these variables."""
    step = re.search(
        rf"- name: {re.escape(name)}\n(?:.*\n)*?      run: \|\n((?:        .*\n|\n)+)",
        ACTION.read_text(encoding="utf-8"),
    )
    script = tmp_path / "step.sh"
    script.write_text(textwrap.dedent(step.group(1)), encoding="utf-8")
    outputs = tmp_path / "outputs"
    outputs.touch()
    variables = {"PATH": os.environ["PATH"], "GITHUB_OUTPUT": outputs.as_posix(), **environment}
    subprocess.run([bash(), script.as_posix()], env=variables, check=True)
    return outputs.read_text(encoding="utf-8").strip()


def results_holding(tmp_path, *written):
    results = tmp_path / "results"
    for name in written:
        (results / name).parent.mkdir(parents=True, exist_ok=True)
        (results / name).write_text("", encoding="utf-8")
    results.mkdir(exist_ok=True)
    return results


class TestTheReportARunNamesForItsCaller:
    """The report a run names for its caller · .github/actions/start

    A job that reads what a run wrote reads the start action's outputs, never a path it assumes: `report` for the EARL
    report, `cases` for the case report, and `report-artifact` for the artifact that holds it. Each is empty or absent
    when the run wrote nothing it could name.
    """

    class TestWhenTheStartActionNamesTheReportItWrote:
        """when the start action names the report it wrote"""

        @pytest.mark.parametrize(
            ("written", "named"),
            [
                ([], None),
                (["conformance-on-host-1.ttl"], "conformance-on-host-1.ttl"),
                (["conformance-on-host-1.ttl", "conformance-on-host-2.ttl"], None),
            ],
            ids=["no report", "one report", "several reports"],
        )
        def test_names_the_report_only_when_the_run_wrote_exactly_one(self, tmp_path, written, named):
            results = results_holding(tmp_path, *(f"earl/{name}" for name in written))

            output = outputs_of_the_step(tmp_path, "name the report the check wrote", RESULTS=results.as_posix())

            assert output == (f"path={(results / 'earl' / named).as_posix()}" if named else "")

    class TestWhenTheStartActionNamesTheCaseReportItWrote:
        @pytest.mark.parametrize(
            "written", [["report.ctrf.json"], []], ids=["a case report written", "no case report written"]
        )
        def test_names_report_ctrf_json_only_when_the_run_wrote_one(self, tmp_path, written):
            """names `report.ctrf.json` only when the run wrote one"""
            results = results_holding(tmp_path, *written)

            output = outputs_of_the_step(tmp_path, "name the report the check wrote", RESULTS=results.as_posix())

            assert (f"cases={(results / 'report.ctrf.json').as_posix()}" in output.splitlines()) == bool(written)
            assert output.count("cases=") == len(written)

    class TestWhenTheStartActionNamesTheArtifactForTheCaseReport:
        @pytest.mark.parametrize(
            ("path", "named"),
            [
                ("cascade-bridge-adapter-fhir-r4", "report-cascade-bridge-adapter-fhir-r4"),
                ("cascade-bridge-spec/fixtures/synthetic-adapter", "report-synthetic-adapter"),
            ],
            ids=["a repository", "a folder inside one"],
        )
        def test_names_the_artifact_report_and_the_directory_under_test(self, tmp_path, path, named):
            """names the artifact `report-` and the directory under test"""
            output = outputs_of_the_step(
                tmp_path, "name the results for this leg", REPOSITORY_PATH=path, JOB="build", CHECK="compatibility"
            )

            assert f"report={named}" in output.splitlines()
            assert re.search(r"^name=compatibility-build-\d+$", output, re.MULTILINE)
