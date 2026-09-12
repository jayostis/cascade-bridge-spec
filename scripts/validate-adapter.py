#!/usr/bin/env python3
"""Validate a Cascade Bridge Adapter package against this specification.

The six checks adapter/validation.md names, in the order it names them, so that
the cheapest check that can fail comes first and each later check may assume
the earlier ones held:

  1. the package is a valid RO-Crate 1.2, by the RO-Crate validator;
  2. the crate and the test manifest it names, loaded as one RDF graph, conform
     to shapes/bridge.shapes.ttl, by pySHACL with SHACL-SPARQL enabled. The
     allowed set of media types is part of those shapes, so a file whose
     encodingFormat says it executes fails here;
  3. every git-tracked file is accounted for: a crate entity carrying a
     declared encodingFormat, or one of the four documents and the dotfiles
     that describe the repository rather than the package;
  4. every digest matches its file, the local claim and the publisher's claim
     reported as the different assertions they are;
  5. every committed input validates against the schema its envelope declares;
  6. every expected graph parses as Turtle. Parsing, not conforming.

**Every check says whether it ran.** A check whose tool is absent, and a check
that found nothing of its kind in the package, are each reported in their own
words and never as a pass: a lint that silently checks nothing is worse than no
lint. The summary at the end lists all six with the word each earned.

Nothing here runs a mapping, compares a graph or reaches the network. Check 4
recomputes digests over the committed bytes and never fetches the publisher's
file; the run is offline and needs no credentials.

This script is what .github/actions/validate-adapter runs, so an adapter's CI
is one `uses:` line pinned at a tag of this repository rather than a copy of
this file. It takes a directory. It knows no adapter's name, no adapter's
repository and no format id, and it must stay that way: a specification that
knows which adapters exist is the bug pinning.md is written against.

Base IRIs are the point of the second check, so they are set explicitly rather
than left to a default. The crate is parsed with ro-crate-metadata.json's own
location as base and the manifest with its own, which is what makes the two
files one graph: the crate's "./" and the manifest's <../> become the same IRI,
the adapter; the crate's "fixtures/manifest.ttl" and the manifest's <> become
the same IRI; and the manifest's <../ro-crate-metadata.json#envelope-efetch>
resolves onto the envelope entity the crate declares. Load either file with the
wrong base and every link between them silently becomes two unrelated nodes,
and the shapes report nothing rather than reporting a mistake. Checks 4, 5 and
6 depend on the same thing for a different reason: they walk from a test to its
input, to its envelope's schema and to its expected graph, and every one of
those walks crosses between the two files.

Usage:

    python3 scripts/validate-adapter.py <path to an adapter checkout>
    python3 scripts/validate-adapter.py <path> --spec-revision <full SHA>

With --spec-revision, the adapter's bridge:specPin is compared against the
revision of this specification the caller is actually running, which is how the
`uses:` pin in an adapter's workflow and the pin in its crate are held to naming
the same commit. Without it the pin is reported and not compared.

Exit status is 0 when every check passes and 1 when any fails or could not be
run.

Requires pyshacl, rdflib, roc-validator and lxml (pip install pyshacl rdflib
roc-validator lxml); the RO-Crate validator is invoked as the
rocrate-validator command it installs, and lxml is the XSD 1.0 engine check 5
uses.
"""

import argparse
import hashlib
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
MF = Namespace("http://www.w3.org/2001/sw/DataAccess/tests/test-manifest#")

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
# (adapter/validation.md, check 3). Everything else is either a described file or
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

# Check 4. The local claim is schema:sha256 -- "sha256" in the RO-Crate 1.2
# context -- which says: these bytes, here, now. Every other digest property is
# the publisher's claim about the file at its source, in whatever namespace it
# is written (RO-Crate's workflow-run terms give md5, sha1, sha256, sha512).
# The two are different assertions, and a mismatch in each means something
# different, so they are recomputed the same way and reported differently
# (adapter/fixtures/README.md; adapter/validation.md, check 4).
DIGEST_ALGORITHMS = {
    "md5": hashlib.md5,
    "sha1": hashlib.sha1,
    "sha256": hashlib.sha256,
    "sha384": hashlib.sha384,
    "sha512": hashlib.sha512,
}
LOCAL_DIGEST = SCHEMA.sha256

