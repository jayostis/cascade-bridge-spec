"""The library cases, run through each host's library command, and judged here rather than by the engine."""

import json
import shutil
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import url2pathname

from compatibility_tool import engines, packages
from compatibility_tool.bootstrap import SPEC_ROOT
from compatibility_tool.console import Stop, first_line, report
from compatibility_tool.document import CRATE, crate_root, hosts, is_adapter, read_file, referenced_id
from compatibility_tool.judge import EARL, MF, Verdict, faults_of, outcome_name
from compatibility_tool.record import Role, Row

MANIFEST = SPEC_ROOT / "fixtures" / "library" / "manifest.ttl"
CALLS_SCHEMA = SPEC_ROOT / "engine" / "library-calls.schema.json"
RESULT_SCHEMA = SPEC_ROOT / "engine" / "library-result.schema.json"
BRIDGE = "https://ns.cascadeprotocol.org/bridge/v1-draft#"
PROV = "http://www.w3.org/ns/prov#"
OA = "http://www.w3.org/ns/oa#"
OPERATIONS = {
    "DescribeCall": "describe",
    "LoadCall": "load",
    "AskCall": "ask",
    "ConvertCall": "convert",
    "TestCall": "test",
}
FORMATS = {"turtle": "turtle", "ntriples": "nt"}


@dataclass
class Call:
    operation: str
    given: dict
    maps: dict = field(default_factory=dict)
    adapter: tuple[str, Path] | None = None
    failure: str | None = None
    missing: str | None = None
    graph: Path | None = None
    findings: Path | None = None
    answer: bool | None = None


@dataclass
class Case:
    iri: str
    name: str
    calls: list[Call]


def path_of(iri):
    return Path(url2pathname(urlsplit(str(iri)).path))


def term(name):
    return packages.installed("rdflib").URIRef(BRIDGE + name)


def file_map(graph, node):
    """A map as the calls file gives it, and the directory it is read from."""
    directory = path_of(graph.value(node, term("directory")))
    withheld = [str(key) for key in graph.objects(node, term("withholds"))]
    files = {}
    for path in sorted(directory.rglob("*")):
        key = path.relative_to(directory).as_posix()
        if path.is_file() and not any(key == w or (w.endswith("/") and key.startswith(w)) for w in withheld):
            files[key] = str(path)
    for substitute in graph.objects(node, term("substitute")):
        files[str(graph.value(substitute, term("key")))] = str(path_of(graph.value(substitute, term("file"))))
    return {"iri": str(graph.value(node, term("iri"))), "files": files}, directory


def named_file(graph, node):
    return {"iri": str(graph.value(node, term("iri"))), "path": str(path_of(graph.value(node, term("file"))))}


def a_call(graph, node, latest):
    rdflib = packages.installed("rdflib")
    operation = OPERATIONS[str(graph.value(node, rdflib.RDF.type)).removeprefix(BRIDGE)]
    call = Call(operation, {}, adapter=latest)
    if operation in ("describe", "load", "test"):
        adapter, directory = file_map(graph, graph.value(node, term("adapterFiles")))
        call.adapter = (adapter["iri"], directory)
        call.maps = {"adapter": adapter}
        vocabulary = graph.value(node, term("vocabularyFiles"))
        if vocabulary is not None:
            call.maps["vocabulary"] = file_map(graph, vocabulary)[0]
        call.given = dict(call.maps)
    if operation == "describe":
        call.given = {"adapter": adapter["iri"], "metadata": str(directory / CRATE)}
    if operation in ("ask", "convert"):
        document = named_file(graph, graph.value(node, term("document")))
        envelope = graph.value(node, term("envelope"))
        if envelope is not None:
            document["envelope"] = str(envelope)
        facts = graph.value(node, term("suppliedFacts"))
        if facts is not None:
            document["facts"] = named_file(graph, facts)
        call.given = {"document": document}
    graph_format = graph.value(node, term("graphFormat"))
    if graph_format is not None:
        call.given["format"] = str(graph_format)
    failure = graph.value(node, term("failure"))
    call.failure = None if failure is None else str(failure).removeprefix(BRIDGE)
    call.missing = optional(graph.value(node, term("missingFile")))
    call.graph = optional_path(graph.value(node, term("expectedGraph")))
    call.findings = optional_path(graph.value(node, term("expectedFindings")))
    answer = graph.value(node, term("expectedAnswer"))
    call.answer = None if answer is None else bool(answer.toPython())
    return call


