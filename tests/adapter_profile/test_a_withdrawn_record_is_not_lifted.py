from rdflib import Graph, Literal

from _terms import BRIDGE

A_RECORD = """@prefix rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix fx:   <http://sparql.xyz/facade-x/ns/> .
@prefix xyz:  <http://sparql.xyz/facade-x/data/> .

[] a fx:root, xyz:ExampleRecord ;
  xyz:Accession "EX000007" ;
  xyz:Version "1" ;
  rdf:_1 [ a xyz:Label ; rdf:_1 "a record written to exercise the statuses it holds" ]"""


def lifted(*statuses):
    """The record above, lifted as sparql.md's Facade-X, holding one xyz:Status element per status given."""
    held = [f'rdf:_{slot} [ a xyz:Status ; rdf:_1 "{status}" ]' for slot, status in enumerate(statuses, start=2)]
    return A_RECORD + "".join(f" ;\n  {element}" for element in held) + " .\n"


A_DOCUMENT = "ni:///sha-256;tGm9FWfUKGlKI5ifQdPtjK86ZoCkfBTJr0IBDqbDSE8"


def dataset(crate, *statuses):
    """The record above in its dataset, as sparql.md's steps build it, a document of that one record, supplied no facts."""
    graph = Graph().parse(data=lifted(*statuses), format="turtle")
    for table in crate.graph.objects(crate.root, BRIDGE.table):
        graph.parse(crate.file_at(table), format="turtle")
    graph.add((BRIDGE.thisDocument, BRIDGE.sha256, Literal(A_DOCUMENT)))
    graph.add((BRIDGE.thisRecord, BRIDGE.selector, Literal("/ExampleRecord")))
    for query in crate.graph.objects(crate.root, BRIDGE.documentTableQuery):
        graph += graph.query(crate.file_at(query).read_text(encoding="utf-8")).graph
    return graph


def mapped(crate, *statuses):
    """What the adapter's one bridge:mapping constructs from that record's dataset."""
    named = list(crate.graph.objects(crate.root, BRIDGE.mapping))
    assert len(named) == 1, (
        f"the synthetic adapter names {len(named)} bridge:mapping queries, where the vector names one"
    )
    return dataset(crate, *statuses).query(crate.file_at(named[0]).read_text(encoding="utf-8")).graph


class TestRecordsAMappingLeavesOutAsWithdrawn:
    """Records a mapping leaves out as withdrawn · fixtures/synthetic-adapter/

    The synthetic adapter's mapping shows the pattern for dropping a record by a looked-up value: it lifts no record
    whose status the concept map maps to withdrawn.
    """

    class TestGivenARecordHoldingAStatusTheConceptMapMapsToSomethingOtherThanWithdrawn:
        def test_is_lifted(self, crate):
            assert len(mapped(crate, "current"))

    class TestGivenARecordHoldingAStatusTheConceptMapLacks:
        def test_is_lifted(self, crate):
            assert len(mapped(crate, "Retired"))

    class TestGivenARecordHoldingNoStatusAtAll:
        def test_is_lifted(self, crate):
            assert len(mapped(crate))

    class TestGivenARecordWhoseOnlyStatusIsWithdrawn:
        def test_is_not_lifted(self, crate):
            assert not len(mapped(crate, "withdrawn"))

    class TestGivenARecordHoldingWithdrawnBesideAnotherStatus:
        def test_is_not_lifted(self, crate):
            assert not len(mapped(crate, "withdrawn", "current"))
            assert not len(mapped(crate, "current", "withdrawn"))
            assert not len(mapped(crate, "Retired", "withdrawn"))

    class TestGivenARecordWhoseWithdrawnIsSpelledOutsideItsKey:
        def test_is_not_lifted(self, crate):
            assert not len(mapped(crate, " Withdrawn "))

    class TestGivenARecordPaddedWithACharacterThatOnlyUnicodeCallsWhitespace:
        """given a record padded with a character that only Unicode calls whitespace"""

        def test_is_lifted(self, crate):
            assert len(mapped(crate, " withdrawn"))