# Check 5. The media types a source-side schema arrives in, and which engine
# reads each. XSD 1.0 by lxml is the only engine wired up; a source schema that
# is a JSON Schema is a real case, and it is reported as not run rather than
# passed.
XSD_MEDIA_TYPES = {"application/xml", "text/xml"}
JSON_SCHEMA_MEDIA_TYPES = {"application/json", "application/schema+json"}

# The words a check may earn. Only OK and NONE are compatible with a package
# being reported as conforming; NOT_RUN never is, because a check the lint
# could not perform is not a check that passed.
OK = "ok"
FAIL = "FAIL"
NOT_RUN = "not run"
NONE = "nothing to check"


class Check:
    """One of the six, and whether it ran.

    `fails` is deliberately not the same question as `status != OK`. A check
    that found nothing of its kind in the package (NONE) has not failed: an
    adapter with no expected graph has nothing for check 6 to disbelieve. A
    check the lint could not perform (NOT_RUN) fails the run -- unless the
    reason is that the package is outside what the lint reads today rather than
    that this machine is missing a tool, which is `benign`. Either way the word
    is printed, because the distinction between "passed" and "was not asked" is
    the whole point.
    """

    def __init__(self, number, title):
        self.number = number
        self.title = title
        self.status = NOT_RUN
        self.note = "the check did not report"
        self.benign = False

    def set(self, status, note, benign=False):
        self.status = status
        self.note = note
        self.benign = benign
        return self

    @property
    def fails(self):
        if self.status in (OK, NONE):
            return False
        if self.status == NOT_RUN and self.benign:
            return False
        return True


def report(ok, line):
    print(("  ok    " if ok else "  FAIL  ") + line)


def note(line):
    print("  note  " + line)


def local_path(adapter, iri):
    """The file an entity IRI names, when it is one inside the package.

    Returns None for a remote entity: an https: IRI is a reference, and there
    are no committed bytes here to hold it to.
    """
    prefix = adapter.resolve().as_uri().rstrip("/") + "/"
    if not str(iri).startswith(prefix):
        return None
    return Path(url2pathname(urlparse(str(iri)).path))


def digest_of(path, algorithm):
    hasher = DIGEST_ALGORITHMS[algorithm]()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            hasher.update(block)
    return hasher.hexdigest()


# ============================================================================
# Check 1
# ============================================================================


def validate_crate(adapter, check):
    """Check 1: the package is a valid RO-Crate 1.2."""
    print("1. RO-Crate 1.2")
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
        return check.set(NOT_RUN, "rocrate-validator is not installed")
    ok = run.returncode == 0
    report(ok, f"{adapter}/ro-crate-metadata.json")
    if not ok:
        print(run.stdout.strip() or run.stderr.strip())
        return check.set(FAIL, "the crate is not a valid RO-Crate 1.2")
    return check.set(OK, "the crate is a valid RO-Crate 1.2")


# ============================================================================
# Loading, which every check after the first depends on
# ============================================================================


def load(adapter):
    """Load the crate and the test manifest it names as one graph.

    Returns the graph, the adapter's root-entity IRI, the manifest's IRI and
    the manifest's path.
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
    manifest_iri = manifests[0]
    manifest_file = Path(url2pathname(urlparse(str(manifest_iri)).path))
    if not manifest_file.is_file():
        raise SystemExit(
            f"  FAIL  the adapter's bridge:testManifest names {manifest_file}, "
            "which does not exist"
        )
    graph.parse(manifest_file, format="turtle", publicID=str(manifest_iri))

    return graph, root, manifest_iri, manifest_file


# ============================================================================
# Check 2
# ============================================================================


def validate_shapes(graph, root, manifest_file, check):
    """Check 2: the crate and the manifest conform to this repository's shapes."""
    print("2. SHACL, crate and test manifest as one graph")
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
        check.set(OK, "the crate and the test manifest conform")
    elif only_spec_pin and missing_spec_pin:
        report(False, SPEC_PIN_ONLY)
        print(
            "        The adapter's root entity carries no bridge:specPin: the\n"
            "        commit of this specification it is written against, a\n"
            "        SoftwareSourceCode entity in the crate with codeRepository\n"
            "        and version (the full SHA), the same shape as\n"
            "        bridge:vocabularyPin. Nothing else about the crate or the\n"
            "        test manifest is wrong. adapter/ro-crate-metadata.md."
        )
        check.set(FAIL, SPEC_PIN_ONLY)
    else:
        report(False, f"{len(violations)} violation(s)")
        if missing_spec_pin:
            print("        including a missing bridge:specPin")
        for path, message in violations:
            print(f"        {path or '-'}: {message}")
        check.set(FAIL, f"{len(violations)} shape violation(s)")

    for path, message in warnings:
        print(f"  warn  {path or '-'}: {message}")

    return check


