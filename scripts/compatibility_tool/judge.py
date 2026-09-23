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
BRIDGE = "https://ns.cascadeprotocol.org/bridge/v1-draft#"
OUTCOMES = {"passed", "failed", "cantTell", "inapplicable", "untested"}
OUTCOMES_OF_A_REPORT_THAT_HOLDS = {"passed", "cantTell", "untested"}
REPORT_DOES_NOT_HOLD = SPEC_ROOT / "engine" / "report-does-not-hold.rq"


def graph_of(path, **arguments):
    return packages.installed("rdflib").Graph().parse(path, **arguments)


def outcome_name(outcome):
    if isinstance(outcome, packages.installed("rdflib").URIRef) and str(outcome).startswith(EARL):
        return str(outcome).removeprefix(EARL)
    return outcome.n3()


def is_entry(test, entry):
    return test == entry or test.endswith("/" + entry)


@dataclass
class Verdict:
    unjudged: str | None = None
    holds: bool = False
    tally: dict[str, int] = field(default_factory=dict)
    unreadable_manifest: str | None = None
    expected: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    input_only_not_cant_tell: dict[str, str] = field(default_factory=dict)

    @property
    def unknown(self):
        return sorted(name for name in self.tally if name not in OUTCOMES)

    def describe(self):
        if self.unjudged is not None:
            return self.unjudged
        said = ", ".join(f"{count} {name}" for name, count in sorted(self.tally.items()))
        if self.unknown:
            said += f"; {', '.join(self.unknown)} is not one of EARL's five outcomes"
        if self.unreadable_manifest is not None:
            return f"{said}; the adapter's test manifest could not be read: {self.unreadable_manifest}"
        causes = []
        if self.missing:
            names = ", ".join(entry.rsplit("#", 1)[-1] for entry in self.missing)
            causes.append(f"{len(self.missing)} of the manifest's {len(self.expected)} tests have no outcome: {names}")
        else:
            said += f", covering all {len(self.expected)} of the manifest's tests"
        if any(name in OUTCOMES - OUTCOMES_OF_A_REPORT_THAT_HOLDS for name in self.tally):
            causes.append("a report that holds gives only passed, cantTell or untested")
        causes += [
            f"input-only {entry.rsplit('#', 1)[-1]} is reported {outcome}, not cantTell"
            for entry, outcome in sorted(self.input_only_not_cant_tell.items())
        ]
        if not self.holds and not causes and not self.unknown:
            causes.append(f"{REPORT_DOES_NOT_HOLD.relative_to(SPEC_ROOT).as_posix()} finds it does not hold")
        return "; ".join([said, *causes])


def read_test_manifest(adapter):
    _, root = crate_root(adapter)
    named = referenced_id(root, "bridge:testManifest")
    if not named:
        raise Stop(f"{adapter / CRATE} names no bridge:testManifest")
    path = adapter / named
    return path, graph_of(path, format="turtle", publicID=path.as_uri())


def manifest_entries_relative_to_adapter(adapter, path, graph):
    URIRef = packages.installed("rdflib").URIRef
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
        name = outcome_name(outcome)
        tally[name] = tally.get(name, 0) + 1
    if not tally:
        return Verdict(unjudged="its report records no outcome")

    adapter = adapter.resolve()
    try:
        manifest_path, manifest = read_test_manifest(adapter)
        expected = manifest_entries_relative_to_adapter(adapter, manifest_path, manifest)
    except Exception as error:
        return Verdict(tally=tally, unreadable_manifest=first_line(str(error)))
    reported = []
    for assertion, result in graph.subject_objects(URIRef(EARL + "result")):
        outcome = graph.value(result, URIRef(EARL + "outcome"))
        if outcome is not None:
            reported += [(str(test), outcome_name(outcome)) for test in graph.objects(assertion, URIRef(EARL + "test"))]
    missing = [entry for entry in expected if not any(is_entry(test, entry) for test, _ in reported)]
    input_only = {
        str(entry).removeprefix(adapter.as_uri() + "/")
        for entry in manifest.subjects(packages.installed("rdflib").RDF.type, URIRef(BRIDGE + "InputOnlyTest"))
    }
    input_only_not_cant_tell = {
        entry: outcome
        for entry in expected
        if entry in input_only
        for test, outcome in reported
        if is_entry(test, entry) and outcome != "cantTell"
    }
    does_not_hold = (graph + manifest).query(REPORT_DOES_NOT_HOLD.read_text(encoding="utf-8")).askAnswer
    return Verdict(
        tally=tally,
        expected=expected,
        missing=missing,
        input_only_not_cant_tell=input_only_not_cant_tell,
        holds=not does_not_hold,
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
