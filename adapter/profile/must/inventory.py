import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import subprocess

from _findings import report_findings
from _terms import SCHEMA
from rdflib import URIRef
from rocrate_validator.models import ValidationContext
from rocrate_validator.requirements.python import PyFunctionCheck, check, requirement

FILES_THE_CRATE_NEED_NOT_DESCRIBE = ("README.md", "LICENSE", "CHANGELOG.md", "CLAUDE.md", "ro-crate-metadata.json")


def git_tracked_files(adapter):
    run_git = subprocess.run(["git", "-C", str(adapter), "ls-files", "-z"], capture_output=True, text=True)
    if run_git.returncode != 0:
        return None
    return sorted(p for p in run_git.stdout.split("\0") if p)


def unaccounted(crate):
    paths = git_tracked_files(crate.adapter)
    if paths is None:
        yield f"{crate.adapter} is not a git checkout, so the inventory cannot be taken"
        return
    for path in paths:
        if path in FILES_THE_CRATE_NEED_NOT_DESCRIBE or path.split("/", 1)[0].startswith("."):
            continue
        entity = URIRef((crate.adapter / path).resolve().as_uri())
        if crate.graph.value(entity, SCHEMA.encodingFormat) is None:
            yield (
                f"{path}: no crate entity with a declared encodingFormat, and "
                f"not one of {', '.join(FILES_THE_CRATE_NEED_NOT_DESCRIBE)} or a dotfile"
            )


@requirement(name="File inventory")
class Inventory(PyFunctionCheck):
    """Every git-tracked file is described by the crate, or describes the repository."""

    @check(name="every git-tracked file is accounted for")
    def run_check(self, context: ValidationContext) -> bool:
        return report_findings(self, context, unaccounted)
