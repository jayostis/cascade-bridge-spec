"""The specification pin: the crate's bridge:specPin names a commit, and where.

Nothing is compared. The pin is written once, in the crate, and the starter
checks this repository out at that commit before the lint runs (pinning.md), so
the revision running is the pinned one by construction. What is left to check
is that the pin says which commit, and in which repository.
"""

from __future__ import annotations

from ..result import failed, passed
from ..terms import BRIDGE, SCHEMA

HEADING = "Specification pin"
TITLE = "the specification pin"


def run(crate):
    pins = list(crate.graph.objects(crate.root, BRIDGE.specPin))
    if not pins:
        return failed("absent").verdict(
            False, "no bridge:specPin to compare; the shapes named it above"
        )
    pin = pins[0]
    version = crate.graph.value(pin, SCHEMA.version)
    repository = crate.graph.value(pin, SCHEMA.codeRepository)

    if version is None:
        return (
            failed("no SHA to compare")
            .says("read", str(pin))
            .verdict(
                False,
                f"{pin} carries no schema:version, so there is no SHA to compare",
            )
        )
    if repository is None:
        return (
            failed("no repository named")
            .says("read", str(pin))
            .verdict(
                False,
                f"{pin} carries no schema:codeRepository, so the pin does not "
                "say which repository holds that commit",
            )
        )
    return (
        passed("names a commit and its repository")
        .says("read", str(pin))
        .verdict(True, f"bridge:specPin names {version}, in {repository}")
        .says(
            "note",
            "read, not compared: the starter runs this lint from that commit, "
            "and whether it is on the default branch is compatibility.py "
            "ready's question",
        )
    )
