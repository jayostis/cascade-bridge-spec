import argparse
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from compatibility_tool import (
    bootstrap,
    engines,
    github,
    judge,
    library,
    picking,
    placing,
    ready,
    runtimes,
    validate,
    vocabularies,
)
from compatibility_tool.console import Status, Stop, report
from compatibility_tool.document import counterparts, is_adapter, is_runtime, is_vocabulary, problems, read_file
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


def counterparts_placed(directory, listed, options, event, api):
    """The counterparts mustPassWith names and the vocabularies their adapters read, each with its reading."""
    reached = picking.follow(api, event, listed, options.spec_repository) if options.mode == "ci" else []
    counterpart_rows = []
    for url in listed:
        if options.mode == "local":
            counterpart_rows.append(placing.locally(directory, url, Role.COUNTERPART))
        else:
            into = directory.parent / github.repository_name(url)
            counterpart_rows.append(placing.in_ci(url, reached, event, into, Role.COUNTERPART))

    # A checked-out adapter is what names the vocabulary, so a Depends-On: line of it is reached only now.
    readings = vocabularies.read_from(directory, counterpart_rows)
    if readings and options.mode == "ci":
        reached = picking.follow(api, event, [*listed, *(reading.url for reading in readings)], options.spec_repository)
    placed = [(reading, vocabularies.place(directory, reading, options, event, reached)) for reading in readings]

    for entry in counterpart_rows:
        entry.adapter = directory if is_adapter(directory) else entry.path
        entry.vocabularies = next(
            (vocabulary.path for reading, vocabulary in placed if entry.adapter in reading.adapters), None
        )
    return [*counterpart_rows, *(vocabulary for _, vocabulary in placed), *placing.not_used(reached)], placed


def compatibility(directory, options, event, api, spec):
    document = read_file(directory)
    refused = problems(directory, document)
    for problem in refused:
        report(False, problem)

    used = [under_test(directory, options, event), spec]
    if refused:
        Record(directory, options.mode, used).save(options.results)
        return Status.FAIL

    runs_runtimes = is_runtime(directory) or is_vocabulary(directory)
    if is_runtime(directory):
        found, placed = runtimes.placed(directory, options, event, api), []
    elif runs_runtimes:
        found, placed = runtimes.named_by(directory, counterparts(document), options, event, api), []
    else:
        found, placed = counterparts_placed(directory, counterparts(document), options, event, api)
    used += found
    record = Record(directory, options.mode, used)
    record.save(options.results)
    for entry in used:
        report(True, entry.describe())

    status = validate.validate(directory, document, spec)
    for reading, vocabulary in placed:
        if status is not Status.FAIL:
            status = vocabularies.check(directory, vocabulary, reading)
    if status is not Status.FAIL:
        set_up = {}
        if runs_runtimes:
            runtimes.run(directory, record, options, set_up)
        else:
            engines.run(directory, record, options, set_up)
            library.run(directory, record, options, set_up)
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
    github.take_token()
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
            ready.check(directory, options, event, api)
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
