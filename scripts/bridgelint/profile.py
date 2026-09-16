"""What a profile requirement needs to call a check and report what it found.

The checks themselves are unchanged: each is still `run(crate) -> Result` under
`checks/`, with its own unit tests. This is the thin part that hands a Result to
rocrate-validator as issues, so that the lint's checks and RO-Crate 1.2's own
run in one pass and are reported the same way.
"""

from __future__ import annotations

from pathlib import Path

from . import crate as crate_module
from .result import FAIL, NOT_RUN

_loaded: dict[Path, object] = {}


def adapter_path(context):
    """The directory the crate lives in, as a path a check can read files from."""
    uri = context.settings.rocrate_uri
    for candidate in (getattr(uri, "path", None), str(uri)):
        if not candidate:
            continue
        text = str(candidate)
        if text.startswith("file://"):
            text = text.removeprefix("file://").lstrip("/")
        path = Path(text)
        if path.is_dir():
            return path.resolve()
    raise FileNotFoundError(f"cannot read {uri} as a directory")


def crate_for(context):
    """The crate and manifest as one graph, parsed once per package per run."""
    path = adapter_path(context)
    if path not in _loaded:
        _loaded[path] = crate_module.load(path)
    return _loaded[path]


def report(result, context, check):
    """Add an issue for everything the check found, and say whether it held.

    A check that could not run adds an issue too, unless the reason is that the
    package is outside what this lint reads rather than that a tool is missing:
    a required check that did not happen is a failure, and reporting it as
    silence is the thing this lint exists to prevent.

    A check that ran and found nothing of its kind adds nothing. It is not a
    failure and there is nothing for the author to do: an adapter whose manifest
    holds only input-only tests has broken no rule.
    """
    if result.status == FAIL:
        for entry in result.entries:
            if entry.kind != FAIL:
                continue
            # Newlines, not a joined line: these carry what to do about it, and
            # run together they are a wall nobody reads. The front end indents
            # every line after the first.
            context.result.add_issue(
                "\n".join((entry.text, *entry.detail)), check
            )
        return False
    if result.status == NOT_RUN and not result.benign:
        context.result.add_issue(
            f"this check did not run, so nothing here says the package passes "
            f"it: {result.note}",
            check,
        )
        return False
    return True
