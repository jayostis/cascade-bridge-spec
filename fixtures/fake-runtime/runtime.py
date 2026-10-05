#!/usr/bin/env python3
import argparse
from pathlib import Path

EARL = """@prefix earl: <http://www.w3.org/ns/earl#> .

<https://example.org/fake-runtime> a earl:Software .
"""

ASSERTION = """
[] a earl:Assertion ;
  earl:assertedBy <https://example.org/fake-runtime> ;
  earl:subject <https://example.org/fake-runtime> ;
  earl:test <https://example.org/rule-vectors#{test}> ;
  earl:mode earl:automatic ;
  earl:result [ a earl:TestResult ; earl:outcome earl:{outcome} ] .
"""

CANNED = {
    "passed": {"rule-1": "passed", "rule-2": "passed"},
    "failed": {"rule-1": "passed", "rule-2": "failed"},
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--canned", choices=CANNED, default="passed")
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--folder", action="append", default=[])
    args = parser.parse_args()
    for pair in args.folder:
        repository, _, folder = pair.rpartition("=")
        if not Path(folder).is_dir():
            print(f"fake runtime: {folder}, handed in for {repository}, is no folder")
            return 2
        print(f"fake runtime: folder {repository} {folder}")
    body = EARL + "".join(ASSERTION.format(test=test, outcome=outcome) for test, outcome in CANNED[args.canned].items())
    args.report.write_text(body, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
