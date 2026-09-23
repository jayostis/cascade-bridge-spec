from rdflib import Graph

from _findings import SHAPES, unmet

PREFIXES = """@prefix bridge:  <https://ns.cascadeprotocol.org/bridge/v1-draft#> .
@prefix ex:      <https://example.org/synthetic-adapter/v1#> .
@prefix clinvar: <https://ns.cascadeprotocol.org/adapter/clinvar/v1-draft#> .
"""

ONE_SOURCE_PATH = "An entry carries exactly one bridge:sourcePath, the path it accounts for, a string."
A_NO_HOME_ENTRY_NAMES_ONE_GAP = "An entry whose verdict is bridge:noHome names exactly one bridge:namesGap"

THE_LABEL_ENTRY = "https://example.org/synthetic-adapter/v1#the-label-entry"
THE_NOTE_ENTRY = "https://example.org/synthetic-adapter/v1#the-note-entry"

TWO_ENTRIES_CARRYING_NO_SOURCE_PATH = f"""
<{THE_LABEL_ENTRY}> a bridge:PathEntry ;
  bridge:verdict bridge:carried .

<{THE_NOTE_ENTRY}> a bridge:PathEntry ;
  bridge:verdict bridge:carried .
"""

THE_ENTRY_THAT_BREAKS_IT = (
    "/VariationArchive/ClassifiedRecord/Classifications/GermlineClassification/@NumberOfSubmitters"
)

CLINVAR_ACCOUNTING_WITH_ONE_NO_HOME_ENTRY_NAMING_NO_GAP = f"""
[] a bridge:PathEntry ;
  bridge:sourcePath "/VariationArchive/@Accession" ;
  bridge:verdict bridge:carried .

[] a bridge:PathEntry ;
  bridge:sourcePath "/VariationArchive/@NumberOfSubmissions" ;
  bridge:verdict bridge:noHome ;
  bridge:namesGap clinvar:aggregateNumberOfSubmissions .

[] a bridge:PathEntry ;
  bridge:sourcePath "/VariationArchive/@NumberOfSubmitters" ;
  bridge:verdict bridge:noHome ;
  bridge:namesGap clinvar:aggregateNumberOfSubmitters .

[] a bridge:PathEntry ;
  bridge:sourcePath "/VariationArchive/ClassifiedRecord/Classifications/GermlineClassification/@DateLastEvaluated" ;
  bridge:verdict bridge:noHome ;
  bridge:namesGap clinvar:aggregateClassificationEvaluationDate .

[] a bridge:PathEntry ;
  bridge:sourcePath "/VariationArchive/ClassifiedRecord/Classifications/GermlineClassification/@NumberOfSubmissions" ;
  bridge:verdict bridge:noHome ;
  bridge:namesGap clinvar:aggregateNumberOfSubmissions .

[] a bridge:PathEntry ;
  bridge:sourcePath "{THE_ENTRY_THAT_BREAKS_IT}" ;
  bridge:verdict bridge:noHome .

[] a bridge:PathEntry ;
  bridge:sourcePath "/VariationArchive/ClassifiedRecord/Classifications/GermlineClassification/Citation" ;
  bridge:verdict bridge:noHome ;
  bridge:namesGap clinvar:aggregateClassificationCitation .
"""


def faults_over(turtle):
    return list(
        unmet(
            Graph().parse(data=PREFIXES + turtle, format="turtle"),
            Graph().parse(SHAPES, format="turtle"),
        )
    )


def test_a_shape_broken_at_two_nodes_gives_two_faults_each_naming_its_node():
    faults = faults_over(TWO_ENTRIES_CARRYING_NO_SOURCE_PATH)

    assert len(faults) == 2, faults
    assert all(ONE_SOURCE_PATH in fault for fault in faults), faults
    named = [[node for node in (THE_LABEL_ENTRY, THE_NOTE_ENTRY) if node in fault] for fault in faults]
    assert sorted(named) == [[THE_LABEL_ENTRY], [THE_NOTE_ENTRY]], faults


def test_a_fault_over_the_clinvar_accounting_names_the_source_path_of_the_entry_that_broke_it():
    faults = faults_over(CLINVAR_ACCOUNTING_WITH_ONE_NO_HOME_ENTRY_NAMING_NO_GAP)

    assert len(faults) == 1, faults
    assert A_NO_HOME_ENTRY_NAMES_ONE_GAP in faults[0]
    assert THE_ENTRY_THAT_BREAKS_IT in faults[0]


THE_FIRST_RECORD = "/ExampleRecordSet/ExampleRecord[1]"
THE_SECOND_RECORD = "/ExampleRecordSet/ExampleRecord[2]"

TWO_ALIKE_FINDINGS_WHOSE_TARGETS_NAME_NO_SOURCE = f"""
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix sh:  <http://www.w3.org/ns/shacl#> .
@prefix oa:  <http://www.w3.org/ns/oa#> .

[] a oa:Annotation ;
  oa:hasTarget [
    oa:hasSelector [ a oa:XPathSelector ; rdf:value "{THE_FIRST_RECORD}" ]
  ] ;
  oa:hasBody ex:no-term-for-a-free-text-note ;
  oa:motivatedBy oa:classifying ;
  sh:resultSeverity sh:Info .

[] a oa:Annotation ;
  oa:hasTarget [
    oa:hasSelector [ a oa:XPathSelector ; rdf:value "{THE_SECOND_RECORD}" ]
  ] ;
  oa:hasBody ex:no-term-for-a-free-text-note ;
  oa:motivatedBy oa:classifying ;
  sh:resultSeverity sh:Info .
"""

A_TARGET_NAMES_ONE_SOURCE = "A finding's target names exactly one oa:hasSource by IRI"


def test_a_fault_found_through_a_nested_shape_names_the_nested_node_that_broke_it():
    faults = faults_over(TWO_ALIKE_FINDINGS_WHOSE_TARGETS_NAME_NO_SOURCE)

    assert len(faults) == 2, faults
    assert all(A_TARGET_NAMES_ONE_SOURCE in fault for fault in faults), faults
    named = [[record for record in (THE_FIRST_RECORD, THE_SECOND_RECORD) if record in fault] for fault in faults]
    assert sorted(named) == [[THE_FIRST_RECORD], [THE_SECOND_RECORD]], faults
