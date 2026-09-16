"""Turning results into the report a person reads.

The humble half of the lint: it makes no decisions, so nothing here needs a
test of its own beyond the end-to-end cases that prove a report still renders.
Every word in the margin is fixed by adapter/validation.md.
"""

from __future__ import annotations

from .result import FAIL, NONE, NOT_RUN

MARGIN = {
    "ok": "  ok    ",
    "FAIL": "  FAIL  ",
    "note": "  note  ",
    "warn": "  warn  ",
    "read": "  read  ",
}
INDENT = " " * 8


def render(heading, result):
    """One check: its heading, then every line it reported. Returns the result,
    so a caller can print it and keep it in one step."""
    print(heading)
    for entry in result.entries:
        print(MARGIN[entry.kind] + entry.text)
        for line in entry.detail:
            print(INDENT + line)
    return result


def summarise(checks, pin):
    """Every check, each with the word it earned.

    This exists because the failure the lint is written against is a check that
    quietly did nothing. `ok` and `nothing to check` are different sentences and
    are printed as different sentences.
    """
    print(f"The {len(checks)} checks of adapter/validation.md, and how each ended:")
    width = max(len(title) for _, title, _ in checks)
    for number, title, result in checks:
        print(f"  {number}  {title.ljust(width)}  {result.status:<16}  {result.note}")
    print(
        f"  -  {'the specification pin'.ljust(width)}  "
        f"{pin.status:<16}  {pin.note}"
    )
    if any(result.status == NOT_RUN for _, _, result in checks):
        print(
            "  A check reported `not run` did not happen. Nothing above claims "
            "this package passed it."
        )
    if any(result.status == NONE for _, _, result in checks):
        print(
            "  A check reported `nothing to check` ran and found nothing of its "
            "kind in this package, which is not the same as passing."
        )
