"""Two noises the validator makes in this process, and why each is silenced.

Neither is a decision, so neither belongs in a check.
"""

from __future__ import annotations

import atexit
import logging


def quieten():
    _quieten_rdflib_terms()
    _quieten_validator_log()


def _quieten_rdflib_terms():
    """rdflib warns per entity when handed a path that is not a URI.

    The validator passes the crate's location through as it was given -- on
    Windows a path with backslashes -- and rdflib logs a warning for each
    entity it builds from it. Dozens of them land on stderr, interleaved with
    this lint's own report.
    """
    logging.getLogger("rdflib.term").setLevel(logging.ERROR)


def _quieten_validator_log():
    """The validator renders a captured log dump when the process exits.

    It lands after this lint's report and, on a console whose code page cannot
    hold the box characters it draws with, raises inside the atexit hook. Every
    unmet requirement is reported above, so the dump adds nothing.
    """
    try:
        from rocrate_validator.utils import log as validator_log

        atexit.unregister(validator_log.__print_logs_on_exit__)
    except (ImportError, AttributeError):
        pass
