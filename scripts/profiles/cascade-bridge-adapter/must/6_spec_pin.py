"""The crate's bridge:specPin names a commit and the repository that holds it."""

from rocrate_validator.models import ValidationContext
from rocrate_validator.requirements.python import PyFunctionCheck, check, requirement


@requirement(name="Specification pin")
class SpecPin(PyFunctionCheck):
    """The crate's bridge:specPin names a commit and the repository that holds it."""

    @check(name="the specification pin names a commit and its repository")
    def run_check(self, context: ValidationContext) -> bool:
        from bridgelint import profile
        from bridgelint.checks import specpin

        return profile.report(specpin.run(profile.crate_for(context)), context, self)
