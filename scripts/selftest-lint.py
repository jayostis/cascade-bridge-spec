#!/usr/bin/env python3
"""Mutation tests for scripts/validate-adapter.py.

The question this file exists to answer is: *what would the lint report if the
thing it claims to check were wrong?* A lint nobody has seen fail is a lint
nobody should trust, and the failure mode it is written against -- a check that
quietly does nothing and reports a pass -- is invisible from a green run. So
every case here breaks one property of a conforming package and asserts that
the lint says so, in the words docs/adapter/validation.md fixes, and that it exits
non-zero; and the first case asserts that the same package, unbroken, passes.

The subject is fixtures/synthetic-adapter, this repository's own synthetic
adapter package. It is copied into a temporary directory and mutated there.
**Nothing here mutates a tracked file**, no mutated copy is ever written inside
the repository, and no real adapter is read, cloned or named: this repository
must not know that any adapter exists (docs/pinning.md), and a fixture it
wrote itself is a subject it owns.

The copy is made into a fresh `git init`, because check 3 takes its inventory
with `git ls-files` and a directory that is not a checkout is a directory it
must refuse rather than walk.

Two kinds of assertion are made about each case, and the second is the one that
makes this more than an exit-code test: the run's exit status, and the word the
summary gives each of the six checks. `ok`, `FAIL`, `not run` and
`nothing to check` are four different sentences, and a check that found nothing
of its kind in a package must never be reported in the same word as a check
that ran and passed.

Run:  python3 scripts/selftest-lint.py
"""

from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SPEC_ROOT = Path(__file__).resolve().parent.parent
LINT = SPEC_ROOT / "scripts" / "validate-adapter.py"
PACKAGE = SPEC_ROOT / "fixtures" / "synthetic-adapter"

CRATE = "ro-crate-metadata.json"
MANIFEST = "fixtures/manifest.ttl"
INPUT_SET = "fixtures/in/example-0001.xml"
INPUT_RECORD = "fixtures/in/example-0002.xml"
EXPECTED = "fixtures/expected/example-0001.ttl"

# The four words a check may earn, longest first so the summary line parser
# does not stop at the "not run" inside a longer phrase.
STATUS = ("nothing to check", "not run", "FAIL", "ok")
SUMMARY_LINE = re.compile(
    r"^\s{2}(?P<number>\d)\s\s(?P<title>.+?)\s\s+"
    r"(?P<status>" + "|".join(STATUS) + r")\s\s+(?P<note>.*)$"
)


class SelfTestFailure(AssertionError):
    pass


# ---------------------------------------------------------------------------
# Staging and mutating a copy
# ---------------------------------------------------------------------------


def stage(directory):
    """A copy of the fixture package in a fresh git checkout."""
    package = Path(directory) / "package"
    shutil.copytree(PACKAGE, package)
    subprocess.run(
        ["git", "init", "-q", str(package)], check=True, capture_output=True
    )
    subprocess.run(
        ["git", "-C", str(package), "add", "-A"], check=True, capture_output=True
    )
    return package


def edit(package, relative, old, new):
    """Replace `old` with `new` in one file, insisting it occurred exactly once.

    A mutation that silently matched nothing is a test that asserts nothing,
    which is the failure this whole file is written against.
    """
    path = package / relative
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SelfTestFailure(
            f"{relative}: the mutation anchor occurs {text.count(old)} times, "
            f"once was expected: {old!r}"
        )
    path.write_text(text.replace(old, new), encoding="utf-8", newline="")


def entity_block(text, relative):
    """The crate text of one file entity, and nothing that merely references it.

    The trailing comma is what tells an entity's own "@id" apart from the
    references to it in hasPart and isBasedOn, which carry none. Match without
    it and a mutation lands on the next entity in the file, which is a test
    asserting something nobody meant.
    """
    start = text.index(f'"@id": "{relative}",')
    return start, text.index("\n    }", start)


def declared_digest(package, relative, algorithm, digits):
    """The digest the crate records for a file, under one algorithm."""
    text = (package / CRATE).read_text(encoding="utf-8")
    start, end = entity_block(text, relative)
    found = re.search(
        r'"%s": "([0-9a-f]{%d})"' % (algorithm, digits), text[start:end]
    )
    if not found:
        raise SelfTestFailure(
            f"{relative}: the crate records no {algorithm}, so there is nothing "
            "to mutate"
        )
    return found.group(1)


