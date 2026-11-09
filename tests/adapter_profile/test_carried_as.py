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


def test_reports_nothing_for_an_accounting_whose_every_carried_entry_names_a_declared_property_on_its_domain(beside):
    accounted(
        beside,
        carried(THE_ACCESSION, ("ex:accession", "ex:Record")),
        carried(THE_VERSION, ("ex:accession", "ex:Revision"), ("rdfs:label", "ex:Note")),
        carried(THE_LABEL, ("ex:status", "ex:Note"), verdict=CARRIED_IN_PART),
        carried(NO_TERM, verdict=NO_HOME),
    )
    assert not said_about(beside)


def test_reports_a_carried_entry_and_a_carried_in_part_entry_naming_no_carried_as_and_no_other(beside):
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


@pytest.mark.parametrize("committed", ["crate", "json_crate"])
def test_reports_nothing_for_the_accounting_each_synthetic_adapter_commits(request, committed):
    assert not list(carried_as.faulty(request.getfixturevalue(committed)))


def test_reports_a_property_the_vocabulary_does_not_declare(beside):
    accounted(
        beside, carried(THE_ACCESSION, ("ex:Note", "ex:Record")), carried(THE_VERSION, ("ex:version", "ex:Record"))
    )
    said = said_about(beside)
    assert (
        f"{THE_ACCESSION} is carried as ex:Note, which no bridge:vocabularyFile of {VOCABULARIES.name} declares a "
        "property" in said
    )
    assert f"ex:version, which no bridge:vocabularyFile of {VOCABULARIES.name} declares a property" in said


def test_reports_a_record_class_the_vocabulary_does_not_declare(beside):
    accounted(beside, carried(THE_ACCESSION, ("rdfs:label", "ex:accession")))
    assert (
        f"{THE_ACCESSION} is carried on ex:accession, which no bridge:vocabularyFile of {VOCABULARIES.name} declares "
        "a class" in said_about(beside)
    )


@pytest.mark.parametrize(
    ("term", "within"),
    [
        ("ex:noteText", "ex:Record"),
        ("ex:accession", "ex:Note"),
        ("ex:unit", "ex:Unrelated"),
        ("ex:status", "ex:Dosage"),
    ],
)
def test_reports_a_property_whose_domain_does_not_cover_the_record_class(beside, term, within):
    accounted(beside, carried(THE_ACCESSION, (term, within)))
    assert (
        f"{THE_ACCESSION} is carried as {term} on {within}, where the rdfs:domain of {term} covers neither "
        f"{within}, a class it is a subclass of, nor a class a property of it reaches"
    ) in said_about(beside)


@pytest.mark.parametrize(
    ("term", "within"),
    [
        ("ex:accession", "ex:Revision"),
        ("ex:status", "ex:Note"),
        ("ex:status", "ex:Revision"),
        ("ex:doseQuantity", "ex:Record"),
        ("ex:unit", "ex:Revision"),
        ("rdfs:label", "ex:Quantity"),
    ],
)
def test_accepts_a_domain_that_is_a_superclass_a_union_member_or_reached_through_a_property_or_no_domain(
    beside, term, within
):
    accounted(beside, carried(THE_ACCESSION, (term, within)))
    assert not said_about(beside)


def test_reports_a_vocabulary_not_checked_out_beside_the_adapter_only_once_a_term_is_named(package):
    shutil.rmtree(package.path.parent / VOCABULARIES.name)
    accounted(package, carried(THE_ACCESSION))
    assert "is not checked out" not in said_about(package)
    accounted(package, carried(THE_ACCESSION, ("ex:accession", "ex:Record")))
    said = said_about(package)
    assert f"{VOCABULARIES.name} is not checked out at" in said
    assert "beside the adapter, where its bridge:vocabularyFile are read" in said


def test_reports_a_vocabulary_file_missing_from_the_checkout(beside):
    (beside.path.parent / VOCABULARIES.name / THE_VOCABULARY_FILE).unlink()
    accounted(beside, carried(THE_ACCESSION, ("ex:accession", "ex:Record")))
    assert f"{THE_VOCABULARY_FILE} is no file of {VOCABULARIES.name}" in said_about(beside)


@pytest.mark.parametrize(
    ("term", "within", "reported"),
    [
        ("ex:problemName", "ex:Finding", True),
        ("ex:problemName", "ex:Problem", False),
        ("ex:unit", "ex:Result", False),
        ("prov:used", "ex:Problem", True),
        ("prov:agent", "ex:Problem", True),
        ("prov:agent", "ex:Run", False),
        ("prov:wasGeneratedBy", "ex:Problem", False),
        ("prov:hadPlan", "ex:Run", False),
        ("prov:wasGeneratedBy", "ex:Run", True),
    ],
)
def test_reaches_through_a_property_to_a_class_and_stops_at_one_a_shape_targets_or_one_such_a_class_is_a_subclass_of(
    package, term, within, reported
):
    a_vocabulary_beside(package, A_VOCABULARY_WITH_RECORD_CLASSES)
    accounted(package, carried(THE_ACCESSION, (term, within)))
    assert bool(said_about(package)) is reported
