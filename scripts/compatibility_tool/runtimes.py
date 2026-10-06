"""A runtime: the repositories its cascade-runtime.json names, each picked as a counterpart is, and its conformance
command run on each host with a folder for each. A vocabulary under test is handed in for the one it names."""

import shutil
from dataclasses import replace

from compatibility_tool import engines, picking, placing
from compatibility_tool.console import Stop, report
from compatibility_tool.document import (
    FILE,
    RUNTIME,
    hosts,
    is_runtime,
    name_clashes,
    named_repositories,
    read_file,
)
from compatibility_tool.github import repository_name, repository_path, url_on_this_server
from compatibility_tool.record import Role


def counterparts(directory):
    """Each repository as cascade-runtime.json writes it, the URL the run fetches it from, and the role it plays."""
    return [
        (
            written,
            url_on_this_server(repository_path(written)),
            Role.VOCABULARY if where == "vocabulary" else Role.ADAPTER,
        )
        for where, written in named_repositories(directory)
    ]


def place(directory, url, role, options, event, reached):
    if options.mode == "local":
        return placing.locally(directory, url, role)
    return placing.in_ci(url, reached, event, directory.parent / repository_name(url), role)


def placed(directory, options, event, api):
    listed = counterparts(directory)
    reached = (
        picking.follow(api, event, [url for _, url, _ in listed], options.spec_repository)
        if options.mode == "ci"
        else []
    )
    rows = [place(directory, url, role, options, event, reached) for _, url, role in listed]
    return [*rows, *placing.not_used(reached)]


def named_by(directory, listed, options, event, api):
    """Each runtime a vocabulary under test names, and each adapter one names, each picked as a counterpart is."""
    reached = picking.follow(api, event, listed, options.spec_repository) if options.mode == "ci" else []
    rows = []
    for url in listed:
        row = place(directory, url, Role.CONFORMANCE, options, event, reached)
        if not is_runtime(row.path):
            raise Stop(f"{url} holds no {RUNTIME}, and a vocabulary's {FILE} names runtimes alone")
        rows.append(row)
    adapters = list(
        dict.fromkeys(url for row in rows for _, url, role in counterparts(row.path) if role is Role.ADAPTER)
    )
    clashes = name_clashes(directory, [*listed, *adapters], f"{FILE} and the {RUNTIME} of each runtime it names")
    if clashes:
        raise Stop("; ".join(clashes))
    if options.mode == "ci":
        reached = picking.follow(api, event, [*listed, *adapters], options.spec_repository)
    rows += [place(directory, url, Role.ADAPTER, options, event, reached) for url in adapters]
    return [*rows, *placing.not_used(reached)]


def folders(runtime, paths):
    """--folder <repository>=<folder> for each repository, keyed as cascade-runtime.json writes it."""
    return [
        argument for written, url, _ in counterparts(runtime) for argument in ("--folder", f"{written}={paths[url]}")
    ]


def run(directory, record, options, set_up):
    """Each host of each runtime the run checks, its conformance command run: a row of its own per host."""
    print("The runtime's conformance command on each host")
    reports = options.results / "earl"
    shutil.rmtree(reports, ignore_errors=True)
    reports.mkdir(parents=True)
    paths = {entry.repository: entry.path for entry in record.used if entry.role in (Role.VOCABULARY, Role.ADAPTER)}
    if is_runtime(directory):
        under_test = next(entry for entry in record.used if entry.role is Role.UNDER_TEST)
        record.used.append(replace(under_test, how="its conformance command", role=Role.CONFORMANCE, path=directory))
    index = 0
    for runtime in record.conformance:
        vocabulary = (
            {}
            if is_runtime(directory)
            else {url: directory for _, url, role in counterparts(runtime.path) if role is Role.VOCABULARY}
        )
        handed = folders(runtime.path, {**paths, **vocabulary})
        listed = hosts(read_file(runtime.path))
        problem = engines.unrunnable(listed)
        if problem:
            report(False, f"{runtime.path} {problem}, so its conformance command was not run")
            continue
        for row, host in zip(record.on_each_host(runtime, [host["name"] for host in listed]), listed, strict=True):
            index += 1
            run_on_host(row, host, handed, set_up, reports / f"conformance-on-host-{index}.ttl")


def run_on_host(row, host, handed, set_up, earl):
    command = engines.prepared(row.path, row.host, host, set_up, "the conformance command")
    if command is None:
        return
    argv = [*command, "--report", str(earl), *handed]
    print(f"  run   {' '.join(argv)}   (in {row.path}, on {row.host})")
    status = engines.execute(argv, row.path)
    if status is None:
        return
    row.report = earl
    wrote = f"its report is {earl}" if earl.is_file() else "it wrote no report"
    report(True, f"the conformance command ran on {row.host}, exit status {status}, which nothing relies on; {wrote}")
