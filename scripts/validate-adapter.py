#!/usr/bin/env python3
"""Validate a Cascade Bridge Adapter package against this specification.

The checks are an RO-Crate profile, scripts/profiles/cascade-bridge-adapter,
which declares itself a profile of RO-Crate 1.2. So one pass validates the
package as an RO-Crate and as an adapter, and every requirement -- theirs and
this specification's -- is reported the same way, at the same severity, by the
same tool. This script is the front end: it runs that profile and prints what it
found.

What each requirement is, and what a failure means, is adapter/validation.md and
the module that implements it under scripts/bridgelint/checks/.

A requirement is met, or it is not, and a run fails on any unmet requirement.
A check that could not run -- a missing tool -- reports an unmet requirement
rather than silence, because a lint that silently checks nothing is worse than
no lint. A check that ran and found nothing of its kind in the package reports
nothing: an adapter whose manifest holds only input-only tests has broken no
rule.

This script is what .github/actions/validate-adapter runs, and the starter hands
over to that action from a checkout of this repository at the adapter's own
bridge:specPin, so an adapter's CI is the starter's one line rather than a copy
of this file. It takes a directory. It knows no adapter's name, no adapter's
repository and no format id, and it must stay that way: a specification that
knows which adapters exist is the bug pinning.md is written against.

Nothing here runs a mapping or compares a graph, and nothing an adapter names is
fetched: digests are recomputed over the committed bytes.

Usage:

    python3 scripts/validate-adapter.py <path to an adapter checkout>

Requires pyshacl, rdflib, roc-validator and lxml.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

PROFILES = Path(__file__).resolve().parent / "profiles"
PROFILE = "cascade-bridge-adapter"
SPEC_ROOT = Path(__file__).resolve().parent.parent


def ours(check):
    """Whether a check comes from this specification's profile."""
    return getattr(check.requirement.profile, "token", None) == PROFILE


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

    from bridgelint.checks.quiet import quieten
    from rocrate_validator import services
    from rocrate_validator.models import ValidationSettings

    quieten()
    print(f"Adapter: {adapter}")
    print(f"Spec:    {SPEC_ROOT}")
    print()

    result = services.validate(
        ValidationSettings(
            rocrate_uri=str(adapter),
            extra_profiles_path=str(PROFILES),
            profile_identifier=PROFILE,
        )
    )

    issues = list(result.get_issues())
    unmet = {issue.check.identifier for issue in issues}

    mine = sorted(
        (c for c in result.executed_checks if ours(c)),
        key=lambda c: c.identifier,
    )
    inherited = [c for c in result.executed_checks if not ours(c)]

    print("The Cascade Bridge Adapter requirements, and how each ended:")
    width = max((len(c.requirement.name) for c in mine), default=0)
    for check in mine:
        word = "FAIL" if check.identifier in unmet else "ok"
        print(f"  {word:<6}{check.requirement.name.ljust(width)}  {check.name}")
    failed_inherited = sum(1 for c in inherited if c.identifier in unmet)
    print(
        f"  {'FAIL' if failed_inherited else 'ok':<6}"
        f"{'RO-Crate 1.2'.ljust(width)}  "
        f"{len(inherited)} inherited requirement(s), {failed_inherited} unmet"
    )

    for issue in issues:
        print()
        head, *rest = issue.message.splitlines()
        print(f"  {issue.check.requirement.name}: {head}")
        for line in rest:
            print(f"        {line}")

    print()
    print("PASS" if result.passed() else "FAIL")
    return 0 if result.passed() else 1


if __name__ == "__main__":
    sys.exit(main())
