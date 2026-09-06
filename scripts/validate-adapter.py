#!/usr/bin/env python3
"""Validate a Cascade Bridge Adapter package against this specification.

Two checks, the two docs/validation.md names first:

  1. the package is a valid RO-Crate 1.2, by the RO-Crate validator;
  2. the crate and the test manifest it names, loaded as one RDF graph, conform
     to shapes/bridge.shapes.ttl, by pySHACL with SHACL-SPARQL enabled.

The rest of the lint docs/validation.md describes -- the file inventory, the
digests, the source-schema validation, the expected graphs -- is not here yet;
it is the reusable GitHub Action this repository has still to publish.

Base IRIs are the point of the second check, so they are set explicitly rather
than left to a default. The crate is parsed with ro-crate-metadata.json's own
location as base and the manifest with its own, which is what makes the two
files one graph: the crate's "./" and the manifest's <../> become the same IRI,
the adapter; the crate's "fixtures/manifest.ttl" and the manifest's <> become
the same IRI; and the manifest's <../ro-crate-metadata.json#envelope-efetch>
resolves onto the envelope entity the crate declares. Load either file with the
wrong base and every link between them silently becomes two unrelated nodes,
and the shapes report nothing rather than reporting a mistake.

Usage:

    python3 scripts/validate-adapter.py <path to an adapter checkout>

Exit status is 0 when both checks pass and 1 when either fails.

Requires pyshacl, rdflib and roc-validator (pip install pyshacl rdflib
roc-validator); the RO-Crate validator is invoked as the rocrate-validator
command it installs.
"""

import argparse
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import url2pathname

from pyshacl import validate as shacl_validate
from rdflib import Graph, Namespace
from rdflib.namespace import RDF, SH

BRIDGE = Namespace("https://ns.cascadeprotocol.org/bridge/v1-draft#")

SPEC_ROOT = Path(__file__).resolve().parent.parent
SHAPES = SPEC_ROOT / "shapes" / "bridge.shapes.ttl"

# The one sentence the ClinVar pilot's next pull request is written to remove.
SPEC_PIN_ONLY = (
    "the crate is valid and the manifest conforms except for the "
    "missing bridge:specPin"
)


def report(ok, line):
    print(("  ok    " if ok else "  FAIL  ") + line)


def validate_crate(adapter):
    """Check 1: the package is a valid RO-Crate 1.2."""
    print("RO-Crate 1.2")
    try:
        run = subprocess.run(
            [
                "rocrate-validator",
                "validate",
                str(adapter),
                "--profile-identifier",
                "ro-crate-1.2",
                "--no-paging",
            ],
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        report(False, "rocrate-validator is not installed (pip install roc-validator)")
        return False
    ok = run.returncode == 0
    report(ok, f"{adapter}/ro-crate-metadata.json")
    if not ok:
        print(run.stdout.strip() or run.stderr.strip())
    return ok


def load(adapter):
    """Load the crate and the test manifest it names as one graph.

    Returns the graph, the adapter's root-entity IRI, and the manifest path.
    """
    crate_file = adapter / "ro-crate-metadata.json"
    graph = Graph()
    graph.parse(
        crate_file, format="json-ld", base=crate_file.resolve().as_uri()
    )

    roots = list(graph.subjects(RDF.type, BRIDGE.Adapter))
    if len(roots) != 1:
        raise SystemExit(
            f"  FAIL  the crate declares {len(roots)} bridge:Adapter entities; "
            "exactly one, the root entity, is expected"
        )
    root = roots[0]

    manifests = list(graph.objects(root, BRIDGE.testManifest))
    if len(manifests) != 1:
        raise SystemExit(
            f"  FAIL  the adapter names {len(manifests)} bridge:testManifest "
            "values; exactly one is expected"
        )
    manifest_file = Path(url2pathname(urlparse(str(manifests[0])).path))
    if not manifest_file.is_file():
        raise SystemExit(
            f"  FAIL  the adapter's bridge:testManifest names {manifest_file}, "
            "which does not exist"
        )
    graph.parse(manifest_file, format="turtle", publicID=str(manifests[0]))

    return graph, root, manifest_file


def validate_shapes(graph, root, manifest_file):
    """Check 2: the crate and the manifest conform to this repository's shapes."""
    print("SHACL, crate and test manifest as one graph")
    conforms, results, _ = shacl_validate(
        graph,
        shacl_graph=Graph().parse(SHAPES, format="turtle"),
        advanced=True,          # the shapes use sh:sparql constraints
        allow_warnings=True,    # warnings are reported below, not failed on
        inplace=False,
    )

    violations, warnings = [], []
    for result in results.subjects(RDF.type, SH.ValidationResult):
        severity = results.value(result, SH.resultSeverity)
        path = results.value(result, SH.resultPath)
        message = str(results.value(result, SH.resultMessage) or "").strip()
        (violations if severity == SH.Violation else warnings).append(
            (path, message)
        )

    missing_spec_pin = (root, BRIDGE.specPin, None) not in graph
    only_spec_pin = bool(violations) and all(
        path == BRIDGE.specPin for path, _ in violations
    )

    if conforms and not violations:
        report(True, f"{SHAPES.name} against the crate and {manifest_file.name}")
    elif only_spec_pin and missing_spec_pin:
        report(False, SPEC_PIN_ONLY)
        print(
            "        The adapter's root entity carries no bridge:specPin: the\n"
            "        commit of this specification it is written against, a\n"
            "        SoftwareSourceCode entity in the crate with codeRepository\n"
            "        and version (the full SHA), the same shape as\n"
            "        bridge:vocabularyPin. Nothing else about the crate or the\n"
            "        test manifest is wrong. docs/adapter-manifest.md."
        )
    else:
        report(False, f"{len(violations)} violation(s)")
        if missing_spec_pin:
            print("        including a missing bridge:specPin")
        for path, message in violations:
            print(f"        {path or '-'}: {message}")

    for path, message in warnings:
        print(f"  warn  {path or '-'}: {message}")

    return not violations


def main():
    parser = argparse.ArgumentParser(
        description="Validate a Cascade Bridge Adapter package against "
        "the Cascade Bridge Specification."
    )
    parser.add_argument("adapter", type=Path, help="path to an adapter checkout")
    args = parser.parse_args()

    adapter = args.adapter.resolve()
    if not (adapter / "ro-crate-metadata.json").is_file():
        raise SystemExit(f"  FAIL  {adapter} holds no ro-crate-metadata.json")

    print(f"Adapter: {adapter}")
    print(f"Spec:    {SPEC_ROOT}")
    print()

    crate_ok = validate_crate(adapter)
    graph, root, manifest_file = load(adapter)
    shapes_ok = validate_shapes(graph, root, manifest_file)

    print()
    print("PASS" if crate_ok and shapes_ok else "FAIL")
    return 0 if crate_ok and shapes_ok else 1


if __name__ == "__main__":
    sys.exit(main())
