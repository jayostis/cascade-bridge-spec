"""A runtime: the repositories its cascade-runtime.json pins, each picked as a counterpart is, and its conformance
command run on each host with a folder for each."""

import re
import shutil

from compatibility_tool import engines, picking, placing
from compatibility_tool.console import report
from compatibility_tool.document import RUNTIME, hosts, pinned_repositories, read_file, read_json
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


def folders(directory, record):
    """--folder <repository>=<folder> for each pin, keyed as cascade-runtime.json writes the repository."""
    paths = {entry.repository: entry.path for entry in record.used if entry.role in (Role.VOCABULARY, Role.ADAPTER)}
    return [argument for written, url, _, _ in pins(directory) for argument in ("--folder", f"{written}={paths[url]}")]


def run(directory, record, options, set_up):
    """Each host of the runtime under test, its conformance command run: a row of its own per host."""
    print("The runtime's conformance command on each host")
    reports = options.results / "earl"
    shutil.rmtree(reports, ignore_errors=True)
    reports.mkdir(parents=True)
    handed = folders(directory, record)
    under_test = next(entry for entry in record.used if entry.role is Role.UNDER_TEST)
    for index, host in enumerate(hosts(read_file(directory)), 1):
        row = Row(
            name=under_test.name,
            repository=under_test.repository,
            commit=under_test.commit,
            how="its conformance command",
            role=Role.CONFORMANCE,
            uncommitted_edits=under_test.uncommitted_edits,
            path=directory,
            pull_request=under_test.pull_request,
            host=host["name"],
        )
        record.used.append(row)
        command = engines.prepared(directory, row.host, host, set_up, "the conformance command")
        if command is None:
            continue
        earl = reports / f"conformance-on-host-{index}.ttl"
        argv = [*command, "--report", str(earl), *handed]
        print(f"  run   {' '.join(argv)}   (in {directory}, on {row.host})")
        status = engines.execute(argv, directory)
        if status is None:
            continue
        row.report = earl
        wrote = f"its report is {earl}" if earl.is_file() else "it wrote no report"
        report(
            True, f"the conformance command ran on {row.host}, exit status {status}, which nothing relies on; {wrote}"
        )
