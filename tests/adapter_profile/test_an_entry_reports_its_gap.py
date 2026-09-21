from lxml import etree
from rdflib import Graph, Literal
from rdflib.namespace import RDF, SH, SKOS, XSD

from _codes import KINDS_A_GAP_MAY_NAME, scheme_named_by
from _selectors import selector_of, step_of
from _terms import BRIDGE, MF, OA

KINDS_AN_ENTRY_REPORTS = (BRIDGE.noPredicate, BRIDGE.sourceLacksRequired)
KINDS_AN_ENTRY_REPORTS_NOTHING_OF = (BRIDGE.carriedWithLoss, BRIDGE.valueNotMapped, BRIDGE.schemaRuleUnnamed)
VERDICTS_THAT_MAY_NAME_A_GAP = (BRIDGE.carriedInPart, BRIDGE.noHome)

THE_NAMESPACE = "https://example.org/synthetic-adapter/ext/v1"

THE_CASE = "example-0005"
THE_CENSUS_CASE = "example-0004"

A_PATH_STANDING_AT_MORE_THAN_ONE_NODE = "/ExampleRecord/Label/Emphasis"
A_PATH_STANDING_AT_ONE_NODE = "/ExampleRecord/Note"
A_PATH_IN_A_NAMESPACE = f"/ExampleRecord/*[local-name()='Provenance' and namespace-uri()='{THE_NAMESPACE}']"
A_PATH_WHOSE_ENTRY_NAMES_NO_GAP = "/ExampleRecord/Status"
A_PATH_WHOSE_ENTRY_NAMES_A_GAP_OF_A_KIND_THAT_REPORTS_NOTHING = "/ExampleRecord/Label"
AN_UNACCOUNTED_PATH_STANDING_AT_MORE_THAN_ONE_NODE = (
    f"/ExampleRecord/*[local-name()='Extension' and namespace-uri()='{THE_NAMESPACE}']"
)
AN_UNACCOUNTED_PATH_STANDING_AT_ONE_NODE = "/ExampleRecord/Novelty"


def accounting_of(crate):
    named = crate.graph.value(crate.root, BRIDGE.sourceAccounting)
    assert named is not None, "the synthetic adapter names no bridge:sourceAccounting"
    return Graph().parse(crate.file_at(named), format="turtle")


def entries_of(crate):
    """Each (source path, gap, severity) of the accounting, the gap None where the entry names none."""
    accounting, scheme = accounting_of(crate), scheme_named_by(crate)
    for entry in accounting.subjects(RDF.type, BRIDGE.PathEntry):
        path = accounting.value(entry, BRIDGE.sourcePath)
        verdict = accounting.value(entry, BRIDGE.verdict)
        gap = accounting.value(entry, BRIDGE.namesGap)
        if gap is not None and verdict not in VERDICTS_THAT_MAY_NAME_A_GAP:
            gap = None
        yield str(path), gap, None if gap is None else (scheme.value(gap, SH.resultSeverity) or SH.Info)


def reported_by_an_entry(crate):
    scheme = scheme_named_by(crate)
    return [
        (path, gap, severity)
        for path, gap, severity in entries_of(crate)
        if gap is not None and scheme.value(gap, SKOS.broader) in KINDS_AN_ENTRY_REPORTS
    ]


def naming_a_gap_no_entry_reports(crate):
    scheme = scheme_named_by(crate)
    return [
        (path, gap)
        for path, gap, _ in entries_of(crate)
        if gap is not None and scheme.value(gap, SKOS.broader) in KINDS_AN_ENTRY_REPORTS_NOTHING_OF
    ]


def records_of(crate, document):
    name = str(crate.graph.value(crate.root, BRIDGE.elementNameOfEachRecord) or "")
    return document.xpath("//*[local-name()=$name]", name=name)


