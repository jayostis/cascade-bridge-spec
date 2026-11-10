import shutil

import pytest
from rdflib import Graph

import carried_as
from adapter_profile_world import CARRIED, CARRIED_IN_PART, NO_HOME, PREFIXES_OF_AN_ACCOUNTING, VOCABULARIES

ACCOUNTING = "vocab/example-accounting.ttl"
THE_VOCABULARY_FILE = "ontologies/example/v1/example.ttl"

A_VOCABULARY = """@prefix ex:   <https://example.org/synthetic-adapter/v1#> .
@prefix owl:  <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

<https://example.org/synthetic-adapter/v1#> a owl:Ontology .

ex:Record a owl:Class .
ex:Revision a owl:Class ; rdfs:subClassOf ex:Record .
ex:Note a owl:Class .
ex:Quantity a owl:Class .
ex:Dosage a owl:Class .

ex:accession a owl:DatatypeProperty ; rdfs:domain ex:Record .
ex:noteText a owl:DatatypeProperty ; rdfs:domain ex:Note .
ex:status a owl:DatatypeProperty ; rdfs:domain [ a owl:Class ; owl:unionOf ( ex:Note ex:Record ) ] .
ex:dosage a owl:ObjectProperty ; rdfs:domain ex:Record ; rdfs:range ex:Dosage .
ex:doseQuantity a owl:ObjectProperty ; rdfs:domain ex:Dosage ; rdfs:range ex:Quantity .
ex:unit a owl:DatatypeProperty ; rdfs:domain ex:Quantity .
ex:Unrelated a owl:Class .
rdfs:label a owl:AnnotationProperty .
"""

A_VOCABULARY_WITH_RECORD_CLASSES = """@prefix ex:   <https://example.org/synthetic-adapter/v1#> .
@prefix owl:  <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix sh:   <http://www.w3.org/ns/shacl#> .
@prefix prov: <http://www.w3.org/ns/prov#> .

ex:Finding a owl:Class .
ex:Problem a owl:Class ; rdfs:subClassOf prov:Entity .
ex:Result a owl:Class .
ex:Quantity a owl:Class .
ex:Run a owl:Class ; rdfs:subClassOf prov:Activity .
prov:Entity a owl:Class .
prov:Activity a owl:Class .
prov:AgentInfluence a owl:Class .

ex:ProblemShape a sh:NodeShape ; sh:targetClass ex:Problem .
ex:ResultShape a sh:NodeShape ; sh:targetClass ex:Result .
ex:FindingShape a sh:NodeShape ; sh:targetClass ex:Finding .
ex:RunShape a sh:NodeShape ; sh:targetClass ex:Run .

ex:about a owl:ObjectProperty ; rdfs:domain ex:Finding ; rdfs:range ex:Problem .
ex:problemName a owl:DatatypeProperty ; rdfs:domain ex:Problem .
ex:measured a owl:ObjectProperty ; rdfs:domain ex:Result ; rdfs:range ex:Quantity .
ex:unit a owl:DatatypeProperty ; rdfs:domain ex:Quantity .
prov:wasGeneratedBy a owl:ObjectProperty ; rdfs:domain prov:Entity ; rdfs:range prov:Activity .
prov:used a owl:ObjectProperty ; rdfs:domain prov:Activity ; rdfs:range prov:Entity .
prov:agent a owl:ObjectProperty ; rdfs:domain prov:AgentInfluence .
prov:Association a owl:Class ; rdfs:subClassOf prov:AgentInfluence .
ex:Plan a owl:Class ; rdfs:subClassOf prov:Entity .
prov:qualifiedAssociation a owl:ObjectProperty ; rdfs:domain prov:Activity ; rdfs:range prov:Association .
prov:hadPlan a owl:ObjectProperty ; rdfs:domain prov:Association ; rdfs:range ex:Plan .
"""

THE_ACCESSION = "/ExampleRecord/@Accession"
THE_VERSION = "/ExampleRecord/@Version"
THE_LABEL = "/ExampleRecord/Label"
A_GAP = "ex:only-the-first-run-of-a-labels-text-is-carried"
NO_TERM = "/ExampleRecord/Note"