# ============================================================================
# Check 3
# ============================================================================


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


def validate_inventory(adapter, graph, check):
    """Check 3: every git-tracked file is accounted for.

    Either the crate describes it and it declares an encodingFormat, or it is
    one of the four repository documents or a dotfile. This is the check that
    makes "an adapter is data" a measured property rather than a claim: a file
    nobody described is a file nobody reviewed.
    """
    print("3. File inventory")
    paths = tracked_files(adapter)
    if paths is None:
        report(
            False,
            f"{adapter} is not a git checkout, so the inventory cannot be taken",
        )
        return check.set(NOT_RUN, "the package is not a git checkout")

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
    summary = (
        f"{len(paths)} tracked, {described} described, "
        f"{len(paths) - described - len(undescribed)} allowlisted, "
        f"{len(undescribed)} neither"
    )
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
    return check.set(OK if ok else FAIL, summary)


# ============================================================================
# Check 4
# ============================================================================


def validate_digests(adapter, graph, check):
    """Check 4: every digest in the crate matches the file beside it.

    Two claims are recorded in a crate and they are not the same assertion
    (adapter/fixtures/README.md):

      * schema:sha256 is the *local* claim -- these bytes, here, now. It is
        computed over the committed bytes when the file is committed, so a
        mismatch says the crate's record is wrong about the file beside it:
        one of the two was changed and the other was not.
      * any other digest property carries the *publisher's* claim about the
        file at its source, copied from whatever the publisher published beside
        it. Recomputing it over the committed bytes therefore asks a different
        question, and a mismatch says the local copy has drifted from the
        source it claims to be a byte-for-byte copy of.

    Both are recomputed the same way and reported in their own words. Nothing
    is fetched: the publisher's file is not on this machine, and a lint that
    needed the network would be a lint that cannot run offline or in a CI job
    without credentials. A digest on an entity that is not committed here --
    a referenced release, a pinned commit -- is recorded and not compared, and
    the run says how many.
    """
    print("4. Digests")
    local, publisher, remote = [], [], []
    for subject, predicate, value in graph:
        algorithm = str(predicate).rsplit("#", 1)[-1].rsplit("/", 1)[-1].lower()
        if algorithm not in DIGEST_ALGORITHMS:
            continue
        path = local_path(adapter, subject)
        if path is None:
            remote.append((subject, algorithm, str(value)))
        elif predicate == LOCAL_DIGEST:
            local.append((path, algorithm, str(value)))
        else:
            publisher.append((path, algorithm, str(value)))

    if not local and not publisher and not remote:
        report(True, "the crate records no digest")
        return check.set(NONE, "the crate records no digest")

    failures = 0
    for path, algorithm, declared in local:
        if not path.is_file():
            report(
                False,
                f"{path.name}: the crate records a {algorithm} for a file that "
                "is not there",
            )
            failures += 1
            continue
        actual = digest_of(path, algorithm)
        if actual != declared:
            failures += 1
            report(False, f"{path.name}: the crate's {algorithm} is not this file's")
            print(f"        crate      {declared}")
            print(f"        recomputed {actual}")
            print(
                "        This is the local claim, and it is wrong about the file\n"
                "        beside it: the file was changed without the crate, or the\n"
                "        crate without the file. Replace the file from its source\n"
                "        or correct the digest, in the same commit\n"
                "        (adapter/fixtures/README.md)."
            )

    for path, algorithm, declared in publisher:
        if not path.is_file():
            report(
                False,
                f"{path.name}: the crate records a publisher's {algorithm} for a "
                "file that is not there",
            )
            failures += 1
            continue
        actual = digest_of(path, algorithm)
        if actual != declared:
            failures += 1
            report(
                False, f"{path.name}: the publisher's {algorithm} is not this copy's"
            )
            print(f"        publisher  {declared}")
            print(f"        this copy  {actual}")
            print(
                "        A different finding from a wrong sha256. The publisher's\n"
                "        digest is the source's claim about its own file, so a\n"
                "        mismatch says this copy has drifted from the source it\n"
                "        claims to be byte for byte -- not that the crate has\n"
                "        miscounted the bytes on disk. Re-fetch from the source,\n"
                "        or record why the two differ."
            )

    if not failures:
        report(
            True,
            f"{len(local)} local sha256 and {len(publisher)} publisher digest(s) "
            "recomputed over the committed bytes",
        )
    if remote:
        note(
            f"{len(remote)} digest(s) on entities not committed here are "
            "recorded and not compared; the lint fetches nothing"
        )
    summary = (
        f"{len(local)} local, {len(publisher)} publisher, "
        f"{len(remote)} not committed"
    )
    return check.set(OK if not failures else FAIL, summary)


