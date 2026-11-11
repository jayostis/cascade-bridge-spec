"""The report of each case a run's engine hosts ran: report.ctrf.json for a tool, report.md for a person."""

import html
import json
import os
import re
import time
from datetime import datetime, timezone

from compatibility_tool import packages
from compatibility_tool.bootstrap import SPEC_ROOT
from compatibility_tool.console import first_line
from compatibility_tool.document import is_adapter
from compatibility_tool.github import url_on_this_server
from compatibility_tool.judge import MF, graph_of, linked, read_test_manifest
from compatibility_tool.record import Role

CTRF = "report.ctrf.json"
MARKDOWN = "report.md"
BRIDGE = "https://ns.cascadeprotocol.org/bridge/v1-draft#"
TOOL = "cascade-bridge-spec compatibility"
STATUS_OF = {"passed": "passed", "cantTell": "other", "untested": "skipped"}
MARKS = {"passed": "✅", "failed": "❌", "skipped": "➖", "other": "❔"}
MANIFEST_CASE = "the adapter's test manifest"
FRAGMENT = re.compile(r"<#([^>\s]+)>")


def remove(results):
    """A results directory is reused, and the start action uploads whatever is in it."""
    for name in (CTRF, MARKDOWN):
        (results / name).unlink(missing_ok=True)


def one_line(text):
    return " ".join(str(text).split())


class Manifest:
    """An adapter's test manifest read once for a run: its entries, and where each of its outcomes is found."""

    def __init__(self, adapter):
        self.adapter = adapter.resolve()
        self.unreadable = None
        self.entries = []
        self.label = self.adapter.name
        self.slashes = set()
        self.base = None
        self.path = None
        self.lines = {}
        try:
            self.path, graph = read_test_manifest(self.adapter)
        except Exception as error:
            self.unreadable = first_line(str(error))
            return
        rdflib = packages.installed("rdflib")
        manifest = rdflib.URIRef(self.path.as_uri())
        listed = graph.value(manifest, rdflib.URIRef(MF + "entries"))
        label = graph.value(manifest, rdflib.RDFS.label)
        self.label = str(label) if label is not None else self.label
        base = graph.value(manifest, rdflib.URIRef(BRIDGE + "adapter"))
        self.base = str(base) if base is not None else None
        for entry in graph.items(listed) if listed else []:
            name = graph.value(entry, rdflib.URIRef(MF + "name"))
            comment = graph.value(entry, rdflib.RDFS.comment)
            self.entries.append(
                {
                    "iri": str(entry),
                    "name": str(name) if name is not None else str(entry).rsplit("#", 1)[-1],
                    "comment": None if comment is None else str(comment),
                    "types": [str(kind) for kind in graph.objects(entry, rdflib.RDF.type)],
                }
            )
            if self.base:
                self.slashes.add(self.within(str(entry)).count("/"))
        for number, text in enumerate(self.path.read_text(encoding="utf-8").splitlines(), 1):
            found = FRAGMENT.match(text)
            if found:
                self.lines.setdefault(found.group(1), number)

    def within(self, iri):
        """What follows the adapter's address in an IRI, as the faults query reads it."""
        return iri.split(self.base, 1)[1] if self.base and self.base in iri else ""

    def candidates(self, iri):
        """The entries an IRI may name: the same IRI, and where another base holds the report's, the same path in the adapter."""
        named = {iri}
        parts = iri.split("/")
        for slashes in self.slashes:
            within = "/".join(parts[-(slashes + 1) :])
            if len(parts) >= slashes + 2 and within:
                named.add(self.base + within)
        return named

    @property
    def file(self):
        if self.path is None:
            return None
        try:
            return self.path.relative_to(self.adapter).as_posix()
        except ValueError:
            return self.path.name


def type_labels():
    """The label the Bridge vocabulary gives each class of manifest entry."""
    rdflib = packages.installed("rdflib")
    graph = graph_of(SPEC_ROOT / "vocab" / "bridge.ttl", format="turtle")
    return {str(kind): str(label) for kind, label in graph.subject_objects(rdflib.RDFS.label)}


def outcome_status(words):
    """The status of a test the report gives these outcomes and no fault: that of the one word they all are, `other` for a mix."""
    if len(set(words)) > 1:
        return "other"
    return STATUS_OF.get(words[0])


