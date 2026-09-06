#!/usr/bin/env python3
"""Validate a Cascade Bridge Adapter package against this specification.

Three checks, the first three docs/validation.md names:

  1. the package is a valid RO-Crate 1.2, by the RO-Crate validator;
  2. the crate and the test manifest it names, loaded as one RDF graph, conform
     to shapes/bridge.shapes.ttl, by pySHACL with SHACL-SPARQL enabled. The
     allowed set of media types is part of those shapes, so a file whose
     encodingFormat says it executes fails here;
  3. every git-tracked file is accounted for: a crate entity carrying a
     declared encodingFormat, or one of the four documents and the dotfiles
     that describe the repository rather than the package.

Checks 4 to 6 of docs/validation.md -- the digests, the source-schema
validation, the expected graphs -- are specified and not built.

This script is what .github/actions/validate-adapter runs, so an adapter's CI
is one `uses:` line pinned at a tag of this repository rather than a copy of
this file. It takes a directory. It knows no adapter's name, no adapter's
repository and no format id, and it must stay that way: a specification that
knows which adapters exist is the bug docs/alignment.md is written against.

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
    python3 scripts/validate-adapter.py <path> --spec-revision <full SHA>

With --spec-revision, the adapter's bridge:specPin is compared against the
revision of this specification the caller is actually running, which is how the
`uses:` pin in an adapter's workflow and the pin in its crate are held to naming
the same commit. Without it the pin is reported and not compared.

Exit status is 0 when every check passes and 1 when any fails.

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
from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import RDF, SH

BRIDGE = Namespace("https://ns.cascadeprotocol.org/bridge/v1-draft#")
SCHEMA = Namespace("http://schema.org/")

SPEC_ROOT = Path(__file__).resolve().parent.parent
SHAPES = SPEC_ROOT / "shapes" / "bridge.shapes.ttl"

# The one sentence an adapter written before this specification existed will
# hit, and the reason it is named rather than reported as a missing property:
# a generic message sends its author looking in the wrong file.
SPEC_PIN_ONLY = (
    "the crate is valid and the manifest conforms except for the "
    "missing bridge:specPin"
)

# The files a repository holding an adapter may carry without the crate
# describing them: they describe the repository, not the package
# (docs/validation.md, check 3). Everything else is either a described file or
# a file nobody reviewed. Dotfiles and dot-directories are allowed wholesale,
# which covers .gitattributes, .editorconfig, .vscode/ and .github/.
#
# ro-crate-metadata.json is in the list for a different reason from the other
# four. It is not undescribed: it is the crate's own metadata descriptor, the
# entity every RO-Crate is required to carry and the one entity RO-Crate 1.2
# forbids from being a data entity in hasPart. It therefore has no
# encodingFormat and cannot be given one, so the inventory must name it here
# or fail every conforming crate.
ALLOWLIST = {
    "README.md",
    "LICENSE",
    "CHANGELOG.md",
    "CLAUDE.md",
    "ro-crate-metadata.json",
}


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


def tracked_files(adapter):
    """Every file git tracks in the adapter's checkout, as relative paths.

    git, not a directory walk: a walk sees build output, a virtual environment
    and whatever the last run left behind, and an inventory that counts those
    is an inventory nobody can keep green.
    """
    run = subprocess.run(
        ["git", "-C", str(adapter), "ls-files", "-z"],
        capture_output=True,
        text=True,
    )
    if run.returncode != 0:
        return None
    return sorted(p for p in run.stdout.split("\0") if p)


def validate_inventory(adapter, graph):
    """Check 3: every git-tracked file is accounted for.

    Either the crate describes it and it declares an encodingFormat, or it is
    one of the four repository documents or a dotfile. This is the check that
    makes "an adapter is data" a measured property rather than a claim: a file
    nobody described is a file nobody reviewed.
    """
    print("File inventory")
    paths = tracked_files(adapter)
    if paths is None:
        report(
            False,
            f"{adapter} is not a git checkout, so the inventory cannot be taken",
        )
        return False, None

    undescribed = []
    described = 0
    for path in paths:
        first = path.split("/", 1)[0]
        if path in ALLOWLIST or first.startswith("."):
            continue
        entity = URIRef((adapter / path).resolve().as_uri())
        if graph.value(entity, SCHEMA.encodingFormat) is not None:
            described += 1
        else:
            undescribed.append(path)

    ok = not undescribed
    report(
        ok,
        f"{len(paths)} tracked file(s): {described} described by the crate, "
        f"{len(paths) - described - len(undescribed)} allowlisted, "
        f"{len(undescribed)} neither",
    )
    for path in undescribed:
        print(
            f"        {path}: no crate entity with a declared encodingFormat, "
            "and not one of README.md, LICENSE, CHANGELOG.md, CLAUDE.md, "
            "ro-crate-metadata.json or a dotfile"
        )
    return ok, described


def check_spec_pin(graph, root, spec_revision):
    """The crate's bridge:specPin and the revision being run must agree.

    The `uses:` pin in an adapter's workflow and the bridge:specPin in its
    crate are the same fact written twice, one for the machine and one for the
    reader (docs/alignment.md). This is where they are held to it.
    """
    print("Specification pin")
    pins = list(graph.objects(root, BRIDGE.specPin))
    if not pins:
        report(False, "no bridge:specPin to compare; the shapes named it above")
        return False
    pin = pins[0]
    version = graph.value(pin, SCHEMA.version)
    repository = graph.value(pin, SCHEMA.codeRepository)
    print(f"  read  {pin}")
    if version is None:
        report(False, f"{pin} carries no schema:version, so there is no SHA to compare")
        return False
    if repository is None:
        report(
            False,
            f"{pin} carries no schema:codeRepository, so the pin does not say "
            "which repository holds that commit",
        )
        return False
    if spec_revision is None:
        print(
            "  note  the revision of this specification being run was not "
            "given (--spec-revision), so the pin is reported and not compared"
        )
        return True
    ok = str(version) == spec_revision
    report(
        ok,
        f"bridge:specPin names {version}, and this specification is "
        f"{spec_revision}",
    )
    if not ok:
        print(
            "        The crate's pin and the revision of this specification the\n"
            "        adapter's workflow calls are the same fact written twice.\n"
            "        They move together, in the pull request that needs them\n"
            "        (docs/alignment.md)."
        )
    return ok


def tier_line(graph, root, inventory_ok):
    """The one derived fact the lint reports, in the words docs/validation.md
    fixes. Candidate, never universal: a lint sees one package on one machine,
    and a tier is measured by running an adapter's fixtures on every published
    Bridge (RFC section 11)."""
    profiles = sorted(
        str(p).rsplit("#", 1)[-1] for p in graph.objects(root, BRIDGE.profileRequired)
    )
    if not inventory_ok:
        return "tier: not computed, because the file inventory did not pass"
    if profiles:
        return "limited: requires " + ", ".join(profiles)
    return "universal candidate"


def main():
    parser = argparse.ArgumentParser(
        description="Validate a Cascade Bridge Adapter package against "
        "the Cascade Bridge Specification."
    )
    parser.add_argument("adapter", type=Path, help="path to an adapter checkout")
    parser.add_argument(
        "--spec-revision",
        default=None,
        help="the full SHA of the revision of this specification being run; "
        "when given, the adapter's bridge:specPin must name it",
    )
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
    inventory_ok, _ = validate_inventory(adapter, graph)
    pin_ok = check_spec_pin(graph, root, args.spec_revision)

    print()
    print(
        "not run, and specified in docs/validation.md: check 4, every digest\n"
        "matches its file; check 5, every input validates against the declared\n"
        "schema; check 6, every expected graph parses. A package passing the\n"
        "checks above has not been reported as passing those."
    )
    print()
    print(tier_line(graph, root, inventory_ok))
    print()
    ok = crate_ok and shapes_ok and inventory_ok and pin_ok
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
