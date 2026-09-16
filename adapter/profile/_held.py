"""The one thing every requirement does with what it found."""

from __future__ import annotations


def held(check, context, messages):
    """Add an issue for each message, and say whether the requirement held.

    A requirement reports by yielding messages and nothing else, so what counts
    as unmet is the same question for all of them: did it yield anything.
    """
    unmet = False
    for message in messages:
        context.result.add_issue(message, check)
        unmet = True
    return not unmet