def cases(crate):
    """Each (name, expected findings graph, records) a test of the manifest names an input and findings for."""
    for test in crate.entries:
        result = crate.graph.value(test, MF.result)
        expected = None if result is None else crate.graph.value(result, BRIDGE.expectedFindings)
        action = crate.graph.value(test, MF.action)
        source = None if action is None else crate.graph.value(action, BRIDGE.input)
        if expected is None or source is None:
            continue
        graph = Graph().parse(crate.file_at(expected), format="turtle")
        records = records_of(crate, etree.parse(str(crate.file_at(source))))
        yield crate.name_of(test), graph, records


def the_case(crate, named):
    found = [case for case in cases(crate) if case[0] == named]
    assert found, f"the manifest names no case {named} carrying an input and expected findings"
    return found[0]


def below_the_record(source_path):
    """The path an XPath evaluates from the record element, which is the step a bridge:sourcePath starts at."""
    return source_path.removeprefix("/").split("/", 1)[1]


def standing_at(record, source_path):
    """The element each node at a path stands on, in document order: an attribute stands on the element carrying it."""
    relative = below_the_record(source_path)
    if relative.startswith("@"):
        return [record] if record.xpath(relative) else []
    if "/@" in relative:
        on, _, attribute = relative.rpartition("/@")
        return [owner for owner in record.xpath(on) if owner.xpath(f"@{attribute}")]
    return record.xpath(relative)


def refinement_of(record, element):
    steps, walked = [], element
    while walked is not None and walked is not record:
        steps.append(step_of(walked, True))
        walked = walked.getparent()
    return "/".join(reversed(steps)) or None


def selected_by(graph, finding):
    selector = graph.value(graph.value(finding, OA.hasTarget), OA.hasSelector)
    refined = graph.value(selector, OA.refinedBy)
    return str(graph.value(selector, RDF.value)), None if refined is None else str(graph.value(refined, RDF.value))


def findings_about(graph, record):
    for finding in graph.subjects(RDF.type, OA.Annotation):
        if selected_by(graph, finding)[0] == selector_of(record):
            yield finding


def naming(graph, record, source_path, body=None):
    return [
        finding
        for finding in findings_about(graph, record)
        if str(graph.value(finding, SH.value) or "") == source_path
        and (body is None or graph.value(finding, OA.hasBody) == body)
    ]


def the_one_naming(graph, record, source_path, body=None):
    found = naming(graph, record, source_path, body)
    assert len(found) == 1, (
        f"{selector_of(record)} expects {len(found)} findings naming {source_path}, where a path is reported once"
    )
    return found[0]


def each_path_reported(crate):
    """Each (case, records graph, record, path, gap, severity, the elements the path stands at) the contract reports."""
    for named, graph, records in cases(crate):
        for record in records:
            for source_path, gap, severity in reported_by_an_entry(crate):
                standing = standing_at(record, source_path)
                if standing:
                    yield named, graph, record, source_path, gap, severity, standing


def every(reported):
    found = list(reported)
    assert found, "no record of the synthetic adapter's inputs stands at a path whose entry names a reporting gap"
    return found


def test_the_kinds_that_report_and_the_kinds_that_report_nothing_are_every_gap_kind_between_them():
    assert set(KINDS_AN_ENTRY_REPORTS).isdisjoint(KINDS_AN_ENTRY_REPORTS_NOTHING_OF)
    assert set(KINDS_AN_ENTRY_REPORTS) | set(KINDS_AN_ENTRY_REPORTS_NOTHING_OF) == set(KINDS_A_GAP_MAY_NAME)


def test_an_entry_whose_verdict_names_a_reporting_gap_is_expected_once_per_distinct_path_per_record(crate):
    for named, graph, record, source_path, gap, _, _ in every(each_path_reported(crate)):
        finding = the_one_naming(graph, record, source_path)
        assert graph.value(finding, OA.hasBody) == gap, f"{named}: {source_path}"
        assert graph.value(finding, OA.motivatedBy) == OA.classifying, f"{named}: {source_path}"


