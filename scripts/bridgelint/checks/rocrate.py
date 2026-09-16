"""Check 1: the package is a valid RO-Crate 1.2."""

from __future__ import annotations

import atexit
import logging
from contextlib import contextmanager

from ..result import failed, not_run, passed

HEADING = "1. RO-Crate 1.2"
TITLE = "the package is a valid RO-Crate 1.2"


def run(adapter):
    """Validate the crate through the library, not the rocrate-validator command.

    The library hands back failed requirements as objects, where the command
    would have to write a JSON report for this to read back, and it saves that
    command's startup on every run.
    """
    try:
        from rocrate_validator import services
        from rocrate_validator.models import ValidationSettings
    except ImportError:
        return not_run("roc-validator is not installed").verdict(
            False, "roc-validator is not installed (pip install roc-validator)"
        )

    _quieten_validator_log()
    with _rdflib_quiet():
        validation = services.validate(
            ValidationSettings(
                rocrate_uri=str(adapter),
                profile_identifier="ro-crate-1.2",
            )
        )
    if validation.passed():
        return passed("the crate is a valid RO-Crate 1.2").verdict(
            True, f"{adapter}/ro-crate-metadata.json"
        )
    return failed("the crate is not a valid RO-Crate 1.2").verdict(
        False,
        f"{adapter}/ro-crate-metadata.json",
        *(describe(issue) for issue in validation.get_issues()),
    )


def describe(issue):
    """One failed requirement: its identifier, what it wanted, and what it found."""
    found = issue.check
    requirement = getattr(found, "requirement", None)
    entity = issue.violatingEntity
    return (
        f"{getattr(found, 'identifier', '?')} "
        f"{getattr(requirement, 'name', '')}: {issue.message}"
        + (f" [{entity}]" if entity else "")
    )


@contextmanager
def _rdflib_quiet():
    """Silence rdflib's term warnings for the duration of the validator's run.

    The validator hands rdflib the crate's location as it was given -- on
    Windows a path with backslashes, which is not a URI -- and rdflib logs a
    warning per entity. Dozens of them land on stderr, interleaved with this
    lint's own report. Scoped to this call: a warning rdflib raises about a
    graph this lint parsed itself is one worth seeing.
    """
    logger = logging.getLogger("rdflib.term")
    was = logger.level
    logger.setLevel(logging.ERROR)
    try:
        yield
    finally:
        logger.setLevel(was)


def _quieten_validator_log():
    """Stop the validator printing a captured log dump when the process exits.

    It registers an atexit hook that renders anything it logged, which lands
    after this lint's own report and, on a console whose code page cannot hold
    the box characters it draws with, raises inside the hook. Every failed
    requirement is reported above, so the dump adds nothing.
    """
    try:
        from rocrate_validator.utils import log as validator_log

        atexit.unregister(validator_log.__print_logs_on_exit__)
    except (ImportError, AttributeError):
        pass
