#!/usr/bin/env python3
"""End-to-end cases for scripts/validate-adapter.py.

What only a whole run can show: that the profile loads at all, that the
requirements this specification adds run beside the ones RO-Crate 1.2 brings,
that the report renders, and that the exit status is right. Everything about
what a single check *decides* is in unittest-lint.py, which asserts on the
Result each check returns and takes a fraction of the time.

The subject is fixtures/synthetic-adapter, copied into a temporary directory
and broken there. **Nothing here mutates a tracked file**, no mutated copy is
ever written inside the repository, and no real adapter is read, cloned or
named.

Cases run concurrently: each is an independent RO-Crate validation costing
seconds, and they share nothing.

Run:  python3 scripts/selftest-lint.py            every case
      python3 scripts/selftest-lint.py rocrate    the ones whose names hold it
"""

from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
import sys
import tempfile
from concurrent import futures
from pathlib import Path

SPEC_ROOT = Path(__file__).resolve().parent.parent
LINT = SPEC_ROOT / "scripts" / "validate-adapter.py"
PACKAGE = SPEC_ROOT / "fixtures" / "synthetic-adapter"

CRATE = "ro-crate-metadata.json"
MANIFEST = "fixtures/manifest.ttl"
EXPECTED = "fixtures/expected/example-0001.ttl"

MAX_WORKERS = 16


class SelfTestFailure(AssertionError):
    pass


def stage(directory):
    """A copy of the fixture package in a fresh git checkout."""
    package = Path(directory) / "package"
    shutil.copytree(PACKAGE, package)
    return package


def track(package):
    subprocess.run(
        ["git", "init", "-q", str(package)], check=True, capture_output=True
    )
    subprocess.run(
        ["git", "-C", str(package), "add", "-A"], check=True, capture_output=True
    )


def edit(package, relative, old, new):
    """Replace `old` with `new` in one file, insisting it occurred exactly once.

    A mutation that silently matched nothing is a test that asserts nothing.
    """
    path = package / relative
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SelfTestFailure(
            f"{relative}: the mutation anchor occurs {text.count(old)} times, "
            f"once was expected: {old!r}"
        )
    path.write_text(text.replace(old, new), encoding="utf-8", newline="")


def restate_digest(package, relative):
    """Rewrite the crate's sha256 and contentSize for a file just mutated.

    Without this the digest requirement fails too, and a case that fails for
    two reasons demonstrates neither.
    """
    data = (package / relative).read_bytes()
    crate = package / CRATE
    text = crate.read_text(encoding="utf-8")
    start = text.index(f'"@id": "{relative}",')
    end = text.index("\n    }", start)
    head, entity, tail = text[:start], text[start:end], text[end:]
    entity = re.sub(
        r'"sha256": "[0-9a-f]{64}"',
        f'"sha256": "{hashlib.sha256(data).hexdigest()}"',
        entity,
    )
    entity = re.sub(r'"contentSize": "\d+"', f'"contentSize": "{len(data)}"', entity)
    crate.write_text(head + entity + tail, encoding="utf-8", newline="")


# ---------------------------------------------------------------------------
# The mutations
# ---------------------------------------------------------------------------


def undeclared_context_key(package):
    """RO-Crate 1.2's rule, not JSON-LD's: every key of a compacted descriptor
    must be present in the @context. JSON-LD expands bridge:specPin from the
    prefix alone, so the graph is unchanged and the shapes still pass. Only the
    inherited RO-Crate requirements see it."""
    edit(package, CRATE, '      "bridge:specPin": "bridge:specPin",\n', "")


def profile_not_an_entity(package):
    """What conformsTo names is not described as a Profile."""
    edit(
        package,
        CRATE,
        '      "@type": ["CreativeWork", "Profile"],',
        '      "@type": "CreativeWork",',
    )


def pin_not_a_data_entity(package):
    """RO-Crate reads a SoftwareSourceCode as a script, and a script has to be
    a data entity."""
    edit(
        package,
        CRATE,
        '      "@type": ["SoftwareSourceCode", "File"],\n'
        '      "name": "cascade-bridge-spec at 0af0fc9",',
        '      "@type": "SoftwareSourceCode",\n'
        '      "name": "cascade-bridge-spec at 0af0fc9",',
    )


