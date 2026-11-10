from _findings import SHAPES
from adapter_profile_world import unmet_over

PREFIXES = """@prefix bridge:  <https://ns.cascadeprotocol.org/bridge/v1-draft#> .
@prefix ex:      <https://example.org/synthetic-adapter/v1#> .
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

THE_ENTRY_THAT_BREAKS_IT = "/ClinicalDocument/recordTarget/patientRole/patient/administrativeGenderCode/@code"

C_CDA_ACCOUNTING_WITH_ONE_NO_HOME_ENTRY_NAMING_NO_GAP = f"""
[] a bridge:PathEntry ;
  bridge:sourcePath "/ClinicalDocument/id/@root" ;
  bridge:verdict bridge:carried .

[] a bridge:PathEntry ;
  bridge:sourcePath "/ClinicalDocument/title" ;
  bridge:verdict bridge:noHome ;
  bridge:namesGap ex:documentTitle .

[] a bridge:PathEntry ;
  bridge:sourcePath "/ClinicalDocument/effectiveTime/@value" ;
  bridge:verdict bridge:noHome ;
  bridge:namesGap ex:documentEffectiveTime .

[] a bridge:PathEntry ;
  bridge:sourcePath "/ClinicalDocument/languageCode/@code" ;
  bridge:verdict bridge:noHome ;
  bridge:namesGap ex:documentLanguage .

[] a bridge:PathEntry ;
  bridge:sourcePath "/ClinicalDocument/versionNumber/@value" ;
  bridge:verdict bridge:noHome ;
  bridge:namesGap ex:documentVersion .

[] a bridge:PathEntry ;
  bridge:sourcePath "{THE_ENTRY_THAT_BREAKS_IT}" ;
  bridge:verdict bridge:noHome .

[] a bridge:PathEntry ;
  bridge:sourcePath "/ClinicalDocument/confidentialityCode/@code" ;
  bridge:verdict bridge:noHome ;
  bridge:namesGap ex:documentConfidentiality .
"""


def faults_over(turtle):
    return unmet_over(PREFIXES + turtle, SHAPES)


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


class TestFaultsThatNameTheNodeThatBroke:
    """Faults that name the node that broke · adapter/profile/_findings.py

    A fault is one line of a failing run: the sentence of the shape that was broken and the node that broke it. Two
    nodes breaking one shape are two faults, each telling its own node.
    """

    class TestGivenAShapeBrokenAtTwoNodes:
        def test_gives_two_faults_each_naming_its_node(self):
            """gives two faults, each naming its node"""
            faults = faults_over(TWO_ENTRIES_CARRYING_NO_SOURCE_PATH)

            assert len(faults) == 2, faults
            assert all(ONE_SOURCE_PATH in fault for fault in faults), faults
            named = [[node for node in (THE_LABEL_ENTRY, THE_NOTE_ENTRY) if node in fault] for fault in faults]
            assert sorted(named) == [[THE_LABEL_ENTRY], [THE_NOTE_ENTRY]], faults

    class TestGivenAFaultOverACCDAAccounting:
        """given a fault over a C-CDA accounting"""

        def test_names_the_source_path_of_the_entry_that_broke_it(self):
            faults = faults_over(C_CDA_ACCOUNTING_WITH_ONE_NO_HOME_ENTRY_NAMING_NO_GAP)

            assert len(faults) == 1, faults
            assert A_NO_HOME_ENTRY_NAMES_ONE_GAP in faults[0]
            assert THE_ENTRY_THAT_BREAKS_IT in faults[0]

    class TestGivenAFaultFoundThroughANestedShape:
        def test_names_the_nested_node_that_broke_it(self):
            faults = faults_over(TWO_ALIKE_FINDINGS_WHOSE_TARGETS_NAME_NO_SOURCE)

            assert len(faults) == 2, faults
            assert all(A_TARGET_NAMES_ONE_SOURCE in fault for fault in faults), faults
            named = [
                [record for record in (THE_FIRST_RECORD, THE_SECOND_RECORD) if record in fault] for fault in faults
            ]
            assert sorted(named) == [[THE_FIRST_RECORD], [THE_SECOND_RECORD]], faults
