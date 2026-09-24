from rdflib import Graph, Literal
from rdflib.namespace import RDF, SH, SKOS, XSD

from _codes import scheme_named_by
from _selectors import selector_of
from _terms import BRIDGE, OA
from adapter_profile_world import accounting_of, below_the_record, cases, refinement_of, selected_by


def lookups_of(crate):
    """Each (source path, concept map, gap) an entry declares a lookup by, either half of it standing for one."""
    accounting = accounting_of(crate)
    for entry in accounting.subjects(RDF.type, BRIDGE.PathEntry):
        concept_map = accounting.value(entry, BRIDGE.lookupIn)
        gap = accounting.value(entry, BRIDGE.lookupNamesGap)
        if concept_map is not None or gap is not None:
            yield str(accounting.value(entry, BRIDGE.sourcePath)), concept_map, gap


def the_one_lookup(crate):
    declared = sorted(lookups_of(crate), key=lambda lookup: lookup[0])
    assert len(declared) == 1, (
        f"the synthetic adapter's accounting declares {len(declared)} lookups, where the vector declares one"
    )
    return declared[0]


def notations_of(crate, concept_map):
    graph = Graph().parse(crate.file_at(concept_map), format="turtle")
    return {str(notation) for notation in graph.objects(None, SKOS.notation)}


XML_WHITESPACE = " \t\r\n"


def key_of(value):
    return value.strip(XML_WHITESPACE).lower()


def value_of(element):
    """A path's value: the text of an element with no element children, and nothing where it has one."""
    return None if len(element) else (element.text or "")


def held_at(record, source_path):
    """Each (value as the record wrote it, the elements holding it in document order) at a path of the record."""
    holding = {}
    for element in record.xpath(below_the_record(source_path)):
        value = value_of(element)
        if value is not None:
            holding.setdefault(value, []).append(element)
    return holding


def outside(holding, notations):
    return {value: elements for value, elements in holding.items() if key_of(value) and key_of(value) not in notations}


def reported_by_the_lookup(graph, record, gap):
    return [
        finding
        for finding in graph.subjects(RDF.type, OA.Annotation)
        if selected_by(graph, finding)[0] == selector_of(record) and graph.value(finding, OA.hasBody) == gap
    ]


def every_value_outside_the_map(crate):
    """Each (case, findings graph, record, finding, value, the elements of the record holding it) the vector reports."""
    source_path, concept_map, gap = the_one_lookup(crate)
    notations = notations_of(crate, concept_map)
    found = []
    for named, graph, records in cases(crate):
        for record in records:
            missed = outside(held_at(record, source_path), notations)
            reported = reported_by_the_lookup(graph, record, gap)
            written = sorted(str(graph.value(finding, SH.value) or "") for finding in reported)
            assert written == sorted(missed), f"{named}: {selector_of(record)}"
            for finding in reported:
                value = str(graph.value(finding, SH.value))
                found.append((named, graph, record, finding, value, missed[value]))
    assert found, "no record of the synthetic adapter's inputs holds a value the concept map it is looked up in lacks"
    return found


def test_an_entry_declares_the_concept_map_its_paths_values_are_looked_up_in_and_the_gap_a_value_outside_it_opens(
    crate,
):
    _, concept_map, gap = the_one_lookup(crate)
    assert concept_map in set(crate.graph.objects(crate.root, BRIDGE.table))
    assert crate.file_at(concept_map) is not None
    scheme = scheme_named_by(crate)
    assert (gap, RDF.type, SKOS.Concept) in scheme
    assert scheme.value(gap, SKOS.broader) == BRIDGE.valueNotMapped


def test_a_value_the_concept_map_lacks_is_reported_once_per_distinct_value_and_a_value_it_carries_nowhere(crate):
    reported = every_value_outside_the_map(crate)
    assert len(reported) == 1, "the vector reports one status outside the concept map, and reports it once"
    for named, graph, _, finding, value, _ in reported:
        assert graph.value(finding, OA.motivatedBy) == OA.classifying, f"{named}: {value}"


def test_a_lookup_finding_is_addressed_at_the_first_occurrence_of_its_value_in_the_record(crate):
    for named, graph, record, finding, value, holding in every_value_outside_the_map(crate):
        assert selected_by(graph, finding) == (selector_of(record), refinement_of(record, holding[0])), (
            f"{named}: {value}"
        )


def test_a_lookup_finding_carries_the_value_as_the_record_wrote_it_and_never_the_key_or_the_path(crate):
    source_path, _, _ = the_one_lookup(crate)
    reported = every_value_outside_the_map(crate)
    assert any(value != key_of(value) for _, _, _, _, value, _ in reported), (
        "every value the vector reports is already its own key, so nothing there tells "
        "the value as the record wrote it from the key it is looked up by"
    )
    for named, graph, _, finding, value, _ in reported:
        assert graph.value(finding, SH.value) == Literal(value), f"{named}: {value}"
        assert value != source_path, f"{named}: {value}"


def test_a_lookup_finding_counts_the_nodes_of_the_record_holding_its_value_where_they_are_more_than_one(crate):
    counted = []
    for named, graph, _, finding, value, holding in every_value_outside_the_map(crate):
        expected = None if len(holding) == 1 else Literal(len(holding), datatype=XSD.integer)
        assert graph.value(finding, BRIDGE.occurrences) == expected, f"{named}: {value}"
        counted.append(len(holding))
    assert 2 in counted, "no record of the vector holds one value outside the concept map twice"


def test_a_lookup_finding_takes_the_severity_its_gap_declares_and_sh_info_where_it_declares_none(crate):
    _, _, gap = the_one_lookup(crate)
    declared = scheme_named_by(crate).value(gap, SH.resultSeverity) or SH.Info
    for named, graph, _, finding, value, _ in every_value_outside_the_map(crate):
        assert graph.value(finding, SH.resultSeverity) == declared, f"{named}: {value}"
