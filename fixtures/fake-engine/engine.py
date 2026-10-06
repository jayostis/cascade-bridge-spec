#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urljoin
from xml.etree import ElementTree

EARL = """@prefix earl: <http://www.w3.org/ns/earl#> .

<https://example.org/fake-engine> a earl:Software .
"""

ASSERTION = """
[] a earl:Assertion ;
  earl:assertedBy <https://example.org/fake-engine> ;
  earl:subject <https://example.org/fake-engine> ;
  earl:test <{manifest}#{test}> ;
  earl:mode earl:automatic ;
  earl:result [ a earl:TestResult ; earl:outcome earl:{outcome} ] .
"""

CANNED = {
    "passed": {
        "example-0001": "passed",
        "example-0002": "cantTell",
        "example-0003": "passed",
        "example-0004": "passed",
        "example-0005": "passed",
        "example-0006": "passed",
        "example-0008": "passed",
        "example-0002-and-example-0007-name-one-record": "passed",
        "example-0008-names-two-records": "passed",
        "example-release-2026-01": "untested",
    },
    "failed": {
        "example-0001": "failed",
        "example-0002": "cantTell",
        "example-0003": "passed",
        "example-0004": "passed",
        "example-0005": "passed",
        "example-0006": "passed",
        "example-0008": "passed",
        "example-0002-and-example-0007-name-one-record": "passed",
        "example-0008-names-two-records": "passed",
        "example-release-2026-01": "untested",
    },
    "partial": {"example-0001": "passed"},
}

GRAPH = {
    "turtle": """@prefix ex: <https://example.org/fake-engine/> .

<https://example.org/fake-engine/record/1> a ex:Record .
""",
    "ntriples": (
        "<https://example.org/fake-engine/record/1>"
        " <http://www.w3.org/1999/02/22-rdf-syntax-ns#type>"
        " <https://example.org/fake-engine/Record> .\n"
    ),
}

FINDINGS = {
    "turtle": """@prefix oa: <http://www.w3.org/ns/oa#> .

<https://example.org/fake-engine/finding/1> a oa:Annotation ;
  oa:hasTarget <https://example.org/fake-engine/record/1> .
""",
    "ntriples": (
        "<https://example.org/fake-engine/finding/1>"
        " <http://www.w3.org/1999/02/22-rdf-syntax-ns#type>"
        " <http://www.w3.org/ns/oa#Annotation> .\n"
        "<https://example.org/fake-engine/finding/1>"
        " <http://www.w3.org/ns/oa#hasTarget>"
        " <https://example.org/fake-engine/record/1> .\n"
    ),
}


def test(args, adapter):
    print(f"fake engine: testing {adapter}, report canned {args.canned}")
    if args.vocabularies is not None:
        print(f"fake engine: vocabularies {args.vocabularies}")
    if args.earl is None or args.canned == "none":
        return 0
    if args.canned == "garbled":
        args.earl.write_text("this is not Turtle {\n", encoding="utf-8")
        return 0
    manifest = (adapter / "fixtures" / "manifest.ttl").as_uri()
    body = EARL + "".join(
        ASSERTION.format(manifest=manifest, test=name, outcome=outcome) for name, outcome in CANNED[args.canned].items()
    )
    args.earl.write_text(body, encoding="utf-8")
    return 0


def names_a_vocabulary_file(adapter):
    crate = json.loads((adapter / "ro-crate-metadata.json").read_text(encoding="utf-8"))
    return any("bridge:vocabularyFile" in entity for entity in crate["@graph"])


def convert(args, adapter):
    if args.document is None or not args.document.is_file():
        print(f"fake engine: {args.document} is not a document to convert", file=sys.stderr)
        return 2
    if args.findings is not None and args.vocabularies is None and names_a_vocabulary_file(adapter):
        print(f"fake engine: {adapter} names a bridge:vocabularyFile and no --vocabularies was given", file=sys.stderr)
        return 2
    print(f"fake engine: converting {args.document} with {adapter}; detect answered true", file=sys.stderr)
    graph = GRAPH[args.format]
    if args.out is None:
        sys.stdout.write(graph)
    else:
        args.out.write_text(graph, encoding="utf-8")
    if args.findings is not None:
        args.findings.write_text(FINDINGS[args.format], encoding="utf-8")
    return 0


