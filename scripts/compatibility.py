#!/usr/bin/env python3
"""Usage:

    python3 scripts/compatibility.py <dir> [--check compatibility|ready-to-merge]
                                          [--results <dir>] [--spec-repository <url>]

compatibility: the adapter lint where the directory holds an adapter's crate,
then its compatibility.json's counterparts, each run and judged; in a runtime,
the repositories its cascade-runtime.json pins, handed to its conformance
command on each host, and its report judged; in a vocabulary, each runtime its
compatibility.json names, run so with the vocabulary in place of the one it
pins. ready-to-merge: the
merge gate. The version of every repository the run uses is picked when it
runs; in a local run every sibling is used as it is on disk.

Exit status is 1 when the check fails or did not run, 0 otherwise.
Requires git; the compatibility check also needs pyshacl, rdflib and
rocrate-validator.
"""

import sys

from compatibility_tool.cli import main

if __name__ == "__main__":
    sys.exit(main(__doc__))
