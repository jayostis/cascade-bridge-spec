"""Every committed input validates against the schema its envelope declares."""

from rocrate_validator.models import ValidationContext
from rocrate_validator.requirements.python import PyFunctionCheck, check, requirement


@requirement(name="Inputs against the declared schema")
class Inputs(PyFunctionCheck):
    """Every committed input validates against the schema its envelope declares."""

    @check(name="every input validates against the declared schema")
    def run_check(self, context: ValidationContext) -> bool:
        from bridgelint import profile
        from bridgelint.checks import inputs

        return profile.report(inputs.run(profile.crate_for(context)), context, self)