CRATE = "ro-crate-metadata.json"
BRIDGE = "https://ns.cascadeprotocol.org/bridge/v1-draft#"
SCHEMA = "http://schema.org/"
RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
OA_HAS_SOURCE = "http://www.w3.org/ns/oa#hasSource"
FORMATS = {"turtle": "turtle", "ntriples": "nt"}
MF = "http://www.w3.org/2001/sw/DataAccess/tests/test-manifest#"
ASSERTION_OF = """
[] a earl:Assertion ;
  earl:assertedBy <https://example.org/fake-engine> ;
  earl:subject <https://example.org/fake-engine> ;
  earl:test <{entry}> ;
  earl:mode earl:automatic ;
  earl:result [ a earl:TestResult ; earl:outcome earl:{outcome} ] .
"""
OUTCOMES = {"InputOnlyTest": "cantTell", "DatasetCompletionTest": "untested"}

LIBRARY = {
    "holds": {},
    "document-kind-for-adapter": {"adapterFailure": "documentFailure"},
    "file-iri-in-findings": {},
    "none": {},
}


class Failure(Exception):
    def __init__(self, kind, map=None, path=None):
        super().__init__(kind)
        self.kind, self.map, self.path = kind, map, path

    def result(self, mode):
        failure = {"kind": LIBRARY[mode].get(self.kind, self.kind)}
        if self.map is not None:
            failure.update(map=self.map, path=self.path)
        return {"failure": failure}


def listed(value):
    return value if isinstance(value, list) else [] if value is None else [value]


def crate_of(metadata):
    crate = json.loads(metadata)
    nodes = {node.get("@id"): node for node in crate["@graph"]}
    return crate, nodes, nodes["./"]


def described(adapter_iri, metadata):
    """The description's triples: the crate's own terms, and the files a load and a test need."""
    crate, nodes, root = crate_of(metadata)
    at = adapter_iri + CRATE

    def inside(value):
        if isinstance(value, dict) and isinstance(value.get("@id"), str):
            resolved = urljoin(at, value["@id"])
            if resolved.startswith(adapter_iri):
                return resolved.removeprefix(adapter_iri).split("#")[0]
        return None

    envelopes = listed(root.get("bridge:envelope"))
    load = [CRATE]
    for node in [root, *(nodes.get(envelope["@id"], {}) for envelope in envelopes)]:
        for key, value in node.items():
            if key.startswith("bridge:") and key != "bridge:testManifest":
                load += [path for path in map(inside, listed(value)) if path]
    files = [CRATE, *(inside(node) for node in crate["@graph"] if "File" in listed(node.get("@type")))]
    iri, literal = "iri", "literal"
    return [
        (RDF_TYPE, iri, BRIDGE + "Adapter"),
        *((SCHEMA + "identifier", literal, value) for value in listed(root.get("identifier"))),
        *((SCHEMA + "version", literal, value) for value in listed(root.get("version"))),
        *((BRIDGE + "sourceMediaType", literal, value) for value in listed(root.get("bridge:sourceMediaType"))),
        *((BRIDGE + "envelope", iri, urljoin(at, envelope["@id"])) for envelope in envelopes),
        *(
            (BRIDGE + "cascadeVocabularyRepository", iri, urljoin(at, repository["@id"]))
            for repository in listed(root.get("bridge:cascadeVocabularyRepository"))
        ),
        *((BRIDGE + "vocabularyFile", literal, path) for path in listed(root.get("bridge:vocabularyFile"))),
        *((BRIDGE + "loadFile", literal, path) for path in dict.fromkeys(load)),
        *((BRIDGE + "crateFile", literal, path) for path in dict.fromkeys(path for path in files if path)),
    ]


def n_triples(subject, triples):
    """N-Triples, which is Turtle too."""
    return "".join(
        f"<{subject}> <{predicate}> " + (f"<{value}>" if kind == "iri" else json.dumps(value)) + " .\n"
        for predicate, kind, value in triples
    )