def test_a_finding_an_entry_reports_is_addressed_at_the_first_occurrence_of_its_path_in_the_record(crate):
    for named, graph, record, source_path, _, _, standing in every(each_path_reported(crate)):
        finding = the_one_naming(graph, record, source_path)
        assert selected_by(graph, finding) == (selector_of(record), refinement_of(record, standing[0])), (
            f"{named}: {source_path}"
        )


def test_a_finding_an_entry_reports_carries_the_number_of_nodes_of_the_record_standing_at_its_path(crate):
    for named, graph, record, source_path, _, _, standing in every(each_path_reported(crate)):
        finding = the_one_naming(graph, record, source_path)
        counted = None if len(standing) == 1 else Literal(len(standing), datatype=XSD.integer)
        assert graph.value(finding, BRIDGE.occurrences) == counted, f"{named}: {source_path}"


def test_a_finding_an_entry_reports_takes_the_severity_its_gap_declares_and_sh_info_where_it_declares_none(crate):
    for named, graph, record, source_path, _, severity, _ in every(each_path_reported(crate)):
        finding = the_one_naming(graph, record, source_path)
        assert graph.value(finding, SH.resultSeverity) == severity, f"{named}: {source_path}"


def test_an_entry_whose_verdict_names_no_gap_reports_nothing(crate):
    silent = [path for path, gap, _ in entries_of(crate) if gap is None]
    assert A_PATH_WHOSE_ENTRY_NAMES_NO_GAP in silent
    _, graph, records = the_case(crate, THE_CASE)
    assert [record for record in records if standing_at(record, A_PATH_WHOSE_ENTRY_NAMES_NO_GAP)], (
        f"no record of {THE_CASE} stands at {A_PATH_WHOSE_ENTRY_NAMES_NO_GAP}, "
        "so nothing there shows that an entry naming no gap reports nothing"
    )
    for named, graph, records in cases(crate):
        for record in records:
            for source_path in silent:
                assert not naming(graph, record, source_path), f"{named}: {source_path}"


def test_an_entry_naming_a_gap_of_a_kind_that_reports_nothing_is_expected_at_no_record(crate):
    silent = naming_a_gap_no_entry_reports(crate)
    the_path = A_PATH_WHOSE_ENTRY_NAMES_A_GAP_OF_A_KIND_THAT_REPORTS_NOTHING
    assert the_path in [path for path, _ in silent]
    standing = [record for _, _, records in cases(crate) for record in records if standing_at(record, the_path)]
    assert standing, f"no record of the synthetic adapter's inputs stands at {the_path}"
    for named, graph, records in cases(crate):
        for record in records:
            for source_path, gap in silent:
                assert not naming(graph, record, source_path, gap), f"{named}: {source_path}"


def test_a_path_standing_at_more_than_one_node_of_one_record_is_reported_once_carrying_that_count(crate):
    named, graph, records = the_case(crate, THE_CASE)
    assert [source_path for source_path, _, _ in reported_by_an_entry(crate)].count(
        A_PATH_STANDING_AT_MORE_THAN_ONE_NODE
    ) == 1
    standing = [(record, standing_at(record, A_PATH_STANDING_AT_MORE_THAN_ONE_NODE)) for record in records]
    record, nodes = max(standing, key=lambda found: len(found[1]))
    assert len(nodes) > 1, f"no record of {named} stands at more than one {A_PATH_STANDING_AT_MORE_THAN_ONE_NODE}"
    finding = the_one_naming(graph, record, A_PATH_STANDING_AT_MORE_THAN_ONE_NODE)
    assert graph.value(finding, BRIDGE.occurrences) == Literal(len(nodes), datatype=XSD.integer)
    assert selected_by(graph, finding)[1] == refinement_of(record, nodes[0])


def test_a_path_standing_at_one_node_of_a_record_is_reported_carrying_no_count(crate):
    _, graph, records = the_case(crate, THE_CASE)
    standing = [(record, standing_at(record, A_PATH_STANDING_AT_ONE_NODE)) for record in records]
    record, nodes = max(standing, key=lambda found: len(found[1]))
    assert len(nodes) == 1, f"{A_PATH_STANDING_AT_ONE_NODE} stands at {len(nodes)} nodes, where one is the case"
    finding = the_one_naming(graph, record, A_PATH_STANDING_AT_ONE_NODE)
    assert graph.value(finding, BRIDGE.occurrences) is None


