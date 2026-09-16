#!/usr/bin/env python3
"""End-to-end cases: the adapter profile, run by rocrate-validator.

What only a whole run shows: that the profile loads, that its requirements run
beside RO-Crate 1.2's, and that the report and the exit status agree. The
subject is fixtures/synthetic-adapter, copied to a temporary directory and
broken there.

Run:  python3 scripts/selftest-lint.py            every case
      python3 scripts/selftest-lint.py rocrate    the ones whose names hold it
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from concurrent import futures
from pathlib import Path

SPEC_ROOT = Path(__file__).resolve().parent.parent
PROFILES = SPEC_ROOT / "adapter"
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


def identifier_not_a_format_id(package):
    edit(package, CRATE, '"identifier": "synthetic-example",', '"identifier": "Synthetic_Example",')


def expected_graph_not_turtle(package):
    edit(package, EXPECTED, "@prefix ex:", "@prefixx ex:")
    restate_digest(package, EXPECTED)


def manifest_not_turtle(package):
    edit(package, MANIFEST, "@prefix mf:", "@prefixx mf:")
    restate_digest(package, MANIFEST)


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
        "expect": [],
    },
    {
        "name": "a Cascade shape unmet: an adapter identifier that is not a format id",
        "mutate": identifier_not_a_format_id,
        "exit": 1,
        "expect": ["The adapter carries exactly one identifier, the format id"],
    },
    {
        "name": "a Cascade requirement unmet: an expected graph that is not Turtle",
        "mutate": expected_graph_not_turtle,
        "exit": 1,
        "expect": ["example-0001: example-0001.ttl does not parse as Turtle"],
        "forbid": ["sha256 is not this file's"],
    },
    {
        "name": "a requirement that could not run is unmet: a manifest that is not Turtle",
        "mutate": manifest_not_turtle,
        "exit": 1,
        "expect": ["could not be checked", "manifest.ttl"],
    },
    {
        "name": "nothing of its kind is not a failure: no expected graphs",
        "mutate": no_expected_graphs,
        "exit": 0,
        "expect": [],
    },
    {
        "name": "rocrate: a bridge: key the @context does not declare",
        "mutate": undeclared_context_key,
        "exit": 1,
        "expect": [
            "is not allowed in the compacted format because it is not present "
            "in the @context",
        ],
        "forbid": ["conform to the shapes"],
    },
    {
        "name": "rocrate: what conformsTo names is not typed Profile",
        "mutate": profile_not_an_entity,
        "exit": 1,
        "expect": ["MUST reference Profile entities"],
    },
    {
        "name": "rocrate: a pin typed SoftwareSourceCode and not File",
        "mutate": pin_not_a_data_entity,
        "exit": 1,
        "expect": ["MUST include `File` in its `@type`"],
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
        report = Path(directory) / "report.json"
        run = subprocess.run(
            [
                "rocrate-validator", "validate", str(package),
                "--extra-profiles-path", str(PROFILES),
                "--profile-identifier", "cascade-bridge-adapter",
                "--no-paging", "--output-format", "json",
                "--output-file", str(report),
            ],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            # The validator logs through rich, which a Windows console code
            # page cannot encode.
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
        output = run.stdout + run.stderr
        if not report.is_file():
            failures.append("the validator wrote no report")
        else:
            issues = json.loads(report.read_text(encoding="utf-8"))["issues"]
            output += "\n".join(str(issue["message"]) for issue in issues)

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
    print(f"Profile: {PROFILES / 'profile'}")
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
