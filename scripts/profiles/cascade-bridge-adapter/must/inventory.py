"""Every git-tracked file is a crate entity with a declared media type, or one
of the documents that describe the repository rather than the package.

This is the requirement that makes "an adapter is data" a measured property
rather than a claim: a file nobody described is a file nobody reviewed, and the
allowed set of media types, which the shapes hold, is where "no code" is
enforced.
"""

import subprocess

from bridgelint.crate import from_context
from bridgelint.terms import ALLOWLIST, SCHEMA
from rdflib import URIRef
from rocrate_validator.models import ValidationContext
from rocrate_validator.requirements.python import PyFunctionCheck, check, requirement


def tracked_files(adapter):
    """Every file git tracks in the adapter's checkout, as relative paths.

    git, not a directory walk: a walk sees build output, a virtual environment
    and whatever the last run left behind, and an inventory that counts those
    is an inventory nobody can keep green. None when it is not a checkout.
    """
    run_git = subprocess.run(
        ["git", "-C", str(adapter), "ls-files", "-z"],
        capture_output=True,
        text=True,
    )
    if run_git.returncode != 0:
        return None
    return sorted(p for p in run_git.stdout.split("\0") if p)


def unaccounted(crate):
    """Every file the crate accounts for nowhere, as a message each."""
    paths = tracked_files(crate.adapter)
    if paths is None:
        yield (
            f"{crate.adapter} is not a git checkout, so the inventory cannot be "
            "taken and nothing here says this package is only data"
        )
        return
    for path in paths:
        if path in ALLOWLIST or path.split("/", 1)[0].startswith("."):
            continue
        entity = URIRef((crate.adapter / path).resolve().as_uri())
        if crate.graph.value(entity, SCHEMA.encodingFormat) is None:
            yield (
                f"{path}: no crate entity with a declared encodingFormat, and "
                "not one of README.md, LICENSE, CHANGELOG.md, CLAUDE.md, "
                "ro-crate-metadata.json or a dotfile"
            )


@requirement(name="File inventory")
class Inventory(PyFunctionCheck):
    """Every git-tracked file is described by the crate, or is one of the
    documents that describe the repository rather than the package."""

    @check(name="every git-tracked file is accounted for")
    def run_check(self, context: ValidationContext) -> bool:
        found = False
        for message in unaccounted(from_context(context)):
            context.result.add_issue(message, self)
            found = True
        return not found
