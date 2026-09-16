"""Every digest the crate records matches the file beside it, the local claim and the publisher's claim reported as the different assertions they are."""

from rocrate_validator.models import ValidationContext
from rocrate_validator.requirements.python import PyFunctionCheck, check, requirement


@requirement(name="Digests")
class Digests(PyFunctionCheck):
    """Every digest the crate records matches the file beside it, the local claim and the publisher's claim reported as the different assertions they are."""

    @check(name="every digest matches its file")
    def run_check(self, context: ValidationContext) -> bool:
        from bridgelint import profile
        from bridgelint.checks import digests

        return profile.report(digests.run(profile.crate_for(context)), context, self)
