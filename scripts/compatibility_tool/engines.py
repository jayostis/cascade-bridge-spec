import shutil
import subprocess
from pathlib import Path

from compatibility_tool.console import report
from compatibility_tool.document import is_adapter, read_file


def executable(argv, cwd):
    first = argv[0]
    if "/" in first or "\\" in first:
        candidate = Path(cwd, first)
        return [str(candidate) if candidate.exists() else first, *argv[1:]]
    return [shutil.which(first) or first, *argv[1:]]  # so Windows finds npm.cmd


def execute(argv, cwd):
    try:
        run = subprocess.run(executable(argv, cwd), cwd=cwd, capture_output=True, encoding="utf-8", errors="replace")
    except OSError as error:
        report(False, f"{argv[0]} could not be started in {cwd}: {error}")
        return None
    for line in (run.stdout + run.stderr).splitlines():
        print(f"        | {line}")
    return run.returncode


def vectors(engine):
    document = read_file(engine) or {}
    setup, command = document.get("setup"), document.get("command")
    if isinstance(setup, list) and setup and isinstance(command, list) and command:
        return setup, command
    return None


def run(directory, record, options):
    reports = options.results / "earl"
    shutil.rmtree(reports, ignore_errors=True)
    reports.mkdir(parents=True)
    print("Each engine on each adapter")
    adapter_side = is_adapter(directory)
    set_up = {}
    for entry in record.counterparts:
        engine, adapter = (entry.path, directory) if adapter_side else (directory, entry.path)
        entry.adapter = adapter
        found = vectors(engine)
        if found is None:
            report(False, f"{engine} states no setup and command, so {entry.name} was not run")
            continue
        setup, command = found
        if engine not in set_up:
            print(f"  setup {' '.join(setup)}   (in {engine})")
            set_up[engine] = execute(setup, engine) == 0
            if not set_up[engine]:
                report(False, f"the setup failed in {engine}")
        if not set_up[engine]:
            report(False, f"{entry.name} was not run: its engine's setup failed")
            continue
        earl = reports / f"{entry.name}.ttl"
        argv = [*command, "test", str(adapter), "--earl", str(earl)]
        if record.vocabularies is not None:
            argv += ["--vocabularies", str(record.vocabularies)]
        print(f"  run   {' '.join(argv)}   (in {engine})")
        status = execute(argv, engine)
        if status is None:
            continue
        entry.report = earl
        wrote = f"its report is {earl}" if earl.is_file() else "it wrote no report"
        report(True, f"{entry.name} ran, exit status {status}, which nothing relies on; {wrote}")