def library_files(given):
    """A map's bytes by key, where the calls file gave one."""
    return None if given is None else {key: Path(path).read_bytes() for key, path in given["files"].items()}


def needed(adapter, vocabulary, iri, wanted):
    if CRATE not in adapter:
        raise Failure("fileMissingFailure", "adapter", CRATE)
    triples = described(iri, adapter[CRATE])
    for path in (value for predicate, _, value in triples if predicate == BRIDGE + wanted):
        if path not in adapter:
            raise Failure("fileMissingFailure", "adapter", path)
    vocabulary_files = [value for predicate, _, value in triples if predicate == BRIDGE + "vocabularyFile"]
    for path in vocabulary_files if vocabulary is not None else []:
        if path not in vocabulary:
            raise Failure("fileMissingFailure", "vocabulary", path)
    return triples, vocabulary_files


def parsed(kind, data, parse):
    try:
        return parse(data)
    except Exception as error:
        raise Failure(kind) from error


def turtle(data, base):
    import rdflib

    return rdflib.Graph().parse(data=data, format="turtle", publicID=base)


def load_adapter(given):
    from rdflib.plugins.sparql.parser import parseQuery

    iri = given["adapter"]["iri"]
    adapter, vocabulary = library_files(given["adapter"]), library_files(given.get("vocabulary"))
    triples, vocabulary_files = needed(adapter, vocabulary, iri, "loadFile")
    for path in (value for predicate, _, value in triples if predicate == BRIDGE + "loadFile"):
        if path.endswith(".rq"):
            parsed("adapterFailure", adapter[path], lambda data: parseQuery(data.decode("utf-8")))
        elif path.endswith(".ttl"):
            parsed("adapterFailure", adapter[path], lambda data, path=path: turtle(data, iri + path))
    for path in vocabulary_files if vocabulary is not None else []:
        parsed(
            "vocabularyFailure",
            vocabulary[path],
            lambda data, path=path: turtle(data, given["vocabulary"]["iri"] + path),
        )
    _, nodes, root = crate_of(adapter[CRATE])
    envelopes = {urljoin(iri + CRATE, envelope["@id"]): nodes[envelope["@id"]] for envelope in root["bridge:envelope"]}
    return {"iri": iri, "root": root, "envelopes": envelopes, "vocabulary": vocabulary is not None}


def read_document(loaded, document):
    data = Path(document["path"]).read_bytes()
    envelope = document.get("envelope")
    if envelope is not None and envelope not in loaded["envelopes"]:
        raise Failure("documentFailure")
    if loaded["root"]["bridge:sourceMediaType"].endswith("json"):
        return parsed("documentFailure", data, json.loads)
    return parsed("documentFailure", data, ElementTree.fromstring)


def local_name(element):
    return element.tag.rsplit("}", 1)[-1]


def ask(given, loaded, _):
    document = read_document(loaded, given["document"])
    names = {envelope.get("bridge:docRootElementName") for envelope in loaded["envelopes"].values()}
    if isinstance(document, dict):
        members = {envelope.get("bridge:docRootMemberName") for envelope in loaded["envelopes"].values()}
        return {"answer": any(member in document for member in members)}
    record = loaded["root"].get("bridge:elementNameOfEachRecord")
    holds_a_record = local_name(document) == record or any(local_name(child) == record for child in document)
    return {"answer": local_name(document) in names and holds_a_record}


def committed(document, kind):
    """The adapter's own expected file for a document it committed under fixtures/in/, and the IRI it is read at."""
    path, iri = Path(document["path"]), document["iri"]
    file = path.parent.parent / kind / f"{path.stem}.ttl"
    if path.parent.name != "in" or "/in/" not in iri or not file.is_file():
        raise Failure("bridgeFailure")
    return file.read_bytes(), f"{iri.rsplit('/in/', 1)[0]}/{kind}/{path.stem}.ttl"