def optional(value):
    return None if value is None else str(value)


def optional_path(value):
    return None if value is None else path_of(value)


def read_cases():
    rdflib = packages.installed("rdflib")
    graph = rdflib.Graph().parse(MANIFEST, format="turtle", publicID=MANIFEST.as_uri())
    listing = graph.value(rdflib.URIRef(MANIFEST.as_uri()), rdflib.URIRef(MF + "entries"))
    cases = []
    for entry in graph.items(listing):
        latest, calls = None, []
        for node in graph.items(graph.value(entry, rdflib.URIRef(MF + "action"))):
            call = a_call(graph, node, latest)
            if call.operation == "load" and call.failure is None:
                latest = call.adapter
            calls.append(call)
        cases.append(Case(str(entry), str(graph.value(entry, rdflib.URIRef(MF + "name"))), calls))
    return cases, graph


def calls_file(cases):
    written = {"cases": [{"name": case.name, "calls": [{c.operation: c.given} for c in case.calls]} for case in cases]}
    problem = first_problem(CALLS_SCHEMA, written)
    if problem is not None:
        raise Stop(f"the calls file does not match {CALLS_SCHEMA.name}: {problem.message}")
    return written


def first_problem(schema, instance):
    validator = packages.installed("jsonschema").Draft202012Validator(json.loads(schema.read_text(encoding="utf-8")))
    return next(iter(validator.iter_errors(instance)), None)


def read_at(file, adapter):
    """An expected file inside the adapter's directory is read at the adapter IRI followed by its path there."""
    base = file.as_uri()
    if adapter is not None:
        iri, directory = adapter
        try:
            base = iri + file.relative_to(directory).as_posix()
        except ValueError:
            pass
    return packages.installed("rdflib").Graph().parse(file, format="turtle", publicID=base)


def returned(written, graph_format):
    try:
        return packages.installed("rdflib").Graph().parse(written, format=FORMATS.get(graph_format, graph_format)), None
    except Exception as error:
        return None, f"does not parse as {graph_format}: {first_line(str(error))}"


def names_a_file_iri(graph):
    URIRef = packages.installed("rdflib").URIRef
    return any(isinstance(node, URIRef) and str(node).startswith("file:") for triple in graph for node in triple)


def without_release(graph):
    rdflib = packages.installed("rdflib")
    copied = rdflib.Graph()
    for triple in graph:
        copied.add(triple)
    for association in list(copied.objects(None, rdflib.URIRef(PROV + "qualifiedAssociation"))):
        for agent in list(copied.objects(association, rdflib.URIRef(PROV + "agent"))):
            copied.remove((agent, None, None))
    return copied


def sources_and_bodies(graph):
    rdflib = packages.installed("rdflib")
    annotations = graph.subjects(rdflib.RDF.type, rdflib.URIRef(OA + "Annotation"))
    return Counter(
        (
            graph.value(graph.value(finding, rdflib.URIRef(OA + "hasTarget")), rdflib.URIRef(OA + "hasSource")),
            graph.value(finding, rdflib.URIRef(OA + "hasBody")),
        )
        for finding in annotations
    )


def isomorphic(one, other):
    packages.installed("rdflib")
    from rdflib.compare import isomorphic as compared

    return compared(one, other)


