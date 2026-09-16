"""Every digest the crate records matches the file beside it.

A crate records two kinds of claim and they are not the same assertion
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
recording it, and a digest on bytes that are not committed here is recorded and
not compared.
"""

from bridgelint.crate import from_context
from bridgelint.terms import DIGEST_ALGORITHMS, LOCAL_DIGEST, digest_of
from rocrate_validator.models import ValidationContext
from rocrate_validator.requirements.python import PyFunctionCheck, check, requirement

LOCAL_ADVICE = (
    "This is the local claim, and it is wrong about the file beside it: the "
    "file was changed without the crate, or the crate without the file. "
    "Replace the file from its source or correct the digest, in the same "
    "commit (adapter/fixtures/README.md)."
)

PUBLISHER_ADVICE = (
    "A different finding from a wrong sha256. The publisher's digest is the "
    "source's claim about its own file, so a mismatch says this copy has "
    "drifted from the source it claims to be byte for byte -- not that the "
    "crate has miscounted the bytes on disk. Re-fetch from the source, or "
    "record why the two differ."
)


def claims(crate):
    """Every digest in the crate that names committed bytes, and whose claim
    it is. A digest on an entity committed nowhere here is not yielded: it is
    recorded and not compared, which is why nothing is fetched."""
    for subject, predicate, value in crate.graph:
        algorithm = str(predicate).rsplit("#", 1)[-1].rsplit("/", 1)[-1].lower()
        if algorithm not in DIGEST_ALGORITHMS:
            continue
        path = crate.path_of(subject)
        if path is not None:
            yield path, algorithm, str(value), predicate == LOCAL_DIGEST


def mismatches(crate):
    """Every digest that does not describe its file, as a message each."""
    for path, algorithm, declared, is_local in claims(crate):
        whose = "crate's" if is_local else "publisher's"
        if not path.is_file():
            yield (
                f"{path.name}: the crate records a {whose} {algorithm} for a "
                "file that is not there"
            )
            continue
        actual = digest_of(path, algorithm)
        if actual == declared:
            continue
        if is_local:
            yield (
                f"{path.name}: the crate's {algorithm} is not this file's\n"
                f"crate      {declared}\n"
                f"recomputed {actual}\n" + LOCAL_ADVICE
            )
        else:
            yield (
                f"{path.name}: the publisher's {algorithm} is not this copy's\n"
                f"publisher  {declared}\n"
                f"this copy  {actual}\n" + PUBLISHER_ADVICE
            )


@requirement(name="Digests")
class Digests(PyFunctionCheck):
    """Every digest the crate records is recomputed over the committed bytes,
    the local claim and the publisher's claim reported as the different
    assertions they are."""

    @check(name="every digest matches its file")
    def run_check(self, context: ValidationContext) -> bool:
        found = False
        for message in mismatches(from_context(context)):
            context.result.add_issue(message, self)
            found = True
        return not found
