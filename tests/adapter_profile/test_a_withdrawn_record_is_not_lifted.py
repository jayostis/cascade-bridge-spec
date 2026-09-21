from rdflib import Graph

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


def mapped(crate, *statuses):
    """What the adapter's one bridge:mapping constructs from that record, over the dataset its tables are loaded into."""
    named = list(crate.graph.objects(crate.root, BRIDGE.mapping))
    assert len(named) == 1, (
        f"the synthetic adapter names {len(named)} bridge:mapping queries, where the vector names one"
    )
    dataset = Graph().parse(data=lifted(*statuses), format="turtle")
    for table in crate.graph.objects(crate.root, BRIDGE.table):
        dataset.parse(crate.file_at(table), format="turtle")
    return dataset.query(crate.file_at(named[0]).read_text(encoding="utf-8")).graph


def test_a_record_holding_a_status_the_concept_map_maps_to_something_other_than_withdrawn_is_lifted(crate):
    assert len(mapped(crate, "current"))


def test_a_record_holding_a_status_the_concept_map_lacks_is_lifted(crate):
    assert len(mapped(crate, "Retired"))


def test_a_record_holding_no_status_at_all_is_lifted(crate):
    assert len(mapped(crate))


def test_a_record_whose_only_status_is_withdrawn_is_not_lifted(crate):
    assert not len(mapped(crate, "withdrawn"))


def test_a_record_holding_withdrawn_beside_another_status_is_not_lifted(crate):
    assert not len(mapped(crate, "withdrawn", "current"))
    assert not len(mapped(crate, "current", "withdrawn"))
    assert not len(mapped(crate, "Retired", "withdrawn"))


def test_a_record_whose_withdrawn_is_spelled_outside_its_key_is_not_lifted(crate):
    assert not len(mapped(crate, " Withdrawn "))
