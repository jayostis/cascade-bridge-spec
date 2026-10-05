"""A runtime: the repositories its cascade-runtime.json pins, each picked as a counterpart is, and its conformance
command run on each host with a folder for each. A vocabulary under test is handed in for the one it pins."""

import re
import shutil
from dataclasses import replace

from compatibility_tool import engines, picking, placing
from compatibility_tool.console import Stop, report
from compatibility_tool.document import FILE, RUNTIME, hosts, is_runtime, pinned_repositories, read_file, read_json
from compatibility_tool.github import repository_name, repository_path, url_on_this_server
from compatibility_tool.record import Role, Row

LOCKFILE = "package-lock.json"
RELEASE = re.compile(r"^(?P<repository>https://[^/]+/[^/]+/[^/]+)/releases/download/(?P<tag>[^/]+)/[^/]+$")


def pins(directory):
    """Each pin as cascade-runtime.json writes the repository, and the URL the run fetches it from."""
    return [
        (
            written,
            url_on_this_server(repository_path(written)),
            commit,
            Role.VOCABULARY if where == "vocabulary" else Role.ADAPTER,
        )
        for where, written, commit in pinned_repositories(directory)
    ]


def released_packages(directory):
    """Each package the lockfile resolves from a repository's release: what a runtime pins a Bridge by."""
    lockfile = directory / LOCKFILE
    listed = (read_json(lockfile).get("packages") or {}) if lockfile.is_file() else {}
    releases = {}
    for entry in listed.values():
        match = RELEASE.match(entry.get("resolved") or "") if isinstance(entry, dict) else None
        if match:
            releases[match["repository"], match["tag"]] = None
    return [
        Row(
            name=repository_name(url),
            repository=url,
            commit=None,
            how=f"the release {tag}, as {LOCKFILE} pins it",
            role=Role.PACKAGE,
            release=tag,
        )
        for url, tag in releases
    ]


def placed(directory, options, event, api):
    pinned = pins(directory)
    urls = [url for _, url, _, _ in pinned]
    reached = picking.follow(api, event, urls, options.spec_repository) if options.mode == "ci" else []
    how = f"the runtime's {RUNTIME}"
    rows = [
        placing.pinned(directory, url, commit, role, how, options, event, reached) for _, url, commit, role in pinned
    ]
    return [*rows, *placing.not_used(reached), *released_packages(directory)]


def named_by(directory, listed, options, event, api):
    """Each runtime a vocabulary under test names, picked as a counterpart is, and each adapter it pins."""
    reached = picking.follow(api, event, listed, options.spec_repository) if options.mode == "ci" else []
    rows = []
    for url in listed:
        if options.mode == "local":
            row = placing.locally(directory, url, Role.CONFORMANCE)
        else:
            row = placing.in_ci(url, reached, event, directory.parent / repository_name(url), Role.CONFORMANCE)
        if not is_runtime(row.path):
            raise Stop(f"{url} holds no {RUNTIME}, and a vocabulary's {FILE} names runtimes alone")
        rows.append(row)
    adapters = {}
    for row in rows:
        for _, url, commit, role in pins(row.path):
            if role is Role.ADAPTER and adapters.setdefault(url, (commit, row.name))[0] != commit:
                raise Stop(f"{adapters[url][1]} and {row.name} pin {url} at two commits, and one checkout serves both")
    if options.mode == "ci":
        reached = picking.follow(api, event, [*listed, *adapters], options.spec_repository)
    rows += [
        placing.pinned(directory, url, commit, Role.ADAPTER, f"{name}'s {RUNTIME}", options, event, reached)
        for url, (commit, name) in adapters.items()
    ]
    return [*rows, *placing.not_used(reached)]


def folders(runtime, paths):
    """--folder <repository>=<folder> for each pin, keyed as cascade-runtime.json writes the repository."""
    return [argument for written, url, _, _ in pins(runtime) for argument in ("--folder", f"{written}={paths[url]}")]


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
            else {url: directory for _, url, _, role in pins(runtime.path) if role is Role.VOCABULARY}
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
