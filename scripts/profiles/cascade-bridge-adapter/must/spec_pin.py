from bridgelint.requirement import held
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
    """bridge:specPin names a commit and the repository that holds it."""

    @check(name="the specification pin names a commit and its repository")
    def run_check(self, context: ValidationContext) -> bool:
        return held(self, context, faults(from_context(context)))
