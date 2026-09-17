from dataclasses import dataclass, field
from pathlib import Path

from rdflib import Graph, URIRef

from compatibility_tool.console import Status, Stop, first_line, note, report
from compatibility_tool.document import CRATE, crate_root, referenced_id
from compatibility_tool.record import Record

EARL = "http://www.w3.org/ns/earl#"
MF = "http://www.w3.org/2001/sw/DataAccess/tests/test-manifest#"
OUTCOMES = {"passed", "failed", "cantTell", "inapplicable", "untested"}
NOT_HOLDING = {"failed", "inapplicable"}


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
    adapter = adapter.resolve()
    _, root = crate_root(adapter)
    named = referenced_id(root, "bridge:testManifest")
    if not named:
        raise Stop(f"{adapter / CRATE} names no bridge:testManifest")
    path = adapter / named
    graph = Graph().parse(path, format="turtle", publicID=path.as_uri())
    listed = graph.value(URIRef(path.as_uri()), URIRef(MF + "entries"))
    prefix = adapter.as_uri() + "/"
    return [str(entry).removeprefix(prefix) for entry in graph.items(listed)] if listed else []


def judge_report(path, adapter):
    if path is None:
        return Verdict(unjudged="it was not run")
    if not path.is_file():
        return Verdict(unjudged="it wrote no report")
    try:
        graph = Graph().parse(path, format="turtle")
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


def linked(text, url):
    return f"[{text}]({url})" if url.startswith("https://") else text


def table_row(entry, verdict):
    repository = entry.pin.repository.removesuffix(".git")
    commit = linked(f"`{entry.commit[:7]}`", f"{repository}/commit/{entry.commit}")
    result = f"{'✅ holds' if verdict.holds else '❌ does not hold'}: {verdict.describe()}".replace("|", "\\|")
    return f"| {linked(entry.pin.name, repository)} | {entry.pin.kind} {entry.pin.value} | {commit} | {result} |"


def append_summary(path, directory, rows):
    lines = [f"### Compatibility of {directory.name}", ""]
    if rows:
        lines += ["| must pass with | pin | commit | result |", "|---|---|---|---|", *rows]
    else:
        lines.append(f"{directory.name} lists no counterpart: nothing to check.")
    with Path(path).open("a", encoding="utf-8") as summary:
        summary.write("\n".join(lines) + "\n\n")


def judge_command(directory, options):
    counterparts = Record.load_checked_out(options.results).counterparts
    print("Each entry, judged by its EARL report")
    if not counterparts:
        if options.summary:
            append_summary(options.summary, directory, [])
        report(True, "no entry: nothing to check")
        return Status.NOTHING_TO_CHECK
    held = 0
    rows = []
    for entry in counterparts:
        verdict = judge_report(entry.report, entry.adapter)
        held += verdict.holds
        rows.append(table_row(entry, verdict))
        flag = ", with uncommitted edits" if entry.uncommitted_edits else ""
        report(
            verdict.holds,
            f"{entry.pin.repository} at {entry.commit} ({entry.pin.kind} {entry.pin.value}{flag}): "
            f"{'holds' if verdict.holds else 'does not hold'}; {verdict.describe()}",
        )
    if options.summary:
        append_summary(options.summary, directory, rows)
    if any(entry.uncommitted_edits for entry in counterparts):
        note("a result produced from uncommitted edits is feedback, never evidence")
    count = len(counterparts)
    print(f"  {count} entr{'y' if count == 1 else 'ies'}: {held} hold, {count - held} do not")
    return Status.OK if held == count else Status.FAIL
