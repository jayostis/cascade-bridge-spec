import shutil
import subprocess
from pathlib import Path

from compatibility_tool.console import report
from compatibility_tool.document import hosts, is_adapter, read_file


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


def vectors(host):
    setup, command = host.get("setup"), host.get("command")
    if isinstance(setup, list) and setup and isinstance(command, list) and command:
        return setup, command
    return None


def unrunnable(listed):
    names = [host.get("name") if isinstance(host, dict) else None for host in listed]
    if not names:
        return "names no host"
    if not all(isinstance(name, str) for name in names):
        return "lists a host with no name"
    repeated = sorted({name for name in names if names.count(name) > 1})
    return f"names more than one host {', '.join(repeated)}" if repeated else None


def run(directory, record, options, set_up):
    reports = options.results / "earl"
    shutil.rmtree(reports, ignore_errors=True)
    reports.mkdir(parents=True)
    print("Each adapter on each host of each engine")
    adapter_side = is_adapter(directory)
    for pairing in record.counterparts:
        engine, adapter = (pairing.path, directory) if adapter_side else (directory, pairing.path)
        pairing.adapter = adapter
        listed = hosts(read_file(engine))
        problem = unrunnable(listed)
        if problem:
            report(False, f"{engine} {problem}, so {pairing.name} was not run")
            continue
        found = {host["name"]: host for host in listed}
        for index, entry in enumerate(record.on_each_host(pairing, found), 1):
            earl = reports / f"{entry.name}-on-host-{index}.ttl"
            run_on_host(entry, engine, found[entry.host], set_up, earl, record)


def prepared(engine, name, host, set_up, what):
    """The host's command once its setup has run in the engine, which happens once a run; None where it cannot run."""
    found = vectors(host)
    if found is None:
        report(False, f"{engine} states no setup and command for {name}, so {what} was not run on it")
        return None
    setup, command = found
    if (engine, name) not in set_up:
        print(f"  setup {' '.join(setup)}   (in {engine}, for {name})")
        set_up[engine, name] = execute(setup, engine) == 0
        if not set_up[engine, name]:
            report(False, f"the setup for {name} failed in {engine}")
    if not set_up[engine, name]:
        report(False, f"{what} was not run on {name}: its setup failed")
        return None
    return command


def run_on_host(entry, engine, host, set_up, earl, record):
    command = prepared(engine, entry.host, host, set_up, entry.name)
    if command is None:
        return
    argv = [*command, "test", str(entry.adapter), "--earl", str(earl)]
    if entry.vocabularies is not None:
        argv += ["--vocabularies", str(entry.vocabularies)]
    print(f"  run   {' '.join(argv)}   (in {engine}, on {entry.host})")
    status = execute(argv, engine)
    if status is None:
        return
    entry.report = earl
    wrote = f"its report is {earl}" if earl.is_file() else "it wrote no report"
    report(True, f"{entry.name} ran on {entry.host}, exit status {status}, which nothing relies on; {wrote}")