def expected_graph_not_turtle(package):
    edit(package, EXPECTED, "@prefix ex:", "@prefixx ex:")
    restate_digest(package, EXPECTED)


def no_expected_graphs(package):
    """The one conversion test becomes an input-only test, which judges nothing.

    A conforming package: the shapes accept it, and the expected-graph
    requirement has nothing of its kind to look at. It must not fail the run.
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
    restate_digest(package, MANIFEST)


# ---------------------------------------------------------------------------
# The cases
# ---------------------------------------------------------------------------

CASES = [
    {
        "name": "green: the fixture package as committed",
        "mutate": None,
        "exit": 0,
        "expect": [
            "ok    Cascade Bridge shapes",
            "ok    Digests",
            "ok    Queries",
            "inherited requirement(s), 0 unmet",
            "PASS",
        ],
    },
    {
        "name": "a Cascade requirement unmet: an expected graph that is not Turtle",
        "mutate": expected_graph_not_turtle,
        "exit": 1,
        "expect": [
            "FAIL  Expected graphs",
            "example-0001.ttl does not parse as Turtle",
            "FAIL",
        ],
        "forbid": ["FAIL  Digests"],
    },
    {
        "name": "nothing of its kind is not a failure: no expected graphs",
        "mutate": no_expected_graphs,
        "exit": 0,
        "expect": ["ok    Expected graphs", "PASS"],
    },
    {
        "name": "rocrate: a bridge: key the @context does not declare",
        "mutate": undeclared_context_key,
        "exit": 1,
        "expect": [
            "FAIL  RO-Crate 1.2",
            "is not allowed in the compacted format because it is not present "
            "in the @context",
        ],
        "forbid": ["FAIL  Cascade Bridge shapes"],
    },
    {
        "name": "rocrate: what conformsTo names is not typed Profile",
        "mutate": profile_not_an_entity,
        "exit": 1,
        "expect": ["FAIL  RO-Crate 1.2", "MUST reference Profile entities"],
    },
    {
        "name": "rocrate: a pin typed SoftwareSourceCode and not File",
        "mutate": pin_not_a_data_entity,
        "exit": 1,
        "expect": ["FAIL  RO-Crate 1.2", "MUST include `File` in its `@type`"],
    },
]


# ---------------------------------------------------------------------------


def run_case(case):
    """One case, in a directory of its own. Returns its failures and its output."""
    failures = []
    with tempfile.TemporaryDirectory() as directory:
        package = stage(directory)
        if case["mutate"]:
            case["mutate"](package)
        track(package)
        run = subprocess.run(
            [sys.executable, str(LINT), str(package)],
            capture_output=True,
            text=True,
        )
        output = run.stdout + run.stderr

        if run.returncode != case["exit"]:
            failures.append(f"exit status {run.returncode}, {case['exit']} expected")
        for fragment in case["expect"]:
            if fragment not in output:
                failures.append(f"the run does not say: {fragment}")
        for fragment in case.get("forbid", ()):
            if fragment in output:
                failures.append(f"the run says what it must not: {fragment}")
    return failures, output


def select(argv):
    chosen = [
        case
        for case in CASES
        if all(term.lower() in case["name"].lower() for term in argv)
    ]
    if argv and not chosen:
        raise SystemExit(f"  FAIL  no case matches {' '.join(argv)}")
    return chosen


def main(argv=()):
    if not PACKAGE.is_dir():
        raise SystemExit(f"  FAIL  {PACKAGE} is not there")
    cases = select(list(argv))
    print(f"Lint:    {LINT}")
    print(f"Subject: {PACKAGE}")
    print()

    with futures.ThreadPoolExecutor(
        max_workers=min(MAX_WORKERS, max(1, len(cases)))
    ) as pool:
        results = list(pool.map(run_case, cases))

    failed = 0
    for case, (case_failures, output) in zip(cases, results):
        if case_failures:
            failed += 1
            print(f"  FAIL  {case['name']}")
            for failure in case_failures:
                print(f"        {failure}")
            print(output)
        else:
            print(f"  ok    {case['name']}")

    print()
    print(f"{len(cases)} case(s): {len(cases) - failed} as specified, {failed} not")
    if len(cases) != len(CASES):
        print(f"{len(CASES) - len(cases)} case(s) not run: this is a filtered run")
    print("PASS" if not failed else "FAIL")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
