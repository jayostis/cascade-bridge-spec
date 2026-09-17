#!/usr/bin/env python3
"""Usage:

    python3 scripts/compatibility.py validate <dir>
    python3 scripts/compatibility.py resolve  <dir> [--mode ci|local] [--results <dir>]
    python3 scripts/compatibility.py checkout <dir> [--mode ci|local] [--results <dir>]
    python3 scripts/compatibility.py run      <dir> [--results <dir>]
    python3 scripts/compatibility.py judge   [<dir>] [--results <dir>] [--summary <file>]
    python3 scripts/compatibility.py ready    <dir>
    python3 scripts/compatibility.py spec-pin <dir> [--output <file>]

Exit status is 1 when the subcommand fails or did not run, 0 otherwise.
Requires git; validate also needs pyshacl and rdflib, and judge rdflib.
"""

import sys

from compatibility_tool.cli import main

if __name__ == "__main__":
    sys.exit(main(__doc__))