# ============================================================================
# The test manifest's entries, which checks 5 and 6 walk
# ============================================================================


def entries(graph, manifest_iri):
    """The tests in mf:entries, in the order the manifest lists them."""
    head = graph.value(manifest_iri, MF.entries)
    found = []
    while head is not None and head != RDF.nil:
        member = graph.value(head, RDF.first)
        if member is not None:
            found.append(member)
        head = graph.value(head, RDF.rest)
    return found


def test_name(graph, test):
    return str(graph.value(test, MF.name) or test)


def entity_name(iri):
    """The file name at the end of an entity IRI, for a message."""
    return Path(url2pathname(urlparse(str(iri)).path)).name or str(iri)


# ============================================================================
# Check 5
# ============================================================================


def schema_for(graph, root, envelope):
    """The schema an input arriving in this envelope is validated against.

    The envelope's own bridge:documentSchema where it declares one -- an
    envelope has one exactly when its document root is not the one the source
    schema declares -- and the adapter's bridge:sourceSchema where it does not.
    """
    document_schema = graph.value(envelope, BRIDGE.documentSchema)
    if document_schema is not None:
        return document_schema, "bridge:documentSchema"
    return graph.value(root, BRIDGE.sourceSchema), "bridge:sourceSchema"


def validate_inputs(adapter, graph, root, manifest_iri, check):
    """Check 5: every committed input validates against the declared schema.

    XSD 1.0 by lxml, which is what an XML source schema is written for. A
    source schema that is a JSON Schema is a real case this lint does not read
    yet: it is reported as not run, because reporting it as a pass would be a
    claim nobody made, and crashing on it would make the lint unusable for an
    adapter it has nothing against.
    """
    print("5. Inputs against the declared schema")

    tests = [
        (test, graph.value(test, MF.action))
        for test in entries(graph, manifest_iri)
    ]
    inputs = [
        (test, graph.value(action, BRIDGE.input), graph.value(action, BRIDGE.envelope))
        for test, action in tests
        if action is not None and graph.value(action, BRIDGE.input) is not None
    ]
    referenced = len(tests) - len(inputs)

    def referenced_note():
        if referenced:
            note(
                f"{referenced} test(s) name a referenced dataset rather than a "
                "committed input; those bytes are not here, and the Bridge that "
                "streams them validates them"
            )

    if not inputs:
        report(True, "the test manifest names no committed input")
        referenced_note()
        return check.set(NONE, "the test manifest names no committed input")

    try:
        from lxml import etree
    except ImportError:
        report(
            False,
            "lxml is not installed (pip install lxml), so no input was validated",
        )
        return check.set(NOT_RUN, "lxml is not installed")

    compiled = {}
    unreadable = {}

    def schema_engine(schema_iri):
        """An lxml XMLSchema for this schema entity, or why there is none.

        Returns (engine, reason, fatal). `fatal` separates the two ways a
        schema can yield no engine, which are not the same finding. A schema
        this lint does not read -- a JSON Schema, a schema referenced rather
        than committed -- is a gap in the lint, and the package is not accused
        of anything. A schema that is declared an XSD and will not compile as
        one is the package being wrong, and fails.
        """
        if schema_iri in compiled:
            return compiled[schema_iri], None, False
        if schema_iri in unreadable:
            return (None,) + unreadable[schema_iri]
        media_type = str(graph.value(schema_iri, SCHEMA.encodingFormat) or "")
        path = local_path(adapter, schema_iri)
        if path is None or not path.is_file():
            outcome = (
                f"{schema_iri} is not a file committed in this package, so there "
                "is nothing here to validate against",
                False,
            )
        elif media_type in JSON_SCHEMA_MEDIA_TYPES:
            outcome = (
                f"{path.name} is declared {media_type}: a JSON Schema source "
                "schema is outside what this lint reads today",
                False,
            )
        elif media_type not in XSD_MEDIA_TYPES:
            outcome = (
                f"{path.name} is declared {media_type or 'no media type'}, which "
                "names no schema language this lint reads",
                False,
            )
        else:
            try:
                compiled[schema_iri] = etree.XMLSchema(etree.parse(str(path)))
                return compiled[schema_iri], None, False
            except etree.Error as error:
                outcome = (
                    f"{path.name} is declared XML and does not compile as an "
                    f"XSD 1.0 schema: {error}",
                    True,
                )
        unreadable[schema_iri] = outcome
        return (None,) + outcome

    validated = 0
    failures = 0
    skipped = []
    for test, input_iri, envelope in inputs:
        name = test_name(graph, test)
        schema_iri, source = schema_for(graph, root, envelope)
        if schema_iri is None:
            failures += 1
            report(
                False,
                f"{name}: its envelope declares no bridge:documentSchema and the "
                "adapter declares no bridge:sourceSchema, so there is nothing to "
                "validate the input against",
            )
            continue
        input_path = local_path(adapter, input_iri)
        if input_path is None or not input_path.is_file():
            failures += 1
            report(
                False,
                f"{name}: bridge:input names {input_iri}, which is not a file in "
                "this package",
            )
            continue
        engine, reason, fatal = schema_engine(schema_iri)
        if engine is None:
            if fatal:
                failures += 1
                report(False, f"{name}: {reason}")
            else:
                skipped.append((name, reason))
            continue
        try:
            document = etree.parse(str(input_path))
        except etree.Error as error:
            failures += 1
            report(False, f"{name}: {input_path.name} is not well-formed XML")
            print(f"        {error}")
            continue
        if engine.validate(document):
            validated += 1
        else:
            failures += 1
            report(
                False,
                f"{name}: {input_path.name} does not validate against "
                f"{entity_name(schema_iri)}, the envelope's {source}",
            )
            for entry in engine.error_log:
                print(f"        line {entry.line}: {entry.message}")

    if not failures and not skipped:
        report(
            True,
            f"{validated} committed input(s) against the schema each test's "
            "envelope declares",
        )
    for name, reason in skipped:
        note(f"{name}: not validated -- {reason}")
    referenced_note()

    if failures:
        return check.set(FAIL, f"{failures} input(s) did not validate")
    if skipped and not validated:
        return check.set(
            NOT_RUN,
            f"no input was validated; {len(skipped)} outside what this lint reads",
            benign=True,
        )
    if skipped:
        return check.set(
            OK,
            f"{validated} validated, {len(skipped)} outside what this lint reads",
        )
    return check.set(OK, f"{validated} input(s) validated")


