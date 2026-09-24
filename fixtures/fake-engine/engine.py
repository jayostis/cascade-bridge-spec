#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

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
        "example-release-2026-01": "untested",
    },
    "failed": {
        "example-0001": "failed",
        "example-0002": "cantTell",
        "example-0003": "passed",
        "example-0004": "passed",
        "example-0005": "passed",
        "example-0006": "passed",
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--canned", choices=("passed", "failed", "partial", "none", "garbled"), default="passed")
    parser.add_argument("command", choices=("test", "convert"))
    parser.add_argument("adapter", type=Path)
    parser.add_argument("document", type=Path, nargs="?")
    parser.add_argument("--earl", type=Path)
    parser.add_argument("--vocabularies", type=Path)
    parser.add_argument("--datasets", action="store_true")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--findings", type=Path)
    parser.add_argument("--format", choices=tuple(GRAPH), default="turtle")
    args = parser.parse_args()

    adapter = args.adapter.resolve()
    if not (adapter / "ro-crate-metadata.json").is_file():
        print(f"fake engine: {adapter} holds no ro-crate-metadata.json", file=sys.stderr)
        return 2
    return {"test": test, "convert": convert}[args.command](args, adapter)


if __name__ == "__main__":
    sys.exit(main())