def restate_digest(package, relative):
    """Rewrite the crate's sha256 and contentSize for a file just mutated.

    A mutated fixture would otherwise fail check 4 as well as the check the
    case is about, and a case that fails for two reasons demonstrates neither.
    """
    data = (package / relative).read_bytes()
    crate = package / CRATE
    text = crate.read_text(encoding="utf-8")
    block, end = entity_block(text, relative)
    head, entity, tail = text[:block], text[block:end], text[end:]
    entity = re.sub(
        r'"sha256": "[0-9a-f]{64}"',
        f'"sha256": "{hashlib.sha256(data).hexdigest()}"',
        entity,
    )
    entity = re.sub(
        r'"contentSize": "\d+"', f'"contentSize": "{len(data)}"', entity
    )
    crate.write_text(head + entity + tail, encoding="utf-8", newline="")


# ---------------------------------------------------------------------------
# The mutations, one per property
# ---------------------------------------------------------------------------


def flip_hex(digest):
    """One hex digit changed: a digest that is the right shape and wrong."""
    return ("f" if digest[0] != "f" else "0") + digest[1:]


def mutate_local_sha256(package):
    """Check 4: the crate's own sha256 no longer describes the file beside it."""
    digest = declared_digest(package, INPUT_SET, "sha256", 64)
    edit(package, CRATE, f'"sha256": "{digest}"', f'"sha256": "{flip_hex(digest)}"')


def mutate_publisher_md5(package):
    """Check 4: the publisher's digest and this copy of the file disagree.

    The realistic shape of it: the publisher republished the file, someone
    copied the new digest out of the `.md5` beside it and did not re-fetch the
    bytes. The local sha256 is untouched and still true, which is exactly why
    this must not be reported in the same words as a wrong sha256.
    """
    digest = declared_digest(package, INPUT_RECORD, "md5", 32)
    edit(package, CRATE, f'"md5": "{digest}"', f'"md5": "{flip_hex(digest)}"')


def mutate_input_against_schema(package):
    """Check 5: an input stops satisfying the schema its envelope declares."""
    edit(package, INPUT_SET, 'Version="3"', 'Version="third"')
    restate_digest(package, INPUT_SET)


def mutate_schema_language(package):
    """Check 5: the schemas are declared JSON, which this lint does not read.

    Not a broken package: an adapter whose source schema is a JSON Schema is a
    real adapter this lint has nothing against. It must say it did not run
    rather than crash, and must not report the inputs as validated.
    """
    edit(
        package,
        CRATE,
        '"name": "Example record XSD, pinned copy",\n      "encodingFormat": "application/xml"',
        '"name": "Example record XSD, pinned copy",\n      "encodingFormat": "application/json"',
    )
    edit(
        package,
        CRATE,
        '"name": "Example set XSD, this package\'s wrapper",\n      "encodingFormat": "application/xml"',
        '"name": "Example set XSD, this package\'s wrapper",\n      "encodingFormat": "application/json"',
    )


def mutate_expected_graph(package):
    """Check 6: an expected graph stops being Turtle."""
    edit(package, EXPECTED, 'rdfs:label "first synthetic record" .', 'rdfs:label "first synthetic record"')
    restate_digest(package, EXPECTED)


def mutate_away_expected_graphs(package):
    """Check 6: the manifest names no expected graph at all.

    The entry becomes an input-only test, which judges nothing and therefore
    carries no mf:result. A conforming package: the shapes accept it and check
    6 has nothing to look at. What it must not do is report that as a pass.
    """
    edit(
        package,
        MANIFEST,
        "<#example-0001> a bridge:IsomorphicConversionTest ;",
        "<#example-0001> a bridge:InputOnlyTest ;",
    )
    edit(
        package,
        MANIFEST,
        "  ] ;\n  mf:result [\n"
        "    bridge:graph <expected/example-0001.ttl> ;\n"
        "    bridge:findings <findings/example-0001.gaps.json>\n"
        "  ] .",
        "  ] .",
    )


def mutate_undescribed_file(package):
    """Check 3: a git-tracked file the crate describes nowhere."""
    (package / "mapping.xsl").write_text(
        "<!-- a file nobody described -->\n", encoding="utf-8", newline=""
    )
    subprocess.run(
        ["git", "-C", str(package), "add", "-A"], check=True, capture_output=True
    )


# ---------------------------------------------------------------------------
# The cases
# ---------------------------------------------------------------------------