# ============================================================================
# Check 6
# ============================================================================


def validate_expected_graphs(adapter, graph, manifest_iri, check):
    """Check 6: every expected graph parses as Turtle.

    Parsing, and nothing else. Whether an expected graph conforms to Cascade's
    shapes is a question for a Bridge's validate stage, asked of the graph a
    mapping actually produced; asking it here would report a fixture as wrong
    for recording something Cascade has no term for yet, which is what the
    findings sidecar beside it is for (adapter/validation.md, check 6).
    """
    print("6. Expected graphs")
    expected = []
    for test in entries(graph, manifest_iri):
        result = graph.value(test, MF.result)
        if result is None:
            continue
        turtle = graph.value(result, BRIDGE.graph)
        if turtle is not None:
            expected.append((test, turtle))

    if not expected:
        report(True, "the test manifest names no expected graph")
        note(
            "a manifest may legitimately name none: an input-only test records "
            "what a Bridge produced and judges nothing"
        )
        return check.set(NONE, "the test manifest names no expected graph")

    failures = 0
    triples = 0
    for test, turtle in expected:
        name = test_name(graph, test)
        path = local_path(adapter, turtle)
        if path is None or not path.is_file():
            failures += 1
            report(
                False,
                f"{name}: bridge:graph names {turtle}, which is not a file in "
                "this package",
            )
            continue
        try:
            parsed = Graph()
            parsed.parse(path, format="turtle", publicID=str(turtle))
        except Exception as error:  # rdflib raises several unrelated parser types
            failures += 1
            report(False, f"{name}: {path.name} does not parse as Turtle")
            print(f"        {error}")
            continue
        triples += len(parsed)

    if not failures:
        report(
            True,
            f"{len(expected)} expected graph(s) parse as Turtle, "
            f"{triples} triples in all",
        )
    note(
        "parsed, not judged. An expected graph is not validated against "
        "Cascade's shapes here: that is a Bridge's validate stage, and a pass "
        "above says the file is Turtle and nothing more"
    )
    return check.set(
        OK if not failures else FAIL,
        f"{len(expected) - failures} of {len(expected)} parsed",
    )


