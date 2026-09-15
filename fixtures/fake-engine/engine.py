#!/usr/bin/env python3
"""A fake engine: the command contract of engine/command.md, and nothing else.

    engine.py [--canned passed|failed|none|garbled] test <adapter directory> --earl <file>

It runs nothing. It checks it was handed an adapter package, prints the
directory, and writes an EARL report in Turtle whose outcomes are canned, for
the three entries of fixtures/synthetic-adapter's test manifest. --canned says
which report:

    passed   example-0001 passed, example-0002 cantTell, the dataset untested,
             which holds: none is earl:failed or earl:inapplicable
    failed   example-0001 failed, which does not hold
    none     no report at all, which does not hold
    garbled  a file that is not Turtle, which does not hold

Its exit status is 0 whatever it reports, because compatibility.md relies on
the report and never on an engine's exit code; a fake that exited non-zero on
a failure would let a tool that read the exit code pass.

scripts/selftest-compatibility.py copies it into a throwaway repository and
names it in that repository's compatibility.json, with the running
interpreter as the command's first argument.
"""

import argparse
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
    "passed": {"example-0001": "passed", "example-0002": "cantTell", "example-release-2026-01": "untested"},
    "failed": {"example-0001": "failed", "example-0002": "cantTell", "example-release-2026-01": "untested"},
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--canned", choices=("passed", "failed", "none", "garbled"), default="passed")
    parser.add_argument("command", choices=("test",))
    parser.add_argument("adapter", type=Path)
    parser.add_argument("--earl", type=Path)
    parser.add_argument("--datasets", action="store_true")
    args = parser.parse_args()

    adapter = args.adapter.resolve()
    if not (adapter / "ro-crate-metadata.json").is_file():
        print(f"fake engine: {adapter} holds no ro-crate-metadata.json", file=sys.stderr)
        return 2
    print(f"fake engine: testing {adapter}, report canned {args.canned}")
    if args.earl is None or args.canned == "none":
        return 0
    if args.canned == "garbled":
        args.earl.write_text("this is not Turtle {\n", encoding="utf-8")
        return 0
    manifest = (adapter / "fixtures" / "manifest.ttl").as_uri()
    body = EARL + "".join(
        ASSERTION.format(manifest=manifest, test=test, outcome=outcome)
        for test, outcome in CANNED[args.canned].items()
    )
    args.earl.write_text(body, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