CASES = [
    {
        "name": "green: the fixture package as committed",
        "mutate": None,
        "exit": 0,
        "statuses": {1: "ok", 2: "ok", 3: "ok", 4: "ok", 5: "ok", 6: "ok"},
        "expect": [
            "6 local sha256 and 2 publisher digest(s) recomputed",
            "2 committed input(s) against the schema each test's envelope declares",
            "1 expected graph(s) parse as Turtle",
            "universal candidate",
            "PASS",
        ],
    },
    {
        "name": "check 3: a git-tracked file the crate describes nowhere",
        "mutate": mutate_undescribed_file,
        "exit": 1,
        "statuses": {3: "FAIL"},
        "expect": [
            "mapping.xsl: no crate entity with a declared encodingFormat",
        ],
    },
    {
        "name": "check 4: the crate's sha256 is not the file's",
        "mutate": mutate_local_sha256,
        "exit": 1,
        "statuses": {4: "FAIL", 5: "ok", 6: "ok"},
        "expect": [
            "example-0001.xml: the crate's sha256 is not this file's",
            "This is the local claim, and it is wrong about the file",
        ],
    },
    {
        "name": "check 4: the publisher's md5 is not this copy's",
        "mutate": mutate_publisher_md5,
        "exit": 1,
        "statuses": {4: "FAIL"},
        "expect": [
            "example-0002.xml: the publisher's md5 is not this copy's",
            "this copy has drifted from the source it",
            "A different finding from a wrong sha256",
        ],
    },
    {
        "name": "check 5: an input does not satisfy its envelope's schema",
        "mutate": mutate_input_against_schema,
        "exit": 1,
        "statuses": {4: "ok", 5: "FAIL", 6: "ok"},
        "expect": [
            "example-0001: example-0001.xml does not validate against "
            "example-set.xsd, the envelope's bridge:documentSchema",
            "Version",
        ],
    },
    {
        "name": "check 5: a schema language this lint does not read",
        "mutate": mutate_schema_language,
        "exit": 0,
        "statuses": {5: "not run"},
        "expect": [
            "a JSON Schema source schema is outside what this lint reads today",
            "A check reported `not run` did not happen",
        ],
        "forbid": ["input(s) validated"],
    },
    {
        "name": "check 6: an expected graph that is not Turtle",
        "mutate": mutate_expected_graph,
        "exit": 1,
        "statuses": {4: "ok", 5: "ok", 6: "FAIL"},
        "expect": [
            "example-0001: example-0001.ttl does not parse as Turtle",
        ],
    },
    {
        "name": "check 6: a manifest that names no expected graph",
        "mutate": mutate_away_expected_graphs,
        "exit": 0,
        "statuses": {6: "nothing to check"},
        "expect": [
            "the test manifest names no expected graph",
            "A check reported `nothing to check` ran and found nothing of its kind",
        ],
        "forbid": ["expected graph(s) parse as Turtle"],
    },
]


# ---------------------------------------------------------------------------


def summary_statuses(output):
    """The word the summary gave each of the six checks."""
    found = {}
    for line in output.splitlines():
        match = SUMMARY_LINE.match(line)
        if match:
            found[int(match.group("number"))] = match.group("status")
    return found


def run_case(case):
    failures = []
    with tempfile.TemporaryDirectory() as directory:
        package = stage(directory)
        if case["mutate"]:
            case["mutate"](package)
        run = subprocess.run(
            [sys.executable, str(LINT), str(package)],
            capture_output=True,
            text=True,
        )
        output = run.stdout + run.stderr

        if run.returncode != case["exit"]:
            failures.append(
                f"exit status {run.returncode}, {case['exit']} expected"
            )
        statuses = summary_statuses(output)
        if len(statuses) != 6:
            failures.append(
                f"the summary reported {len(statuses)} of the six checks"
            )
        for number, expected in case["statuses"].items():
            if statuses.get(number) != expected:
                failures.append(
                    f"check {number} was reported `{statuses.get(number)}`, "
                    f"`{expected}` expected"
                )
        for fragment in case["expect"]:
            if fragment not in output:
                failures.append(f"the run does not say: {fragment}")
        for fragment in case.get("forbid", ()):
            if fragment in output:
                failures.append(f"the run says what it must not: {fragment}")

        if failures:
            print(output)
    return failures


def main():
    if not PACKAGE.is_dir():
        raise SystemExit(f"  FAIL  {PACKAGE} is not there")
    print(f"Lint:    {LINT}")
    print(f"Subject: {PACKAGE}")
    print()

    failed = 0
    for case in CASES:
        failures = run_case(case)
        if failures:
            failed += 1
            print(f"  FAIL  {case['name']}")
            for failure in failures:
                print(f"        {failure}")
        else:
            print(f"  ok    {case['name']}")

    print()
    print(
        f"{len(CASES)} case(s): {len(CASES) - failed} as specified, {failed} not"
    )
    print("PASS" if not failed else "FAIL")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