def carried(path, *nodes, verdict=CARRIED):
    written = ["[] a bridge:PathEntry", f'bridge:sourcePath "{path}"', f"bridge:verdict {verdict}"]
    if verdict == CARRIED_IN_PART:
        written.append(f"bridge:namesGap {A_GAP}")
    if verdict == NO_HOME:
        written.append("bridge:namesGap ex:no-term-for-a-free-text-note")
    written += [
        f"bridge:carriedAs [ bridge:asProperty {term} ; bridge:inRecordClass {within} ]" for term, within in nodes
    ]
    return " ;\n  ".join(written) + " .\n"


def accounted(package, *entries):
    text = (
        PREFIXES_OF_AN_ACCOUNTING
        + "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .\n"
        + "@prefix prov: <http://www.w3.org/ns/prov#> .\n\n"
        + "\n".join(entries)
    )
    Graph().parse(data=text, format="turtle")
    return package.write(ACCOUNTING, text)


def a_vocabulary_beside(package, text=A_VOCABULARY):
    (package.path.parent / VOCABULARIES.name / THE_VOCABULARY_FILE).write_text(text, encoding="utf-8", newline="")


def said_about(package):
    return "\n".join(carried_as.faulty(package.crate))


@pytest.fixture
def beside(package):
    a_vocabulary_beside(package)
    return package