def result_of(directory, position):
    path = directory / f"{position}.json"
    if not path.is_file():
        return None, "wrote no result"
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as error:
        return None, f"wrote a result that is not JSON: {first_line(str(error))}"
    problem = first_problem(RESULT_SCHEMA, result)
    if problem is not None:
        return None, f"wrote a result {RESULT_SCHEMA.name} refuses: {problem.message}"
    return result, None


def failed_as_expected(call, failure):
    if failure is None:
        return f"returned, where it must fail with {call.failure}"
    if failure["kind"] != call.failure:
        return f"failed with {failure['kind']}, where {call.failure} was expected"
    if call.missing is not None:
        named = call.maps.get(failure["map"], {}).get("iri", "") + failure["path"]
        if named != call.missing:
            return f"named {failure['map']} {failure['path']} missing, where {call.missing} was expected"
    return None


def judged_graph(directory, position, call, kind):
    graph, problem = returned(directory / f"{position}.{kind}", call.given.get("format", "turtle"))
    if problem is not None:
        return None, f"the {kind} it returned {problem}"
    if names_a_file_iri(graph):
        return None, f"a file: IRI is in the {kind} it returned"
    return graph, None


def judged_report(directory, position, call):
    rdflib = packages.installed("rdflib")
    graph, problem = returned(directory / f"{position}.report", "turtle")
    if problem is not None:
        return f"the report it returned {problem}"
    if names_a_file_iri(graph):
        return "a file: IRI is in the report it returned"
    iri, adapter = call.adapter
    _, root = crate_root(adapter)
    named = referenced_id(root, "bridge:testManifest")
    manifest = rdflib.Graph().parse(adapter / named, format="turtle", publicID=iri + named)
    faults = faults_of(graph + manifest)
    if faults:
        return f"its report has faults: {'; '.join(faults)}"
    elsewhere = sorted({str(test) for test in graph.objects(None, rdflib.URIRef(EARL + "test"))} - {""})
    elsewhere = [test for test in elsewhere if not test.startswith(iri)]
    if elsewhere:
        return f"its report names {elsewhere[0]}, which is not under {iri}"
    return None


def judged_call(directory, position, call):
    result, problem = result_of(directory, position)
    if problem is not None:
        return problem
    failure = result.get("failure")
    if call.failure is not None:
        return failed_as_expected(call, failure)
    if failure is not None:
        said = f": {failure['message']}" if failure.get("message") else ""
        return f"failed with {failure['kind']}{said}"
    if call.operation == "ask":
        if result.get("answer") is not call.answer:
            return f"answered {str(result.get('answer')).lower()}, where {str(call.answer).lower()} was expected"
    if call.operation == "test":
        return judged_report(directory, position, call)
    if call.operation in ("describe", "convert"):
        graph, problem = judged_graph(directory, position, call, "graph")
        if problem is not None:
            return problem
        expected = read_at(call.graph, call.adapter)
        if call.operation == "convert":
            graph, expected = without_release(graph), without_release(expected)
        if not isomorphic(graph, expected):
            return f"its graph is not isomorphic to {call.graph.name}"
    if call.operation == "convert":
        return judged_findings(directory, position, call)
    return None


def judged_findings(directory, position, call):
    if call.findings is None:
        written = directory / f"{position}.findings"
        if not written.is_file():
            return None
        graph, problem = judged_graph(directory, position, call, "findings")
        if problem is None and len(graph):
            return "returned findings, where none was expected"
        return problem
    if not (directory / f"{position}.findings").is_file():
        return f"returned no findings, where {call.findings.name}'s were expected"
    graph, problem = judged_graph(directory, position, call, "findings")
    if problem is not None:
        return problem
    found, expected = sources_and_bodies(graph), sources_and_bodies(read_at(call.findings, call.adapter))
    if found != expected:
        missing, extra = expected - found, found - expected
        said = [f"{count} of {source} {body} missing" for (source, body), count in missing.items()]
        said += [f"{count} of {source} {body} not expected" for (source, body), count in extra.items()]
        return f"its findings are not {call.findings.name}'s by source and body: {'; '.join(said[:3])}"
    return None