def convert_document(given, loaded, mode):
    document = given["document"]
    read_document(loaded, document)
    facts = document.get("facts")
    if facts is not None:
        parsed("factsFailure", Path(facts["path"]).read_bytes(), lambda data: turtle(data, facts["iri"]))
    written = {"graph": turtle(*committed(document, "expected"))}
    if loaded["vocabulary"]:
        findings = turtle(*committed(document, "findings"))
        if mode == "file-iri-in-findings":
            import rdflib

            for target in list(findings.subjects(rdflib.URIRef(OA_HAS_SOURCE), None)):
                findings.set((target, rdflib.URIRef(OA_HAS_SOURCE), rdflib.URIRef(Path(document["path"]).as_uri())))
        written["findings"] = findings
    return {name: graph.serialize(format=FORMATS[given["format"]]) for name, graph in written.items()}


def test_adapter(given):
    import rdflib

    iri = given["adapter"]["iri"]
    adapter, vocabulary = library_files(given["adapter"]), library_files(given.get("vocabulary"))
    if vocabulary is None and CRATE in adapter and "bridge:vocabularyFile" in crate_of(adapter[CRATE])[2]:
        raise Failure("vocabularyFailure")
    needed(adapter, vocabulary, iri, "crateFile")
    named = crate_of(adapter[CRATE])[2]["bridge:testManifest"]["@id"]
    manifest = turtle(adapter[named], iri + named)
    listing = next(manifest.subjects(rdflib.URIRef(BRIDGE + "adapter"), None))
    entries = manifest.items(manifest.value(listing, rdflib.URIRef(MF + "entries")))
    report = EARL + "".join(
        ASSERTION_OF.format(
            entry=entry,
            outcome=OUTCOMES.get(str(manifest.value(entry, rdflib.RDF.type)).removeprefix(BRIDGE), "passed"),
        )
        for entry in entries
    )
    return report


def run_library(args):
    calls = json.loads(args.calls.read_text(encoding="utf-8"))
    if args.library == "none":
        print("fake engine: library results canned none, so none written")
        return 0
    for case in calls["cases"]:
        written = args.results / case["name"]
        written.mkdir(parents=True, exist_ok=True)
        loaded = None
        for position, call in enumerate(case["calls"], 1):
            [(operation, given)] = call.items()
            if operation in ("ask", "convert") and loaded is None:
                continue
            try:
                result = {}
                if operation == "describe":
                    metadata = Path(given["metadata"]).read_bytes()
                    graph = n_triples(given["adapter"], described(given["adapter"], metadata))
                    (written / f"{position}.graph").write_text(graph, encoding="utf-8")
                elif operation == "load":
                    loaded = load_adapter(given)
                elif operation == "ask":
                    result = ask(given, loaded, args.library)
                elif operation == "convert":
                    for name, data in convert_document(given, loaded, args.library).items():
                        (written / f"{position}.{name}").write_text(data, encoding="utf-8")
                else:
                    (written / f"{position}.report").write_text(test_adapter(given), encoding="utf-8")
            except Failure as failure:
                result = failure.result(args.library)
            (written / f"{position}.json").write_text(json.dumps(result), encoding="utf-8")
    print(f"fake engine: {len(calls['cases'])} library cases, results canned {args.library}")
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--canned", choices=("passed", "failed", "partial", "none", "garbled"), default="passed")
    parser.add_argument("--library", choices=tuple(LIBRARY), default="holds")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("test", "convert"):
        command = commands.add_parser(name)
        command.add_argument("adapter", type=Path)
        command.add_argument("document", type=Path, nargs="?")
        command.add_argument("--earl", type=Path)
        command.add_argument("--vocabularies", type=Path)
        command.add_argument("--datasets", action="store_true")
        command.add_argument("--out", type=Path)
        command.add_argument("--findings", type=Path)
        command.add_argument("--format", choices=tuple(GRAPH), default="turtle")
    library = commands.add_parser("library")
    library.add_argument("calls", type=Path)
    library.add_argument("results", type=Path)
    args = parser.parse_args()

    if args.command == "library":
        return run_library(args)
    adapter = args.adapter.resolve()
    if not (adapter / "ro-crate-metadata.json").is_file():
        print(f"fake engine: {adapter} holds no ro-crate-metadata.json", file=sys.stderr)
        return 2
    return {"test": test, "convert": convert}[args.command](args, adapter)


if __name__ == "__main__":
    sys.exit(main())