def environment(record):
    under_test = next(row for row in record.used if row.role is Role.UNDER_TEST)
    found = {"repositoryUrl": under_test.repository, "commit": under_test.commit}
    run = build_url()
    if run:
        found["buildUrl"] = run
    if os.environ.get("GITHUB_REF_NAME") and record.mode == "ci":
        found["branchName"] = os.environ["GITHUB_REF_NAME"]
    return {key: value for key, value in found.items() if value}


def build_url():
    repository, run = os.environ.get("GITHUB_REPOSITORY"), os.environ.get("GITHUB_RUN_ID")
    return url_on_this_server(f"{repository}/actions/runs/{run}") if repository and run else None


class Cases:
    """Each case of each counterpart's adapter, on each engine host, as the judge's verdict on it."""

    def __init__(self, record):
        self.record = record
        self.adapter_side = is_adapter(record.directory)
        self.under_test = next(row for row in record.used if row.role is Role.UNDER_TEST)
        self.manifests = {}
        self.labels = None
        self.tests = []

    def manifest(self, adapter):
        if adapter not in self.manifests:
            self.manifests[adapter] = Manifest(adapter)
        return self.manifests[adapter]

    def type_label(self, kinds):
        if self.labels is None:
            self.labels = type_labels()
        known = [self.labels[kind] for kind in kinds if kind in self.labels]
        return known[0] if known else (kinds[0] if kinds else None)

    def collect(self):
        for row in self.record.counterparts:
            if row.verdict is not None and row.adapter is not None:
                self.tests += self.cases_on(row)
        return self.tests

    def cases_on(self, row):
        manifest = self.manifest(row.adapter)
        verdict = row.verdict
        engine = row.name if self.adapter_side else self.under_test.name
        adapter = self.under_test if self.adapter_side else row
        host = f"with {engine}" + (f" on {row.host}" if row.host else "")
        suite = [manifest.label, host]
        shared = {"adapter": {"repository": adapter.repository, "commit": adapter.commit}}
        if row.report is not None and row.report.is_file():
            shared["report"] = f"earl/{row.report.name}"
        levels = [{"name": manifest.label}, {"name": host}]

        def described(found):
            """The cases written, with the manifest's level saying how many there are, or that there are none to count."""
            if manifest.unreadable is not None:
                levels[0]["description"] = (
                    f"The test manifest of {manifest.adapter.name} could not be read, so its cases are not known."
                )
            else:
                levels[0]["description"] = (
                    f"{len(found)} cases of {manifest.adapter.name}, each an entry of its test manifest "
                    "or a fault the judge names that no entry does, run by an engine host and judged by the "
                    "compatibility tool."
                )
            return found

        def case(name, status, message=None, entry=None):
            found = {"name": name, "status": status, "duration": 0, "suite": suite}
            if message:
                found["message"] = one_line(message)
            if manifest.file:
                found["filePath"] = manifest.file
            extra = {}
            if entry is not None:
                fragment = entry["iri"].rsplit("#", 1)[-1] if "#" in entry["iri"] else None
                if fragment in manifest.lines:
                    found["line"] = manifest.lines[fragment]
                if entry["comment"]:
                    extra["description"] = entry["comment"]
                if entry["types"]:
                    extra["type"] = self.type_label(entry["types"])
            found["extra"] = {**extra, **shared, "levels": levels}
            return found

        if manifest.unreadable is not None:
            said = f"{MANIFEST_CASE} could not be read: {manifest.unreadable}"
            message = f"{row.result}; {said}" if verdict.unjudged else said
            own = [case(MANIFEST_CASE, "failed", message)]
            return described(own + [case(fault, "failed", fault) for _, fault in verdict.named])
        if verdict.unjudged is not None:
            return described([case(entry["name"], "failed", row.result, entry) for entry in manifest.entries])

        by_iri = {entry["iri"]: entry for entry in manifest.entries}
        faults = {iri: [] for iri in by_iri}
        own = []
        for named, fault in verdict.named:
            matched = [iri for iri in (manifest.candidates(named) if named else ()) if iri in by_iri]
            for iri in matched:
                faults[iri].append(fault)
            if not matched:
                own.append(case(fault, "failed", fault))
        outcomes = {iri: [] for iri in by_iri}
        for test, word in verdict.reported:
            for iri in (iri for iri in (manifest.candidates(test) if test else ()) if iri in by_iri):
                outcomes[iri].append(word)
        nothing_reported = not verdict.reported
        cases = []
        for iri, entry in by_iri.items():
            words = list(dict.fromkeys(outcomes[iri]))
            if faults[iri]:
                status, message = "failed", "; ".join(faults[iri])
            elif not words:
                status = "failed"
                message = "; ".join(f for n, f in verdict.named if n is None) if nothing_reported else None
                message = message or f"{entry['name']} has no outcome"
            elif outcome_status(words):
                status, message = outcome_status(words), None
            else:
                status, message = "failed", f"{entry['name']} is reported {', '.join(words)}"
            found = case(entry["name"], status, message, entry)
            if words:
                found["extra"]["outcome"] = words
            cases.append(found)
        return described(cases + own)


