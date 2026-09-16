"""Every graph a test names as its expected result parses as Turtle. Parsing, not conforming."""

from rocrate_validator.models import ValidationContext
from rocrate_validator.requirements.python import PyFunctionCheck, check, requirement


@requirement(name="Expected graphs")
class ExpectedGraphs(PyFunctionCheck):
    """Every graph a test names as its expected result parses as Turtle. Parsing, not conforming."""

    @check(name="every expected graph parses as Turtle")
    def run_check(self, context: ValidationContext) -> bool:
        from bridgelint import profile
        from bridgelint.checks import graphs

        return profile.report(graphs.run(profile.crate_for(context)), context, self)
