import argparse
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from compatibility_tool import git, github, picking, placing
from compatibility_tool.console import Status, Stop, report
from compatibility_tool.document import SPEC_ROOT, counterparts, read_file
from compatibility_tool.record import Record, Role, Used

SPECIFICATION = "cascade-bridge-spec"
CHECKS = ("compatibility", "ready-to-merge")


@dataclass(frozen=True)
class Options:
    check: str
    mode: str
    results: Path
    spec_repository: str | None
    spec_picked: Path | None


def parse(usage, argv):
    parser = argparse.ArgumentParser(description=usage, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "directory",
        type=Path,
        nargs="?",
        default=Path("."),
        help="the repository under test; the current directory when omitted",
    )
    parser.add_argument("--check", choices=CHECKS, default=CHECKS[0])
    parser.add_argument("--results", default=None, help="where the record and the EARL reports go")
    parser.add_argument(
        "--spec-repository",
        default=os.environ.get("CASCADE_SPEC_REPOSITORY"),
        help=f"the {SPECIFICATION} the run picks a version of; the checkout this runs from, locally",
    )
    parser.add_argument("--spec-picked", type=Path, default=None, help=argparse.SUPPRESS)
    return parser.parse_args(argv)


def under_test(directory, options, event):
    if options.mode == "local":
        return placing.locally(directory, "", Role.UNDER_TEST)
    entry = placing.on_disk(directory.name, own_url(event.repository), directory, Role.UNDER_TEST)
    entry.how = (
        f"pull request #{event.number} merged into {event.branch}"
        if event.number
        else f"{event.branch}, the branch this run is on"
    )
    return entry


def own_url(repository):
    server = os.environ.get("GITHUB_SERVER_URL", "https://github.com").rstrip("/")
    return f"{server}/{repository}"


def specification(directory, options, event, reached):
    if options.spec_picked:
        return Used.from_json(SPECIFICATION, json.loads(options.spec_picked.read_text(encoding="utf-8")))
    if options.mode == "local":
        return placing.on_disk(SPECIFICATION, options.spec_repository or "", SPEC_ROOT, Role.SPECIFICATION)
    if not options.spec_repository:
        raise Stop(f"the check was not told which repository is {SPECIFICATION}; start passes --spec-repository")
    if github.repository_path(options.spec_repository) == event.repository:
        # The repository under test is this one: its checkout is the version, whatever the caller bootstrapped.
        checkout = git.toplevel(directory) or SPEC_ROOT
        entry = placing.on_disk(SPECIFICATION, options.spec_repository, checkout, Role.SPECIFICATION)
        entry.how = under_test(directory, options, event).how
        return entry
    into = directory.parent / SPECIFICATION
    return placing.in_ci(options.spec_repository, reached, event.branch, bool(event.number), into, Role.SPECIFICATION)


def run_from_the_picked_specification(spec, directory, options):
    """The rules run from the version picked, not from the one the caller bootstrapped."""
    picked = options.results / "specification.json"
    picked.write_text(json.dumps(spec.to_json()), encoding="utf-8")
    argv = [
        sys.executable,
        str(spec.path / "scripts" / "compatibility.py"),
        str(directory),
        "--check",
        options.check,
        "--results",
        str(options.results),
        "--spec-picked",
        str(picked),
    ]
    print(f"  note  the specification is {spec.commit} ({spec.how}); the checks run from {spec.path}")
    status = subprocess.run(argv).returncode
    if status not in (0, 1):
        report(False, f"{argv[1]} did not run the check: it exited {status}")
    return status


def ours(spec):
    return spec.path and Path(spec.path).resolve() == SPEC_ROOT


def compatibility(directory, options, event, api):
    from compatibility_tool import engines, judge, validate

    document = read_file(directory)
    listed = counterparts(document)
    problems = validate.form_problems(directory, document)
    for problem in problems:
        report(False, problem)

    checked_out = {event.repository, *(github.repository_path(url) for url in listed)}
    if options.spec_repository:
        checked_out.add(github.repository_path(options.spec_repository))
    reached = picking.follow(api, event.under_test, checked_out) if options.mode == "ci" else []
    spec = specification(directory, options, event, reached)
    if options.mode == "ci" and not options.spec_picked and not ours(spec):
        return Status.FAIL if run_from_the_picked_specification(spec, directory, options) else Status.OK

    used = [under_test(directory, options, event), spec]
    if problems:
        Record(directory, options.mode, used).save(options.results)
        return Status.FAIL

    for url in listed:
        if options.mode == "local":
            used.append(placing.locally(directory, url, Role.COUNTERPART))
        else:
            into = directory.parent / github.repository_name(url)
            used.append(placing.in_ci(url, reached, event.branch, bool(event.number), into, Role.COUNTERPART))
    for entry in reached:
        if not entry.used:
            used.append(
                Used(
                    name=entry.named.path.split("/")[-1],
                    repository=own_url(entry.named.path),
                    commit=entry.pull.get("head", {}).get("sha"),
                    how=f"{entry.named.label}, in a repository this run checks nothing out from",
                    role=Role.NOT_USED,
                )
            )
    record = Record(directory, options.mode, used)
    record.save(options.results)
    for entry in used:
        report(True, entry.describe())

    status = validate.validate(directory, document, spec)
    if status is Status.FAIL:
        judge.write_table(record, options, api, event)
        return status
    engines.run(directory, record, options)
    judged = judge.judge(record, options)
    record.save(options.results)
    judge.write_table(record, options, api, event)
    return judged


def ready_to_merge(event, api):
    from compatibility_tool import ready

    return ready.check(event, api)


def main(usage, argv=None):
    args = parse(usage, argv)
    directory = args.directory.resolve()
    if not directory.is_dir():
        report(False, f"{directory} is not a directory")
        return Status.FAIL.exit_code

    results = (
        Path(args.results).resolve()
        if args.results
        else Path(tempfile.gettempdir()) / "cascade-compatibility" / directory.name
    )
    results.mkdir(parents=True, exist_ok=True)
    options = Options(
        check=args.check,
        mode="ci" if os.environ.get("CI") == "true" else "local",
        results=results,
        spec_repository=args.spec_repository,
        spec_picked=args.spec_picked,
    )
    api = github.Api()
    print(f"Repository: {directory}")
    print(f"Check:      {args.check} ({options.mode})")
    print()
    try:
        event = github.event(api) if options.mode == "ci" else github.Event("", None, "")
        if args.check == "ready-to-merge":
            status = ready_to_merge(event, api)
        else:
            status = compatibility(directory, options, event, api)
    except Stop as stop:
        report(False, str(stop))
        status = Status.FAIL
    print()
    print(f"{args.check}: {status.word}")
    print(status.verdict)
    return status.exit_code