def judged_case(directory, case):
    for position, call in enumerate(case.calls, 1):
        reason = judged_call(directory / case.name, position, call)
        if reason is not None:
            return f"call {position}, {call.operation}, {reason}"
    return None


def write_report(path, subject, cases, reasons):
    rdflib = packages.installed("rdflib")
    earl = rdflib.Namespace(EARL)
    graph = rdflib.Graph()
    graph.bind("earl", earl)
    for case in cases:
        assertion, result = rdflib.BNode(), rdflib.BNode()
        graph.add((assertion, rdflib.RDF.type, earl.Assertion))
        graph.add((assertion, earl.subject, rdflib.URIRef(subject)))
        graph.add((assertion, earl.test, rdflib.URIRef(case.iri)))
        graph.add((assertion, earl.mode, earl.automatic))
        graph.add((assertion, earl.result, result))
        graph.add((result, rdflib.RDF.type, earl.TestResult))
        reason = reasons[case.name]
        graph.add((result, earl.outcome, earl.failed if reason else earl.passed))
        if reason:
            graph.add((result, earl.info, rdflib.Literal(reason)))
    graph.serialize(path, format="turtle")
    return graph


def verdict_of(report_graph, manifest, cases, reasons, unjudged):
    if unjudged is not None:
        return Verdict(unjudged=unjudged)
    outcomes = report_graph.objects(None, packages.installed("rdflib").URIRef(EARL + "outcome"))
    tally = Counter(outcome_name(outcome) for outcome in outcomes)
    faults = faults_of(report_graph + manifest)
    said = [f"{case.name}: {reasons[case.name]}" for case in cases if reasons[case.name]]
    return Verdict(tally=dict(tally), tests=len(cases), faults=(said or faults) if faults else [])


def run(directory, record, options, set_up):
    """Each host of an engine under test, its library run on the cases and judged: a row of its own per host."""
    if is_adapter(directory):
        return
    listed = hosts(read_file(directory))
    if engines.unrunnable(listed):
        return
    print("The library cases on each host of the engine")
    cases, manifest = read_cases()
    root = options.results / "library"
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True)
    calls = root / "calls.json"
    calls.write_text(json.dumps(calls_file(cases), indent=2) + "\n", encoding="utf-8")
    under_test = next(entry for entry in record.used if entry.role is Role.UNDER_TEST)
    reports = options.results / "earl"
    reports.mkdir(parents=True, exist_ok=True)
    for index, host in enumerate(listed, 1):
        row = Row(
            name=under_test.name,
            repository=under_test.repository,
            commit=under_test.commit,
            how="the specification's library cases",
            role=Role.LIBRARY,
            uncommitted_edits=under_test.uncommitted_edits,
            path=directory,
            pull_request=under_test.pull_request,
            host=host["name"],
        )
        record.used.append(row)
        run_on_host(row, directory, host, set_up, cases, manifest, calls, root / f"on-host-{index}", options, index)


def run_on_host(row, engine, host, set_up, cases, manifest, calls, results, options, index):
    command = engines.prepared(engine, row.host, host, set_up, "the library")
    unjudged = "it was not run"
    if command is not None:
        results.mkdir(parents=True)
        argv = [*command, "library", str(calls), str(results)]
        print(f"  run   {' '.join(argv)}   (in {engine}, on {row.host})")
        status = engines.execute(argv, engine)
        if status is not None:
            unjudged = None if any(results.iterdir()) else "it wrote no results"
            report(True, f"the library cases ran on {row.host}, exit status {status}, which nothing relies on")
    reasons = {case.name: unjudged or judged_case(results, case) for case in cases}
    row.report = options.results / "earl" / f"library-on-host-{index}.ttl"
    subject = row.repository or engine.as_uri()
    graph = write_report(row.report, subject, cases, reasons)
    verdict = verdict_of(graph, manifest, cases, reasons, unjudged)
    row.holds = verdict.holds
    row.result = verdict.describe()