class TestTermsACarriedPathIsCarriedAs:
    """Terms a carried path is carried as · adapter/profile/must/carried_as.py, shapes/carried-as.shapes.ttl

    A carried entry names the property and the record class its path is carried as, and both are looked up in the
    Cascade vocabulary checked out beside the adapter.
    """

    class TestGivenAnAccountingWhoseCarriedEntriesNameDeclaredTerms:
        def test_reports_nothing_for_an_accounting_whose_every_carried_entry_names_a_declared_property_on_its_domain(
            self, beside
        ):
            accounted(
                beside,
                carried(THE_ACCESSION, ("ex:accession", "ex:Record")),
                carried(THE_VERSION, ("ex:accession", "ex:Revision"), ("rdfs:label", "ex:Note")),
                carried(THE_LABEL, ("ex:status", "ex:Note"), verdict=CARRIED_IN_PART),
                carried(NO_TERM, verdict=NO_HOME),
            )
            assert not said_about(beside)

        @pytest.mark.parametrize("committed", ["crate", "json_crate"], ids=["the XML adapter", "the JSON adapter"])
        def test_reports_nothing_for_the_accounting_each_synthetic_adapter_commits(self, request, committed):
            assert not list(carried_as.faulty(request.getfixturevalue(committed)))

        @pytest.mark.parametrize(
            ("term", "within"),
            [
                pytest.param("ex:accession", "ex:Revision", id="ex:accession on ex:Revision"),
                pytest.param("ex:status", "ex:Note", id="ex:status on ex:Note"),
                pytest.param("ex:status", "ex:Revision", id="ex:status on ex:Revision"),
                pytest.param("ex:doseQuantity", "ex:Record", id="ex:doseQuantity on ex:Record"),
                pytest.param("ex:unit", "ex:Revision", id="ex:unit on ex:Revision"),
                pytest.param("rdfs:label", "ex:Quantity", id="rdfs:label on ex:Quantity"),
            ],
        )
        def test_accepts_a_domain_that_is_a_superclass_a_union_member_reached_through_a_property_or_absent(
            self, beside, term, within
        ):
            """accepts a domain that is a superclass, a union member, reached through a property, or absent"""
            accounted(beside, carried(THE_ACCESSION, (term, within)))
            assert not said_about(beside)

    class TestGivenAnAccountingNamingATermWrongly:
        def test_reports_a_carried_entry_and_a_carried_in_part_entry_naming_no_bridge_carriedas_and_no_other(
            self, beside
        ):
            """reports a carried entry and a carried-in-part entry naming no `bridge:carriedAs` and no other"""
            accounted(
                beside,
                carried(THE_ACCESSION),
                carried(THE_LABEL, verdict=CARRIED_IN_PART),
                carried(THE_VERSION, ("ex:accession", "ex:Record")),
                carried(NO_TERM, verdict=NO_HOME),
            )
            said = said_about(beside)
            wanted = (
                "An entry whose verdict is bridge:carried or bridge:carriedInPart names at least one bridge:carriedAs: "
                "the Cascade property its path's value becomes, and the class of the record it is written on."
            )
            assert f"{THE_ACCESSION}: {wanted}" in said
            assert f"{THE_LABEL}: {wanted}" in said
            assert THE_VERSION not in said
            assert NO_TERM not in said

        def test_reports_a_property_the_vocabulary_does_not_declare(self, beside):
            accounted(
                beside,
                carried(THE_ACCESSION, ("ex:Note", "ex:Record")),
                carried(THE_VERSION, ("ex:version", "ex:Record")),
            )
            said = said_about(beside)
            assert (
                f"{THE_ACCESSION} is carried as ex:Note, which no bridge:vocabularyFile of {VOCABULARIES.name} declares a "
                "property" in said
            )
            assert f"ex:version, which no bridge:vocabularyFile of {VOCABULARIES.name} declares a property" in said

        def test_reports_a_record_class_the_vocabulary_does_not_declare(self, beside):
            accounted(beside, carried(THE_ACCESSION, ("rdfs:label", "ex:accession")))
            assert (
                f"{THE_ACCESSION} is carried on ex:accession, which no bridge:vocabularyFile of {VOCABULARIES.name} declares "
                "a class" in said_about(beside)
            )

        @pytest.mark.parametrize(
            ("term", "within"),
            [
                pytest.param("ex:noteText", "ex:Record", id="ex:noteText on ex:Record"),
                pytest.param("ex:accession", "ex:Note", id="ex:accession on ex:Note"),
                pytest.param("ex:unit", "ex:Unrelated", id="ex:unit on ex:Unrelated"),
                pytest.param("ex:status", "ex:Dosage", id="ex:status on ex:Dosage"),
            ],
        )
        def test_reports_a_property_whose_domain_does_not_cover_the_record_class(self, beside, term, within):
            accounted(beside, carried(THE_ACCESSION, (term, within)))
            assert (
                f"{THE_ACCESSION} is carried as {term} on {within}, where the rdfs:domain of {term} covers neither "
                f"{within}, a class it is a subclass of, nor a class a property of it reaches"
            ) in said_about(beside)

    class TestGivenTheVocabularyBesideTheAdapter:
        def test_reports_one_not_checked_out_only_once_an_entry_names_a_term(self, package):
            shutil.rmtree(package.path.parent / VOCABULARIES.name)
            accounted(package, carried(THE_ACCESSION))
            assert "is not checked out" not in said_about(package)
            accounted(package, carried(THE_ACCESSION, ("ex:accession", "ex:Record")))
            said = said_about(package)
            assert f"{VOCABULARIES.name} is not checked out at" in said
            assert "beside the adapter, where its bridge:vocabularyFile are read" in said

        def test_reports_a_vocabulary_file_missing_from_the_checkout(self, beside):
            (beside.path.parent / VOCABULARIES.name / THE_VOCABULARY_FILE).unlink()
            accounted(beside, carried(THE_ACCESSION, ("ex:accession", "ex:Record")))
            assert f"{THE_VOCABULARY_FILE} is no file of {VOCABULARIES.name}" in said_about(beside)

    class TestGivenAPropertyWhoseDomainIsReachedThroughAnotherProperty:
        @pytest.mark.parametrize(
            ("term", "within", "reported"),
            [
                pytest.param("ex:problemName", "ex:Finding", True, id="ex:problemName on ex:Finding, reported"),
                pytest.param("ex:problemName", "ex:Problem", False, id="ex:problemName on ex:Problem, not reported"),
                pytest.param("ex:unit", "ex:Result", False, id="ex:unit on ex:Result, not reported"),
                pytest.param("prov:used", "ex:Problem", True, id="prov:used on ex:Problem, reported"),
                pytest.param("prov:agent", "ex:Problem", True, id="prov:agent on ex:Problem, reported"),
                pytest.param("prov:agent", "ex:Run", False, id="prov:agent on ex:Run, not reported"),
                pytest.param(
                    "prov:wasGeneratedBy", "ex:Problem", False, id="prov:wasGeneratedBy on ex:Problem, not reported"
                ),
                pytest.param("prov:hadPlan", "ex:Run", False, id="prov:hadPlan on ex:Run, not reported"),
                pytest.param("prov:wasGeneratedBy", "ex:Run", True, id="prov:wasGeneratedBy on ex:Run, reported"),
            ],
        )
        def test_reaches_through_to_a_class_stopping_at_one_a_shape_targets_or_a_subclass_of_one(
            self, package, term, within, reported
        ):
            """reaches through to a class, stopping at one a shape targets or a subclass of one"""
            a_vocabulary_beside(package, A_VOCABULARY_WITH_RECORD_CLASSES)
            accounted(package, carried(THE_ACCESSION, (term, within)))
            assert bool(said_about(package)) is reported
