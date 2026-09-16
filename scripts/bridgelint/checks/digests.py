"""Check 4: every digest in the crate matches the file beside it.

Two claims are recorded in a crate and they are not the same assertion
(adapter/fixtures/README.md):

  * schema:sha256 is the *local* claim -- these bytes, here, now. A mismatch
    says the crate's record is wrong about the file beside it: one of the two
    was changed and the other was not.
  * any other digest property carries the *publisher's* claim about the file at
    its source. Recomputing it over the committed bytes asks a different
    question, and a mismatch says the local copy has drifted from the source it
    claims to be a byte-for-byte copy of.

Both are recomputed the same way and reported in their own words. Nothing is
fetched: the publisher's digest is already in the crate, which is the point of
recording it.
"""

from __future__ import annotations

from ..result import failed, nothing_to_check, passed
from ..terms import DIGEST_ALGORITHMS, LOCAL_DIGEST, digest_of

HEADING = "4. Digests"
TITLE = "every digest matches its file"


def _sort(crate):
    """Every digest in the crate, split by which claim it is."""
    local, publisher, remote = [], [], []
    for subject, predicate, value in crate.graph:
        algorithm = str(predicate).rsplit("#", 1)[-1].rsplit("/", 1)[-1].lower()
        if algorithm not in DIGEST_ALGORITHMS:
            continue
        path = crate.path_of(subject)
        if path is None:
            remote.append((subject, algorithm, str(value)))
        elif predicate == LOCAL_DIGEST:
            local.append((path, algorithm, str(value)))
        else:
            publisher.append((path, algorithm, str(value)))
    return local, publisher, remote


def run(crate):
    local, publisher, remote = _sort(crate)
    if not local and not publisher and not remote:
        return nothing_to_check("the crate records no digest").verdict(
            True, "the crate records no digest"
        )

    entries = []
    failures = 0

    for path, algorithm, declared in local:
        if not path.is_file():
            failures += 1
            entries.append(
                (
                    False,
                    f"{path.name}: the crate records a {algorithm} for a file "
                    "that is not there",
                    (),
                )
            )
            continue
        actual = digest_of(path, algorithm)
        if actual != declared:
            failures += 1
            entries.append(
                (
                    False,
                    f"{path.name}: the crate's {algorithm} is not this file's",
                    (
                        f"crate      {declared}",
                        f"recomputed {actual}",
                        "This is the local claim, and it is wrong about the file",
                        "beside it: the file was changed without the crate, or the",
                        "crate without the file. Replace the file from its source",
                        "or correct the digest, in the same commit",
                        "(adapter/fixtures/README.md).",
                    ),
                )
            )

    for path, algorithm, declared in publisher:
        if not path.is_file():
            failures += 1
            entries.append(
                (
                    False,
                    f"{path.name}: the crate records a publisher's {algorithm} "
                    "for a file that is not there",
                    (),
                )
            )
            continue
        actual = digest_of(path, algorithm)
        if actual != declared:
            failures += 1
            entries.append(
                (
                    False,
                    f"{path.name}: the publisher's {algorithm} is not this copy's",
                    (
                        f"publisher  {declared}",
                        f"this copy  {actual}",
                        "A different finding from a wrong sha256. The publisher's",
                        "digest is the source's claim about its own file, so a",
                        "mismatch says this copy has drifted from the source it",
                        "claims to be byte for byte -- not that the crate has",
                        "miscounted the bytes on disk. Re-fetch from the source,",
                        "or record why the two differ.",
                    ),
                )
            )

    note = (
        f"{len(local)} local, {len(publisher)} publisher, "
        f"{len(remote)} not committed"
    )
    result = (passed if not failures else failed)(note)
    if not failures:
        result.verdict(
            True,
            f"{len(local)} local sha256 and {len(publisher)} publisher "
            "digest(s) recomputed over the committed bytes",
        )
    for ok, text, detail in entries:
        result.verdict(ok, text, *detail)
    if remote:
        result.says(
            "note",
            f"{len(remote)} digest(s) on entities not committed here are "
            "recorded and not compared; the lint fetches nothing",
        )
    return result
