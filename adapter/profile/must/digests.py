import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import hashlib

from _findings import report_findings
from _terms import SCHEMA
from rocrate_validator.models import ValidationContext
from rocrate_validator.requirements.python import PyFunctionCheck, check, requirement

ALGORITHMS = {
    "md5": hashlib.md5,
    "sha1": hashlib.sha1,
    "sha256": hashlib.sha256,
    "sha384": hashlib.sha384,
    "sha512": hashlib.sha512,
}
LOCAL_DIGEST = SCHEMA.sha256

LOCAL_ADVICE = (
    "This is the local claim, and it is wrong about the file beside it: the "
    "file was changed without the crate, or the crate without the file. "
    "Replace the file from its source or correct the digest, in the same commit."
)

PUBLISHER_ADVICE = (
    "A different finding from a wrong sha256: this copy has drifted from the "
    "source it claims to be byte for byte. Re-fetch from the source, or record "
    "why the two differ."
)


def digest_of(path, algorithm):
    hasher = ALGORITHMS[algorithm]()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            hasher.update(block)
    return hasher.hexdigest()


def claims(crate):
    for subject, predicate, value in crate.graph:
        algorithm = str(predicate).rsplit("#", 1)[-1].rsplit("/", 1)[-1].lower()
        if algorithm not in ALGORITHMS:
            continue
        path = crate.path_in_package(subject)
        if path is not None:
            yield path, algorithm, str(value), predicate == LOCAL_DIGEST


def mismatches(crate):
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
    """Every digest the crate records matches the file beside it."""

    @check(name="every digest matches its file")
    def run_check(self, context: ValidationContext) -> bool:
        return report_findings(self, context, mismatches)
