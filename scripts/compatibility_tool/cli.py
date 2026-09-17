import argparse
import importlib
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from compatibility_tool.console import Status, Stop, report
from compatibility_tool.document import SPEC_ROOT

COMMANDS = {
    "spec-pin": ("document", "spec_pin_command"),
    "validate": ("validate", "validate_command"),
    "resolve": ("pins", "resolve_command"),
    "checkout": ("pins", "checkout_command"),
    "run": ("engines", "run_command"),
    "judge": ("judge", "judge_command"),
    "ready": ("pins", "ready_command"),
}


@dataclass(frozen=True)
class Options:
    mode: str
    results: Path
    worktrees: Path
    temporary: Path
    output: str | None
    summary: str | None


def parse(usage, argv):
    parser = argparse.ArgumentParser(description=usage, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=sorted(COMMANDS))
    parser.add_argument(
        "directory",
        type=Path,
        nargs="?",
        default=Path("."),
        help="the repository under test; the current directory when omitted",
    )
    parser.add_argument(
        "--mode",
        choices=("ci", "local"),
        default="ci" if os.environ.get("CI") == "true" else "local",
        help="where pins resolve: ci, or local (siblings' working trees); ci when the CI variable is true",
    )
    parser.add_argument(
        "--results",
        default=None,
        help="where the record and the EARL reports go; by default a directory "
        "named for the repository under the system temporary directory",
    )
    parser.add_argument("--output", default=None, help="spec-pin only: a file to append repository=, kind= and ref= to")
    parser.add_argument(
        "--summary", default=None, help="judge only: a Markdown file to append a table of every entry to"
    )
    return parser.parse_args(argv)


def main(usage, argv=None):
    args = parse(usage, argv)
    directory = args.directory.resolve()
    if not directory.is_dir():
        report(False, f"{directory} is not a directory")
        return Status.FAIL.exit_code

    temporary = Path(tempfile.gettempdir())
    options = Options(
        mode=args.mode,
        results=Path(args.results).resolve() if args.results else temporary / "cascade-compatibility" / directory.name,
        worktrees=temporary / "cascade-compatibility" / "worktrees",
        temporary=temporary,
        output=args.output,
        summary=args.summary,
    )
    print(f"Repository: {directory}")
    print(f"Spec:       {SPEC_ROOT}")
    print()
    module, function = COMMANDS[args.command]
    try:
        status = getattr(importlib.import_module(f"compatibility_tool.{module}"), function)(directory, options)
    except Stop as stop:
        report(False, str(stop))
        status = Status.FAIL
    print()
    print(f"{args.command}: {status.word}")
    print(status.verdict)
    return status.exit_code
