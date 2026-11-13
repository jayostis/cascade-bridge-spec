import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import re

from rdflib.namespace import RDF, SKOS
from rocrate_validator.models import ValidationContext
from rocrate_validator.requirements.python import PyFunctionCheck, check, requirement

from _accounting import accounting_of
from _crate import file_name_of
from _findings import report_findings
from _terms import BRIDGE

AN_ID = re.compile(r"[0-9]+(\.[0-9]+)+")


def in_words(label):
    return bool(label.strip()) and not AN_ID.fullmatch(label.strip())


def faulty(crate):
    accounting = accounting_of(crate)
    ids = sorted({str(term) for term in accounting.objects(None, BRIDGE.inSourceRecordType) if AN_ID.fullmatch(term)})
    if not ids:
        return
    file = file_name_of(crate.graph.value(crate.root, BRIDGE.sourceAccounting))
    for source_type in ids:
        concepts = [
            concept
            for concept in accounting.subjects(RDF.type, SKOS.Concept)
            if source_type in map(str, accounting.objects(concept, SKOS.notation))
        ]
        labels = [str(label) for concept in concepts for label in accounting.objects(concept, SKOS.prefLabel)]
        if len(concepts) != 1 or len(labels) != 1 or not in_words(labels[0]):
            yield (
                f"{source_type} is the bridge:inSourceRecordType of an entry, where an id names its record type in "
                f'words: a skos:Concept of {file} whose skos:notation is "{source_type}" and which carries one '
                "skos:prefLabel, a name that is not itself an id"
            )


@requirement(name="Record type names")
class RecordTypeNames(PyFunctionCheck):
    """A record type an accounting names by an id is named in words in the same accounting."""

    @check(name="every id a bridge:inSourceRecordType names is the notation of a concept with one name in words")
    def run_check(self, context: ValidationContext) -> bool:
        return report_findings(self, context, faulty)
