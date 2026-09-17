import os
from dataclasses import dataclass, field
from pathlib import Path

from compatibility_tool import packages
from compatibility_tool.console import Status, Stop, first_line, note, report, warn
from compatibility_tool.document import CRATE, crate_root, referenced_id
from compatibility_tool.record import Role

EARL = "http://www.w3.org/ns/earl#"
MF = "http://www.w3.org/2001/sw/DataAccess/tests/test-manifest#"
OUTCOMES = {"passed", "failed", "cantTell", "inapplicable", "untested"}
NOT_HOLDING = {"failed", "inapplicable"}


def graph_of(path, **arguments):
    return packages.installed("rdflib").Graph().parse(path, **arguments)


@dataclass
class Verdict:
    unjudged: str | None = None
    tally: dict[str, int] = field(default_factory=dict)
    unreadable_manifest: str | None = None
    expected: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)

    @property
    def unknown(self):
        return sorted(name for name in self.tally if name not in OUTCOMES)

    @property
    def holds(self):
        return (
            self.unjudged is None
            and self.unreadable_manifest is None
            and not self.unknown
            and not self.missing
            and not NOT_HOLDING & self.tally.keys()
        )

    def describe(self):
        if self.unjudged is not None:
            return self.unjudged
        said = ", ".join(f"{count} {name}" for name, count in sorted(self.tally.items()))
        if self.unknown:
            said += f"; {', '.join(self.unknown)} is not one of EARL's five outcomes"
        if self.unreadable_manifest is not None:
            return f"{said}; the adapter's test manifest could not be read: {self.unreadable_manifest}"
        if self.missing:
            names = ", ".join(entry.rsplit("#", 1)[-1] for entry in self.missing)
            return f"{said}; {len(self.missing)} of the manifest's {len(self.expected)} tests have no outcome: {names}"
        return f"{said}, covering all {len(self.expected)} of the manifest's tests"


def manifest_entries_relative_to_adapter(adapter):
    URIRef = packages.installed("rdflib").URIRef
    adapter = adapter.resolve()
    _, root = crate_root(adapter)
    named = referenced_id(root, "bridge:testManifest")
    if not named:
        raise Stop(f"{adapter / CRATE} names no bridge:testManifest")
    path = adapter / named
    graph = graph_of(path, format="turtle", publicID=path.as_uri())
    listed = graph.value(URIRef(path.as_uri()), URIRef(MF + "entries"))
    prefix = adapter.as_uri() + "/"
    return [str(entry).removeprefix(prefix) for entry in graph.items(listed)] if listed else []


def judge_report(path, adapter):
    URIRef = packages.installed("rdflib").URIRef
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
    for outcome in graph.objects(None, URIRef(EARL + "outcome")):
        name = str(outcome).removeprefix(EARL)
        tally[name] = tally.get(name, 0) + 1
    if not tally:
        return Verdict(unjudged="its report records no outcome")

    try:
        expected = manifest_entries_relative_to_adapter(adapter)
    except Exception as error:
        return Verdict(tally=tally, unreadable_manifest=first_line(str(error)))
    tested = set()
    for assertion, result in graph.subject_objects(URIRef(EARL + "result")):
        if graph.value(result, URIRef(EARL + "outcome")) is not None:
            tested.update(str(test) for test in graph.objects(assertion, URIRef(EARL + "test")))
    missing = [entry for entry in expected if not any(test == entry or test.endswith("/" + entry) for test in tested)]
    return Verdict(tally=tally, expected=expected, missing=missing)


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


def result_cell(entry):
    if entry.role is Role.NOT_USED:
        return "not used"
    if entry.holds is None:
        return "—"
    return f"{'✅ holds' if entry.holds else '❌ does not hold'}: {entry.result}".replace("|", "\\|")


def table(record):
    lines = [
        f"### Compatibility of {record.directory.name}",
        "",
        "| repository | version | commit | result |",
        "|---|---|---|---|",
    ]
    for entry in record.used:
        repository = entry.repository.removesuffix(".git")
        commit = entry.commit or "—"
        shown = linked(f"`{commit[:7]}`", f"{repository}/commit/{commit}") if entry.commit else "—"
        edits = ", with uncommitted edits" if entry.uncommitted_edits else ""
        lines.append(f"| [{entry.name}]({repository}) | {entry.how}{edits} | {shown} | {result_cell(entry)} |")
    if any(entry.from_named_pull_requests for entry in record.used):
        lines += [
            "",
            "This pass is as fresh as this run: rerun it once the pull requests above have merged, and before merging.",
        ]
    return "\n".join(lines) + "\n"


def write_table(record, options, api, event):
    if options.mode != "ci":
        return
    written = table(record)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with Path(summary).open("a", encoding="utf-8") as handle:
            handle.write(written + "\n")
    if not event.number:
        return
    try:
        api.comment(event.repository, event.number, written)
    except Exception as error:
        warn(f"no comment was posted on {event.repository}#{event.number}: {first_line(str(error))}")
