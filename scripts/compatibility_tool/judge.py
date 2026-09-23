import os
from dataclasses import dataclass, field
from pathlib import Path

from compatibility_tool import packages
from compatibility_tool.bootstrap import SPEC_ROOT
from compatibility_tool.console import Status, Stop, first_line, note, report
from compatibility_tool.document import CRATE, crate_root, referenced_id
from compatibility_tool.record import Role

EARL = "http://www.w3.org/ns/earl#"
MF = "http://www.w3.org/2001/sw/DataAccess/tests/test-manifest#"
FAULTS_OF_A_REPORT = SPEC_ROOT / "engine" / "faults-of-a-report.rq"


def graph_of(path, **arguments):
    return packages.installed("rdflib").Graph().parse(path, **arguments)


def outcome_name(outcome):
    if isinstance(outcome, packages.installed("rdflib").URIRef) and str(outcome).startswith(EARL):
        return str(outcome).removeprefix(EARL)
    return outcome.n3()


@dataclass
class Verdict:
    unjudged: str | None = None
    tally: dict[str, int] = field(default_factory=dict)
    unreadable_manifest: str | None = None
    tests: int = 0
    faults: list[str] = field(default_factory=list)

    @property
    def holds(self):
        return self.unjudged is None and self.unreadable_manifest is None and not self.faults

    def describe(self):
        if self.unjudged is not None:
            return self.unjudged
        said = ", ".join(f"{count} {name}" for name, count in sorted(self.tally.items()))
        if self.unreadable_manifest is not None:
            return "; ".join(
                filter(None, [said, f"the adapter's test manifest could not be read: {self.unreadable_manifest}"])
            )
        if not self.faults:
            said += f", covering all {self.tests} of the manifest's tests"
        return "; ".join(filter(None, [said, *self.faults]))


def read_test_manifest(adapter):
    _, root = crate_root(adapter)
    named = referenced_id(root, "bridge:testManifest")
    if not named:
        raise Stop(f"{adapter / CRATE} names no bridge:testManifest")
    path = adapter / named
    return path, graph_of(path, format="turtle", publicID=path.as_uri())


def count_of_tests(path, graph):
    URIRef = packages.installed("rdflib").URIRef
    listed = graph.value(URIRef(path.as_uri()), URIRef(MF + "entries"))
    return len(list(graph.items(listed))) if listed else 0


def judge_report(path, adapter):
    if path is None:
        return Verdict(unjudged="it was not run")
    if not path.is_file():
        return Verdict(unjudged="it wrote no report")
    try:
        graph = graph_of(path, format="turtle")
    except Stop:
        raise
    except Exception as error:
        return Verdict(unjudged=f"its report does not parse as Turtle: {first_line(str(error))}")
    tally = {}
    for outcome in graph.objects(None, packages.installed("rdflib").URIRef(EARL + "outcome")):
        name = outcome_name(outcome)
        tally[name] = tally.get(name, 0) + 1

    adapter = adapter.resolve()
    try:
        manifest_path, manifest = read_test_manifest(adapter)
    except Exception as error:
        return Verdict(tally=tally, unreadable_manifest=first_line(str(error)))
    rows = (graph + manifest).query(FAULTS_OF_A_REPORT.read_text(encoding="utf-8"))
    return Verdict(
        tally=tally,
        tests=count_of_tests(manifest_path, manifest),
        faults=[str(row.fault) for row in rows],
    )


def judge(record, options):
    print("Each counterpart, judged by its EARL report")
    counterparts = record.counterparts
    if not counterparts:
        report(True, f"{record.directory} lists no counterpart: nothing to check")
        return Status.NOTHING_TO_CHECK
    held = 0
    for entry in counterparts:
        verdict = judge_report(entry.report, entry.adapter)
        entry.holds = verdict.holds
        entry.result = verdict.describe()
        held += verdict.holds
        report(
            verdict.holds,
            f"{entry.describe()}: {'holds' if verdict.holds else 'does not hold'}; {verdict.describe()}",
        )
    if any(entry.uncommitted_edits for entry in counterparts):
        note("a result produced from uncommitted edits is feedback, never evidence")
    count = len(counterparts)
    print(f"  {count} counterpart{'' if count == 1 else 's'}: {held} hold, {count - held} do not")
    return Status.OK if held == count else Status.FAIL


def linked(text, url):
    return f"[{text}]({url})" if url.startswith("https://") else text


def cell(text):
    return text.replace("|", "\\|")


def result_cell(entry):
    if entry.role is Role.NOT_USED:
        return "not used"
    if entry.holds is None:
        return "—"
    return cell(f"{'✅ holds' if entry.holds else '❌ does not hold'}: {entry.result}")


def version_cell(entry):
    """The vocabulary is at the adapter's pin unless a Depends-On: line named a pull request of it instead."""
    if entry.role is Role.VOCABULARY and entry.from_named_pull_requests:
        return f"Depends-On: {entry.how}"
    return entry.how


def table(record):
    lines = [
        f"### Compatibility of {record.directory.name}",
        "",
        "| repository | engine host | version | commit | result |",
        "|---|---|---|---|---|",
    ]
    for entry in record.used:
        repository = entry.repository.removesuffix(".git")
        commit = entry.commit or "—"
        shown = linked(f"`{commit[:7]}`", f"{repository}/commit/{commit}") if entry.commit else "—"
        edits = ", with uncommitted edits" if entry.uncommitted_edits else ""
        host = cell(entry.host or "—")
        lines.append(
            f"| [{entry.name}]({repository}) | {host} | {version_cell(entry)}{edits} | {shown} | {result_cell(entry)} |"
        )
    if any(entry.from_named_pull_requests for entry in record.used):
        lines += [
            "",
            "This pass is as fresh as this run: rerun it once the pull requests above have merged, and before merging.",
        ]
    return "\n".join(lines) + "\n"


def write_table(record, options):
    if options.mode != "ci":
        return
    written = table(record)
    (options.results / "table.md").write_text(written, encoding="utf-8")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with Path(summary).open("a", encoding="utf-8") as handle:
            handle.write(written + "\n")
