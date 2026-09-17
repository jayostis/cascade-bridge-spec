#!/usr/bin/env python3
"""Usage: engine.py [--canned passed|failed|partial|none|garbled] test <adapter directory> --earl <file>"""

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
    "partial": {"example-0001": "passed"},
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--canned", choices=("passed", "failed", "partial", "none", "garbled"), default="passed")
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
        ASSERTION.format(manifest=manifest, test=test, outcome=outcome) for test, outcome in CANNED[args.canned].items()
    )
    args.earl.write_text(body, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