# ============================================================================
# The specification pin, and the tier line
# ============================================================================


def check_spec_pin(graph, root, spec_revision):
    """The crate's bridge:specPin and the revision being run must agree.

    The `uses:` pin in an adapter's workflow and the bridge:specPin in its
    crate are the same fact written twice, one for the machine and one for the
    reader (pinning.md). This is where they are held to it.
    """
    print("Specification pin")
    pins = list(graph.objects(root, BRIDGE.specPin))
    if not pins:
        report(False, "no bridge:specPin to compare; the shapes named it above")
        return False, "absent"
    pin = pins[0]
    version = graph.value(pin, SCHEMA.version)
    repository = graph.value(pin, SCHEMA.codeRepository)
    print(f"  read  {pin}")
    if version is None:
        report(False, f"{pin} carries no schema:version, so there is no SHA to compare")
        return False, "no SHA to compare"
    if repository is None:
        report(
            False,
            f"{pin} carries no schema:codeRepository, so the pin does not say "
            "which repository holds that commit",
        )
        return False, "no repository named"
    if spec_revision is None:
        note(
            "the revision of this specification being run was not given "
            "(--spec-revision), so the pin is reported and not compared"
        )
        return True, "reported, not compared"
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
            "        (pinning.md)."
        )
    return ok, ("agrees with the ref this lint was called at" if ok else "disagrees")


def tier_line(graph, root, inventory_ok):
    """The one derived fact the lint reports, in the words adapter/validation.md
    fixes. Candidate, never universal: a lint sees one package on one machine,
    and a tier is measured by running an adapter's fixtures on every published
    Bridge."""
    profiles = sorted(
        str(p).rsplit("#", 1)[-1] for p in graph.objects(root, BRIDGE.profileRequired)
    )
    if not inventory_ok:
        return "tier: not computed, because the file inventory did not pass"
    if profiles:
        return "limited: requires " + ", ".join(profiles)
    return "universal candidate"


# ============================================================================


def summarise(checks, pin_ok, pin_note):
    """All six, each with the word it earned.

    The summary exists because the failure this lint is written against is a
    check that quietly did nothing. "ok" and "nothing to check" are different
    sentences and are printed as different sentences.
    """
    print("The six checks of adapter/validation.md, and how each ended:")
    width = max(len(check.title) for check in checks)
    for check in checks:
        print(
            f"  {check.number}  {check.title.ljust(width)}  "
            f"{check.status:<16}  {check.note}"
        )
    print(
        f"  -  {'the specification pin'.ljust(width)}  "
        f"{('ok' if pin_ok else FAIL):<16}  {pin_note}"
    )
    not_run = [c for c in checks if c.status == NOT_RUN]
    nothing = [c for c in checks if c.status == NONE]
    if not_run:
        print(
            "  A check reported `not run` did not happen. Nothing above claims "
            "this package passed it."
        )
    if nothing:
        print(
            "  A check reported `nothing to check` ran and found nothing of its "
            "kind in this package, which is not the same as passing."
        )


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

    checks = [
        Check(1, "the package is a valid RO-Crate 1.2"),
        Check(2, "the crate and the test manifest conform to the shapes"),
        Check(3, "every git-tracked file is accounted for"),
        Check(4, "every digest matches its file"),
        Check(5, "every input validates against the declared schema"),
        Check(6, "every expected graph parses"),
    ]
    one, two, three, four, five, six = checks

    validate_crate(adapter, one)
    graph, root, manifest_iri, manifest_file = load(adapter)
    validate_shapes(graph, root, manifest_file, two)
    validate_inventory(adapter, graph, three)
    validate_digests(adapter, graph, four)
    validate_inputs(adapter, graph, root, manifest_iri, five)
    validate_expected_graphs(adapter, graph, manifest_iri, six)
    pin_ok, pin_note = check_spec_pin(graph, root, args.spec_revision)

    print()
    summarise(checks, pin_ok, pin_note)
    print()
    print(tier_line(graph, root, three.status == OK))
    print()
    ok = pin_ok and not any(check.fails for check in checks)
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
