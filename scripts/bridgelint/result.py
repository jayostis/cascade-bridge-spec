"""What a check decides, with nothing about how it is printed.

A check returns one of these and prints nothing. That is the whole reason this
module exists: a check that printed its own verdict could only be observed by
running the lint and reading its output, which is why the end-to-end suite used
to be the only suite there was. A `Result` can be asserted on in a test that
takes microseconds.

`report.py` is the only module that knows what any of this looks like on a
terminal.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# The four words a check may earn. Only OK and NONE are compatible with a
# package being reported as conforming; NOT_RUN never is, because a check the
# lint could not perform is not a check that passed.
OK = "ok"
FAIL = "FAIL"
NOT_RUN = "not run"
NONE = "nothing to check"


@dataclass
class Entry:
    """One line of a check's report, and the detail indented beneath it.

    `kind` is the word in the margin: ok, FAIL, note, warn or read. `detail`
    holds plain lines; the indentation is the renderer's business.
    """

    kind: str
    text: str
    detail: tuple[str, ...] = ()


@dataclass
class Result:
    """A check's verdict: the word it earned, its one-line note, its report."""

    status: str
    note: str
    entries: list[Entry] = field(default_factory=list)
    benign: bool = False

    @property
    def fails(self) -> bool:
        """Whether this check should fail the run.

        Deliberately not the same question as `status != OK`. A check that
        found nothing of its kind in the package (NONE) has not failed: an
        adapter with no expected graph has nothing for check 6 to disbelieve. A
        check the lint could not perform (NOT_RUN) fails the run -- unless the
        reason is that the package is outside what the lint reads today rather
        than that this machine is missing a tool, which is `benign`.
        """
        if self.status in (OK, NONE):
            return False
        if self.status == NOT_RUN and self.benign:
            return False
        return True

    def says(self, kind: str, text: str, *detail: str) -> Result:
        self.entries.append(Entry(kind, text, tuple(detail)))
        return self

    def verdict(self, ok: bool, text: str, *detail: str) -> Result:
        return self.says(OK if ok else FAIL, text, *detail)


def passed(note: str) -> Result:
    return Result(OK, note)


def failed(note: str) -> Result:
    return Result(FAIL, note)


def nothing_to_check(note: str) -> Result:
    return Result(NONE, note)


def not_run(note: str, benign: bool = False) -> Result:
    return Result(NOT_RUN, note, benign=benign)
