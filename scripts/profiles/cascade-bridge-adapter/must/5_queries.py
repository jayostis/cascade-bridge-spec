"""Every query the adapter names parses as SPARQL 1.1 and has the form its property declares."""

from rocrate_validator.models import ValidationContext
from rocrate_validator.requirements.python import PyFunctionCheck, check, requirement


@requirement(name="Queries")
class Queries(PyFunctionCheck):
    """Every query the adapter names parses as SPARQL 1.1 and has the form its property declares."""

    @check(name="every query parses in its declared form")
    def run_check(self, context: ValidationContext) -> bool:
        from bridgelint import profile
        from bridgelint.checks import queries

        return profile.report(queries.run(profile.crate_for(context)), context, self)