def ctrf(record, cases):
    now = int(time.time() * 1000)
    start, stop = record.started or now, record.stopped or now
    count = {
        status: sum(found["status"] == status for found in cases) for status in ("passed", "failed", "skipped", "other")
    }
    return {
        "reportFormat": "CTRF",
        "specVersion": "0.2.0",
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "generatedBy": "cascade-bridge-spec scripts/compatibility.py",
        "results": {
            "tool": {"name": TOOL},
            "summary": {
                "tests": len(cases),
                **count,
                "pending": 0,
                "start": start,
                "stop": stop,
                "duration": stop - start,
            },
            "tests": cases,
            "environment": environment(record),
            "extra": {"caseDurations": "unmeasured"},
        },
    }


def markdown(record, cases):
    groups = {}
    for found in cases:
        groups.setdefault(tuple(found["suite"]), []).append(found)
    count = {status: sum(found["status"] == status for found in cases) for status in MARKS}
    said = ", ".join(
        f"{count[status]} {word}"
        for status, word in (("passed", "passed"), ("failed", "failed"), ("skipped", "skipped"), ("other", "undecided"))
        if count[status]
    )
    lines = [
        f"### Each case of {record.directory.name} on each engine host",
        "",
        f"{len(cases)} cases in {len(groups)} {'group' if len(groups) == 1 else 'groups'}: {said}.",
        "",
    ]
    ordered = sorted(groups.items(), key=lambda group: all(found["status"] != "failed" for found in group[1]))
    for (label, host), held in ordered:
        failed = sum(found["status"] == "failed" for found in held)
        counts = f"{len(held)} cases" + (f", {failed} failed" if failed else "")
        lines += [
            f"<details{' open' if failed else ''}>",
            f"<summary>{html.escape(label)}, {html.escape(host)}: {counts}</summary>",
            "",
        ]
        for found in sorted(held, key=lambda one: one["status"] != "failed"):
            name = found["name"].replace("`", "'")
            line = f"- {MARKS[found['status']]} `{name}`"
            message = found.get("message")
            if message and message != found["name"]:
                line += f": {message}"
            comment = found["extra"].get("description")
            if found["status"] == "failed" and comment:
                line += f" ({comment})"
            lines.append(line)
        lines += ["", "</details>", ""]
    return "\n".join(lines)


def write(record, options):
    """Writes the case report where a run judged each engine host's report; its Markdown, or None where it wrote none."""
    cases = Cases(record).collect()
    if not cases:
        return None
    (options.results / CTRF).write_text(json.dumps(ctrf(record, cases), indent=2) + "\n", encoding="utf-8")
    written = markdown(record, cases)
    (options.results / MARKDOWN).write_text(written, encoding="utf-8")
    return written


def pointer(options):
    """The line of table.md that says where the case report is, for a run that wrote one in CI."""
    url = build_url()
    if options.mode != "ci" or url is None:
        return ""
    where = linked("this run's summary", url)
    if where == "this run's summary":
        where += f" at {url}"
    artifact = os.environ.get("CASCADE_REPORT_ARTIFACT")
    held = f"; for a tool, `{CTRF}` in the run's artifact `{artifact}`" if artifact else ""
    return f"\nEach case on each engine host: {where}{held}.\n"
