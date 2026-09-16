"""Check 3: every git-tracked file is accounted for.

Either the crate describes it and it declares an encodingFormat, or it is one
of the four repository documents or a dotfile. This is the check that makes "an
adapter is data" a measured property rather than a claim: a file nobody
described is a file nobody reviewed, and the allowed set of media types, which
the shapes hold, is where "no code" is enforced.
"""

from __future__ import annotations

import subprocess

from rdflib import URIRef

from ..result import failed, not_run, passed
from ..terms import ALLOWLIST, SCHEMA

HEADING = "3. File inventory"
TITLE = "every git-tracked file is accounted for"


def tracked_files(adapter):
    """Every file git tracks in the adapter's checkout, as relative paths.

    git, not a directory walk: a walk sees build output, a virtual environment
    and whatever the last run left behind, and an inventory that counts those
    is an inventory nobody can keep green.
    """
    run_git = subprocess.run(
        ["git", "-C", str(adapter), "ls-files", "-z"],
        capture_output=True,
        text=True,
    )
    if run_git.returncode != 0:
        return None
    return sorted(p for p in run_git.stdout.split("\0") if p)


def run(crate):
    paths = tracked_files(crate.adapter)
    if paths is None:
        return not_run("the package is not a git checkout").verdict(
            False,
            f"{crate.adapter} is not a git checkout, so the inventory cannot "
            "be taken",
        )

    undescribed = []
    described = 0
    for path in paths:
        first = path.split("/", 1)[0]
        if path in ALLOWLIST or first.startswith("."):
            continue
        entity = URIRef((crate.adapter / path).resolve().as_uri())
        if crate.graph.value(entity, SCHEMA.encodingFormat) is not None:
            described += 1
        else:
            undescribed.append(path)

    allowlisted = len(paths) - described - len(undescribed)
    note = (
        f"{len(paths)} tracked, {described} described, "
        f"{allowlisted} allowlisted, {len(undescribed)} neither"
    )
    result = (passed if not undescribed else failed)(note)
    return result.verdict(
        not undescribed,
        f"{len(paths)} tracked file(s): {described} described by the crate, "
        f"{allowlisted} allowlisted, {len(undescribed)} neither",
        *(
            f"{path}: no crate entity with a declared encodingFormat, and not "
            "one of README.md, LICENSE, CHANGELOG.md, CLAUDE.md, "
            "ro-crate-metadata.json or a dotfile"
            for path in undescribed
        ),
    )
