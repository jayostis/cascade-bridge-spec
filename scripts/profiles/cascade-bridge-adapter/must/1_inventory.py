"""Every git-tracked file is a crate entity with a declared media type, or one of the documents that describe the repository rather than the package."""

from rocrate_validator.models import ValidationContext
from rocrate_validator.requirements.python import PyFunctionCheck, check, requirement


@requirement(name="File inventory")
class Inventory(PyFunctionCheck):
    """Every git-tracked file is a crate entity with a declared media type, or one of the documents that describe the repository rather than the package."""

    @check(name="every git-tracked file is accounted for")
    def run_check(self, context: ValidationContext) -> bool:
        from bridgelint import profile
        from bridgelint.checks import inventory

        return profile.report(inventory.run(profile.crate_for(context)), context, self)
