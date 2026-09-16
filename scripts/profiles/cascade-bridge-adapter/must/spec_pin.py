"""The crate's bridge:specPin names a commit, and the repository that holds it.

Nothing is compared. The pin is written once, in the crate, and the starter
checks this repository out at that commit before the lint runs (pinning.md), so
the revision running is the pinned one by construction. What is left to check is
that the pin says which commit, and where. Whether that commit is on the default
branch is the merge gate's question, not this one's.
"""

from bridgelint.crate import from_context
from bridgelint.terms import BRIDGE, SCHEMA
from rocrate_validator.models import ValidationContext
from rocrate_validator.requirements.python import PyFunctionCheck, check, requirement


def faults(crate):
    """Everything wrong with the specification pin, as a message each."""
    pins = list(crate.graph.objects(crate.root, BRIDGE.specPin))
    if not pins:
        yield (
            "the crate carries no bridge:specPin, so it does not say which "
            "revision of this specification it is written against"
        )
        return
    pin = pins[0]
    if crate.graph.value(pin, SCHEMA.version) is None:
        yield f"{pin} carries no schema:version, so the pin names no commit"
    if crate.graph.value(pin, SCHEMA.codeRepository) is None:
        yield (
            f"{pin} carries no schema:codeRepository, so the pin does not say "
            "which repository holds that commit"
        )


@requirement(name="Specification pin")
class SpecPin(PyFunctionCheck):
    """The crate's bridge:specPin names a commit and the repository holding
    it."""

    @check(name="the specification pin names a commit and its repository")
    def run_check(self, context: ValidationContext) -> bool:
        found = False
        for message in faults(from_context(context)):
            context.result.add_issue(message, self)
            found = True
        return not found