def test_a_path_in_a_namespace_is_reported_at_the_step_a_selector_writes_for_it(crate):
    reported = dict((path, gap) for path, gap, _ in reported_by_an_entry(crate))
    assert A_PATH_IN_A_NAMESPACE in reported
    _, graph, records = the_case(crate, THE_CASE)
    record = next(record for record in records if standing_at(record, A_PATH_IN_A_NAMESPACE))
    finding = the_one_naming(graph, record, A_PATH_IN_A_NAMESPACE, reported[A_PATH_IN_A_NAMESPACE])
    assert selected_by(graph, finding)[1] == (f"*[local-name()='Provenance' and namespace-uri()='{THE_NAMESPACE}'][1]")


def test_a_gap_declaring_a_warning_gives_that_severity_to_the_finding_an_entry_reports_it_by(crate):
    severities = dict((path, severity) for path, _, severity in reported_by_an_entry(crate))
    assert severities.get(A_PATH_IN_A_NAMESPACE) == SH.Warning
    _, graph, records = the_case(crate, THE_CASE)
    record = next(record for record in records if standing_at(record, A_PATH_IN_A_NAMESPACE))
    assert graph.value(the_one_naming(graph, record, A_PATH_IN_A_NAMESPACE), SH.resultSeverity) == SH.Warning


def test_a_census_finding_carries_the_number_of_nodes_standing_at_its_path_on_the_same_rule(crate):
    accounted = [path for path, _, _ in entries_of(crate)]
    assert AN_UNACCOUNTED_PATH_STANDING_AT_MORE_THAN_ONE_NODE not in accounted
    _, graph, records = the_case(crate, THE_CASE)
    record = next(
        record for record in records if standing_at(record, AN_UNACCOUNTED_PATH_STANDING_AT_MORE_THAN_ONE_NODE)
    )
    nodes = standing_at(record, AN_UNACCOUNTED_PATH_STANDING_AT_MORE_THAN_ONE_NODE)
    assert len(nodes) > 1
    finding = the_one_naming(graph, record, AN_UNACCOUNTED_PATH_STANDING_AT_MORE_THAN_ONE_NODE, BRIDGE.pathNotAccounted)
    assert graph.value(finding, BRIDGE.occurrences) == Literal(len(nodes), datatype=XSD.integer)
    assert selected_by(graph, finding)[1] == refinement_of(record, nodes[0])

    _, census, records = the_case(crate, THE_CENSUS_CASE)
    alone = next(record for record in records if standing_at(record, AN_UNACCOUNTED_PATH_STANDING_AT_ONE_NODE))
    assert len(standing_at(alone, AN_UNACCOUNTED_PATH_STANDING_AT_ONE_NODE)) == 1
    only = the_one_naming(census, alone, AN_UNACCOUNTED_PATH_STANDING_AT_ONE_NODE, BRIDGE.pathNotAccounted)
    assert census.value(only, BRIDGE.occurrences) is None


def test_a_gap_an_entry_reports_and_a_findings_query_constructs_stands_as_two_findings(crate):
    reported = dict((path, gap) for path, gap, _ in reported_by_an_entry(crate))
    assert A_PATH_STANDING_AT_ONE_NODE in reported
    _, graph, records = the_case(crate, THE_CASE)
    record = next(record for record in records if standing_at(record, A_PATH_STANDING_AT_ONE_NODE))
    both = [
        finding
        for finding in findings_about(graph, record)
        if graph.value(finding, OA.hasBody) == reported[A_PATH_STANDING_AT_ONE_NODE]
    ]
    assert len(both) == 2, "a gap both an entry and a findings query report stands twice, nothing deduplicating them"
    assert sorted(str(graph.value(finding, SH.value) or "") for finding in both) == ["", A_PATH_STANDING_AT_ONE_NODE]
