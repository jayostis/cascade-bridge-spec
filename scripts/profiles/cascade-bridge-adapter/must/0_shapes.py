"""The crate and its test manifest, as one graph, conform to the Cascade Bridge shapes."""

from rocrate_validator.models import ValidationContext
from rocrate_validator.requirements.python import PyFunctionCheck, check, requirement


@requirement(name="Cascade Bridge shapes")
class Shapes(PyFunctionCheck):
    """The crate and its test manifest, as one graph, conform to the Cascade Bridge shapes."""

    @check(name="the crate and the test manifest conform to the shapes")
    def run_check(self, context: ValidationContext) -> bool:
        from bridgelint import profile
        from bridgelint.checks import shapes

        return profile.report(shapes.run(profile.crate_for(context)), context, self)
