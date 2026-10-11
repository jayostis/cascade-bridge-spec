"""The start action's report output: the one report a run wrote, or nothing."""

import os
import re
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

ACTION = Path(__file__).resolve().parents[2] / ".github" / "actions" / "start" / "action.yml"
STEP = re.compile(r"- name: name the report the check wrote\n(?:.*\n)*?      run: \|\n((?:        .*\n|\n)+)")


def bash():
    """Git's bash where there is one: on Windows, `bash` on the path may be WSL's, which cannot read these paths."""
    git = shutil.which("git")
    beside_git = Path(git).parents[1] / "bin" / "bash.exe" if git and os.name == "nt" else None
    return str(beside_git) if beside_git and beside_git.is_file() else shutil.which("bash")


pytestmark = pytest.mark.skipif(bash() is None, reason="the step is bash")


def output_of_the_step(tmp_path, written):
    earl = tmp_path / "earl"
    earl.mkdir()
    for name in written:
        (earl / name).write_text("", encoding="utf-8")
    script = tmp_path / "step.sh"
    script.write_text(textwrap.dedent(STEP.search(ACTION.read_text(encoding="utf-8")).group(1)), encoding="utf-8")
    outputs = tmp_path / "outputs"
    outputs.touch()
    environment = {"PATH": os.environ["PATH"], "EARL": earl.as_posix(), "GITHUB_OUTPUT": outputs.as_posix()}
    subprocess.run([bash(), script.as_posix()], env=environment, check=True)
    return outputs.read_text(encoding="utf-8").strip(), earl


@pytest.mark.parametrize(
    ("written", "named"),
    [
        ([], None),
        (["conformance-on-host-1.ttl"], "conformance-on-host-1.ttl"),
        (["conformance-on-host-1.ttl", "conformance-on-host-2.ttl"], None),
    ],
    ids=["none", "one", "several"],
)
def test_report_names_the_report_only_when_the_run_wrote_exactly_one(tmp_path, written, named):
    output, earl = output_of_the_step(tmp_path, written)

    assert output == (f"path={(earl / named).as_posix()}" if named else "")
