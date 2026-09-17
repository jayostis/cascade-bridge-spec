"""The hop from the version a caller fetched to start to the version the run picks."""

import json
import subprocess
import sys
from pathlib import Path

from compatibility_tool import github, placing
from compatibility_tool.console import Stop, note
from compatibility_tool.record import Role, Row

SPECIFICATION = "cascade-bridge-spec"
SPEC_ROOT = Path(__file__).resolve().parents[2]
ENTRY_POINT = ("scripts", "compatibility.py")


def picked(directory, options, event, reached):
    if options.spec_picked:
        return Row.from_json(SPECIFICATION, json.loads(options.spec_picked.read_text(encoding="utf-8")))
    if options.mode == "local":
        return placing.on_disk(
            SPECIFICATION,
            options.spec_repository or "",
            SPEC_ROOT,
            Role.SPECIFICATION,
            "the checkout the tooling runs from",
        )
    if not options.spec_repository:
        raise Stop(f"the check was not told which repository is {SPECIFICATION}; start passes --spec-repository")
    if github.repository_path(options.spec_repository) == event.repository:
        # The repository under test is this one, so its checkout is the version.
        return placing.on_disk(
            SPECIFICATION,
            options.spec_repository,
            placing.toplevel(directory, SPEC_ROOT),
            Role.SPECIFICATION,
            placing.under_test_is(event),
        )
    into = directory.parent / SPECIFICATION
    return placing.in_ci(options.spec_repository, reached, event, into, Role.SPECIFICATION)


def running_from(spec):
    return spec.path and Path(spec.path).resolve() == SPEC_ROOT


def hop(spec, directory, options):
    """The child's exit status, or None when this process is already the version picked."""
    if options.mode != "ci" or options.spec_picked or running_from(spec):
        return None
    handover = options.results / "specification.json"
    options.results.mkdir(parents=True, exist_ok=True)
    handover.write_text(json.dumps(spec.to_json()), encoding="utf-8")
    entry_point = spec.path.joinpath(*ENTRY_POINT)
    if not entry_point.is_file():
        raise Stop(f"{spec.repository} at {spec.commit} holds no {'/'.join(ENTRY_POINT)} to run the checks from")
    note(f"the specification is {spec.commit} ({spec.how}); the checks run from {entry_point}")
    argv = [
        sys.executable,
        str(entry_point),
        str(directory),
        "--check",
        options.check,
        "--results",
        str(options.results),
        "--spec-repository",
        options.spec_repository,
        "--spec-picked",
        str(handover),
    ]
    status = subprocess.run(argv).returncode
    if status not in (0, 1):
        raise Stop(f"{entry_point} did not run the check: it exited {status}")
    return status
