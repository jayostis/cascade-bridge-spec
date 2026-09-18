import argparse
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from compatibility_tool import bootstrap, engines, github, judge, picking, placing, ready, validate
from compatibility_tool.console import Status, Stop, report
from compatibility_tool.document import counterparts, is_adapter, problems, read_file
from compatibility_tool.record import Record, Role

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
        help="the cascade-bridge-spec the run picks a version of; the checkout this runs from, locally",
    )
    parser.add_argument("--spec-picked", type=Path, default=None, help=argparse.SUPPRESS)
    return parser.parse_args(argv)


def under_test(directory, options, event):
    if options.mode == "local":
        return placing.locally(directory, "", Role.UNDER_TEST)
    return placing.on_disk(
        directory.name,
        github.url_on_this_server(event.repository),
        directory,
        Role.UNDER_TEST,
        placing.under_test_is(event),
    )


def compatibility(directory, options, event, api, spec):
    document = read_file(directory)
    listed = counterparts(document)
    refused = problems(directory, document)
    for problem in refused:
        report(False, problem)

    used = [under_test(directory, options, event), spec]
    if refused:
        Record(directory, options.mode, used).save(options.results)
        return Status.FAIL

    reached = picking.follow(api, event, listed, options.spec_repository) if options.mode == "ci" else []
    for url in listed:
        if options.mode == "local":
            used.append(placing.locally(directory, url, Role.COUNTERPART))
        else:
            into = directory.parent / github.repository_name(url)
            used.append(placing.in_ci(url, reached, event, into, Role.COUNTERPART))
    used += placing.not_used(reached)
    for entry in used:
        if entry.role is Role.COUNTERPART:
            entry.adapter = directory if is_adapter(directory) else entry.path
    record = Record(directory, options.mode, used)
    record.save(options.results)
    for entry in used:
        report(True, entry.describe())

    status = validate.validate(directory, document, spec)
    if status is not Status.FAIL:
        engines.run(directory, record, options)
        status = judge.judge(record, options)
        record.save(options.results)
    judge.write_table(record, options)
    return status


def main(usage, argv=None):
    sys.stdout.reconfigure(line_buffering=True)  # a subprocess writes to this stdout too, and CI reads it in order
    args = parse(usage, argv)
    directory = args.directory.resolve()
    if not directory.is_dir():
        report(False, f"{directory} is not a directory")
        return Status.FAIL.exit_code

    options = Options(
        check=args.check,
        mode="ci" if os.environ.get("CI") == "true" else "local",
        results=Path(args.results).resolve()
        if args.results
        else Path(tempfile.gettempdir()) / "cascade-compatibility" / directory.name,
        spec_repository=args.spec_repository,
        spec_picked=args.spec_picked,
    )
    options.results.mkdir(parents=True, exist_ok=True)
    api = github.Api()
    try:
        event = github.event(api) if options.mode == "ci" else github.Event("", None, "")
        reached = picking.follow(api, event, [], options.spec_repository) if options.mode == "ci" else []
        spec = bootstrap.picked(directory, options, event, reached)
        hopped = bootstrap.hop(spec, directory, options)
        if hopped is not None:
            return hopped
        print(f"Repository: {directory}")
        print(f"Check:      {args.check} ({options.mode})")
        print()
        status = (
            ready.check(event, api)
            if args.check == "ready-to-merge"
            else compatibility(directory, options, event, api, spec)
        )
    except Stop as stop:
        report(False, str(stop))
        status = Status.FAIL
    print()
    print(f"{args.check}: {status.word}")
    print(status.verdict)
    return status.exit_code
