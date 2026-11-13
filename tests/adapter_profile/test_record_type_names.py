import pytest
import record_type_names
from rdflib import URIRef

from _terms import BRIDGE
from adapter_profile_world import CARRIED, PREFIXES_OF_AN_ACCOUNTING

ACCOUNTING = "vocab/example-accounting.ttl"

AN_ALLERGY = "2.16.840.1.113883.10.20.22.4.7"
A_PROBLEM = "2.16.840.1.113883.10.20.22.4.4"

THE_ACCESSION = "/ExampleRecord/@Accession"
THE_VERSION = "/ExampleRecord/@Version"


def carried_in(source_type, path=THE_ACCESSION):
    return (
        f'[] a bridge:PathEntry ; bridge:sourcePath "{path}" ; bridge:verdict {CARRIED} ;\n'
        f"  bridge:carriedAs [ bridge:asProperty ex:accession ; bridge:inRecordClass ex:Record ;"
        f' bridge:inSourceRecordType "{source_type}" ] .\n'
    )


def named(source_type, *labels, notation=None):
    written = ["[] a skos:Concept", f'skos:notation "{notation or source_type}"']
    written += [f'skos:prefLabel "{label}"@en' for label in labels]
    return " ;\n  ".join(written) + " .\n"


def accounted(package, *statements):
    text = PREFIXES_OF_AN_ACCOUNTING + "@prefix skos: <http://www.w3.org/2004/02/skos/core#> .\n\n"
    return package.write(ACCOUNTING, text + "\n".join(statements))


def said_about(package):
    return "\n".join(record_type_names.faulty(package.crate))


def wanted(source_type):
    return (
        f"{source_type} is the bridge:inSourceRecordType of an entry, where an id names its record type in words: "
        f'a skos:Concept of example-accounting.ttl whose skos:notation is "{source_type}" and which carries '
        "one skos:prefLabel, a name that is not itself an id"
    )


class TestNamesOfASourcesKindsOfRecord:
    """Names of a source's kinds of record · adapter/profile/must/record_type_names.py

    A source that names a kind of record by an id, a C-CDA's templateId root among them, names it in words too, so a
    tool showing the adapter to a reader prints the name with the id beside it.
    """

    class TestGivenAnAccountingNamingKindsOfRecordByAnId:
        def test_reports_nothing_where_each_id_is_the_notation_of_a_concept_with_one_label(self, package):
            accounted(
                package,
                carried_in(AN_ALLERGY),
                carried_in(A_PROBLEM, THE_VERSION),
                named(AN_ALLERGY, "Allergy - Intolerance Observation"),
                named(A_PROBLEM, "Problem Observation"),
            )
            assert not said_about(package)

        def test_reports_an_id_no_concept_has_for_its_notation(self, package):
            accounted(package, carried_in(AN_ALLERGY), named(A_PROBLEM, "Problem Observation"))
            assert wanted(AN_ALLERGY) in said_about(package)

        def test_reports_each_id_with_no_name_and_no_other(self, package):
            accounted(
                package,
                carried_in(AN_ALLERGY),
                carried_in(A_PROBLEM, THE_VERSION),
                carried_in("2.16.840.1.113883.10.20.22.4.2", "/ExampleRecord/Label"),
                named(A_PROBLEM, "Problem Observation"),
            )
            said = said_about(package).splitlines()
            assert [line.split(" is the bridge:inSourceRecordType")[0] for line in said] == [
                "2.16.840.1.113883.10.20.22.4.2",
                AN_ALLERGY,
            ]

        def test_reports_an_id_once_however_many_entries_name_it(self, package):
            accounted(package, carried_in(AN_ALLERGY), carried_in(AN_ALLERGY, THE_VERSION))
            assert len(said_about(package).splitlines()) == 1

        def test_reports_a_concept_carrying_no_label(self, package):
            accounted(package, carried_in(AN_ALLERGY), named(AN_ALLERGY))
            assert wanted(AN_ALLERGY) in said_about(package)

        def test_reports_a_concept_carrying_two_labels(self, package):
            accounted(package, carried_in(AN_ALLERGY), named(AN_ALLERGY, "Allergy", "Intolerance"))
            assert wanted(AN_ALLERGY) in said_about(package)

        @pytest.mark.parametrize("label", [AN_ALLERGY, "4.7", "", "  "], ids=["the id", "an id", "empty", "blank"])
        def test_reports_a_label_that_is_no_name_in_words(self, package, label):
            accounted(package, carried_in(AN_ALLERGY), named(AN_ALLERGY, label))
            assert wanted(AN_ALLERGY) in said_about(package)

        def test_reports_a_label_given_to_an_id_that_differs_by_a_digit(self, package):
            accounted(package, carried_in(AN_ALLERGY), named(AN_ALLERGY, "Allergy", notation=AN_ALLERGY + "0"))
            assert wanted(AN_ALLERGY) in said_about(package)

    class TestGivenAnAccountingNamingKindsOfRecordByName:
        @pytest.mark.parametrize("source_type", ["Condition", "AllergyIntolerance", "ExampleRecord", "A1.2"])
        def test_reports_nothing_for_a_name_that_is_no_dotted_number(self, package, source_type):
            accounted(package, carried_in(source_type))
            assert not said_about(package)

        def test_reports_nothing_for_an_accounting_naming_no_kind_of_record(self, package):
            accounted(package)
            assert not said_about(package)

    class TestGivenAnAdapterNamingNoAccounting:
        def test_reports_nothing(self, crate):
            crate.graph.remove((crate.root, BRIDGE.sourceAccounting, None))
            assert not list(record_type_names.faulty(crate))

        def test_reports_nothing_for_an_accounting_that_is_not_a_file_in_the_package(self, crate):
            crate.graph.remove((crate.root, BRIDGE.sourceAccounting, None))
            crate.graph.add((crate.root, BRIDGE.sourceAccounting, URIRef("https://example.org/an-accounting.ttl")))
            assert not list(record_type_names.faulty(crate))

    class TestGivenTheSyntheticAdapters:
        @pytest.mark.parametrize("committed", ["crate", "json_crate"], ids=["the XML adapter", "the JSON adapter"])
        def test_reports_nothing_for_the_accounting_each_commits(self, request, committed):
            assert not list(record_type_names.faulty(request.getfixturevalue(committed)))
