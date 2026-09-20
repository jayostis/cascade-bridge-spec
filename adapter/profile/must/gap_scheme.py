import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rocrate_validator.models import ValidationContext
from rocrate_validator.requirements.python import PyFunctionCheck, check, requirement

from _findings import report_findings


def faulty(crate):
    return iter(())


@requirement(name="Gap scheme")
class GapScheme(PyFunctionCheck):
    """An adapter naming a findings query names one gap scheme, and every gap in it carries a label, its scheme and one kind."""

    @check(name="the adapter names one gap scheme and every gap in it is whole")
    def run_check(self, context: ValidationContext) -> bool:
        return report_findings(self, context, faulty)
