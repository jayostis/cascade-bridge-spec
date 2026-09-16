#!/usr/bin/env python3
"""Validate a Cascade Bridge Adapter package against this specification.

The checks adapter/validation.md names, in the order it names them, so that the
cheapest check that can fail comes first and each later check may assume the
earlier ones held. What each check is, and what a failure means, is that
document and the module that implements it, one per check under
scripts/bridgelint/checks/.

**Every check says whether it ran.** A check whose tool is absent, and a check
that found nothing of its kind in the package, are each reported in their own
words and never as a pass: a lint that silently checks nothing is worse than no
lint. The summary at the end lists every check with the word it earned.

Nothing here runs a mapping or compares a graph, and nothing an adapter names is
fetched: check 4 recomputes digests over the committed bytes. The tools it runs
do use the network, starting with the RO-Crate context the crate names.

This script is what .github/actions/validate-adapter runs, and the starter hands
over to that action from a checkout of this repository at the adapter's own
bridge:specPin, so an adapter's CI is the starter's one line rather than a copy
of this file. It takes a directory. It knows no adapter's name, no adapter's
repository and no format id, and it must stay that way: a specification that
knows which adapters exist is the bug pinning.md is written against.

Usage:

    python3 scripts/validate-adapter.py <path to an adapter checkout>

Exit status is 0 when the run passes and 1 when it fails; adapter/validation.md
says which words fail it.

Requires pyshacl, rdflib, roc-validator and lxml (pip install pyshacl rdflib
roc-validator lxml).
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from bridgelint import crate as crate_module  # noqa: E402
from bridgelint import report  # noqa: E402
from bridgelint.checks import (  # noqa: E402
    digests,
    graphs,
    inputs,
    inventory,
    queries,
    rocrate,
    shapes,
    specpin,
)
from bridgelint.terms import SPEC_ROOT  # noqa: E402


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

    print(f"Adapter: {adapter}")
    print(f"Spec:    {SPEC_ROOT}")
    print()

    # Check 1 runs before the crate is loaded: an invalid RO-Crate is the
    # cheapest thing that can be wrong, and loading it here would raise before
    # the report could say so.
    results = [(1, rocrate.TITLE, report.render(rocrate.HEADING, rocrate.run(adapter)))]

    crate = crate_module.load(adapter)
    for number, module in enumerate(
        (shapes, inventory, digests, inputs, graphs, queries), start=2
    ):
        results.append(
            (number, module.TITLE, report.render(module.HEADING, module.run(crate)))
        )
    pin = report.render(specpin.HEADING, specpin.run(crate))

    print()
    report.summarise(results, pin)
    print()
    ok = not pin.fails and not any(result.fails for _, _, result in results)
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
