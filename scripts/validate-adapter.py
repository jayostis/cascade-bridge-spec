#!/usr/bin/env python3
"""Validate a Cascade Bridge Adapter package against this specification.

The requirements are an RO-Crate profile,
scripts/profiles/cascade-bridge-adapter, which declares itself a profile of
RO-Crate 1.2, so one pass validates a package as an RO-Crate and as an adapter.
What each requirement is, and why, is the file that implements it under that
profile's must/, one per requirement.

This writes no report of its own. It runs rocrate-validator, which writes one as
JSON, and prints the issues in it -- because the validator's own text output
names the requirements that failed only when it can page, and CI cannot.

A requirement is met or it is not, and a run fails on any unmet requirement. A
requirement nothing could check -- a missing tool -- is unmet rather than
silent, because a lint that silently checks nothing is worse than no lint. A
requirement that found nothing of its kind in the package reports nothing: an
adapter whose manifest holds only input-only tests has broken no rule.

This script is what .github/actions/validate-adapter runs, and the starter hands
over to that action from a checkout of this repository at the adapter's own
bridge:specPin. It takes a directory. It knows no adapter's name, no adapter's
repository and no format id, and it must stay that way: a specification that
knows which adapters exist is the bug pinning.md is written against.

Usage:

    python3 scripts/validate-adapter.py <path to an adapter checkout>

Requires pyshacl, rdflib, roc-validator and lxml.
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
PROFILES = SCRIPTS / "profiles"
PROFILE = "cascade-bridge-adapter"


def validate(adapter, report):
    """Run the validator over this specification's profile, writing `report`.

    PYTHONPATH carries scripts/ because the profile's requirements import what
    they share, and they run in the validator's process rather than this one.
    """
    environment = dict(os.environ)
    environment["PYTHONPATH"] = (
        str(SCRIPTS) + os.pathsep + environment.get("PYTHONPATH", "")
    )
    return subprocess.run(
        [
            "rocrate-validator",
            "validate",
            str(adapter),
            "--extra-profiles-path",
            str(PROFILES),
            "--profile-identifier",
            PROFILE,
            "--no-paging",
            "--output-format",
            "json",
            "--output-file",
            str(report),
        ],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        env=environment,
    )


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

    with tempfile.TemporaryDirectory() as scratch:
        path = Path(scratch) / "report.json"
        try:
            run = validate(adapter, path)
        except FileNotFoundError:
            raise SystemExit(
                "  FAIL  rocrate-validator is not installed "
                "(pip install roc-validator)"
            ) from None
        try:
            report = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            print((run.stdout or "").strip() or (run.stderr or "").strip())
            raise SystemExit(
                "  FAIL  the validator wrote no report this could read"
            ) from None

    statistics = report.get("statistics", {})
    print(f"Adapter: {adapter}")
    print(
        f"{statistics.get('total_passed_requirements', '?')} of "
        f"{statistics.get('total_requirements', '?')} requirements met, "
        "RO-Crate 1.2's and this specification's."
    )

    for issue in report.get("issues", []):
        print()
        head, *rest = str(issue.get("message", "")).splitlines()
        print(f"  {issue.get('severity', '?')}  {head}")
        for line in rest:
            print(f"        {line}")

    print()
    passed = bool(report.get("passed"))
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
