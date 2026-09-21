from pathlib import Path

from rdflib import Graph, URIRef
from rdflib.namespace import RDFS

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = " ".join((ROOT / "engine" / "sparql.md").read_text(encoding="utf-8").split())
VOCABULARY = Graph().parse(ROOT / "vocab" / "bridge.ttl", format="turtle")
BRIDGE = "https://ns.cascadeprotocol.org/bridge/v1-draft#"

HOW_AN_ISOMORPHIC_CONVERSION_TEST_COMPARES = str(
    VOCABULARY.value(URIRef(f"{BRIDGE}IsomorphicConversionTest"), RDFS.comment)
)


def test_two_addresses_selecting_one_node_of_the_input_are_the_same_finding():
    assert (
        "two oa:XPathSelector rdf:values match where they select the same node of bridge:input"
        in HOW_AN_ISOMORPHIC_CONVERSION_TEST_COMPARES
    )


def test_an_address_selecting_other_than_one_node_of_the_input_is_compared_as_it_is_written():
    assert (
        "one selecting other than exactly one node matches only the same spelling"
        in HOW_AN_ISOMORPHIC_CONVERSION_TEST_COMPARES
    )


def test_everything_else_a_finding_carries_is_compared_exactly():
    assert "IRIs and literals exact" in HOW_AN_ISOMORPHIC_CONVERSION_TEST_COMPARES


def test_the_contract_holds_a_records_selector_to_no_spelling():
    assert "Every step below the document element carries" not in CONTRACT


def test_a_records_selector_selects_the_record_and_a_refinement_a_node_of_that_record():
    assert (
        "A record's selector is an XPath selecting the record, and a refinement is an XPath relative to the record, "
        "selecting one node of it."
    ) in CONTRACT


def test_a_bridge_reports_an_address_of_its_own_that_selects_no_one_node():
    assert (
        "An address a Bridge writes that does not select exactly one node of the document it is about carries "
        "`bridge:addressNotOneNode` as its body, the address as written as its `sh:value`, and `sh:Violation` as "
        "its `sh:resultSeverity`."
    ) in CONTRACT


def test_that_finding_is_addressed_at_the_record_once_for_each_distinct_address():
    assert "addressed at the record, refined no further, once for each distinct address" in CONTRACT


def test_a_bridge_reports_such_an_address_and_refuses_nothing_for_it():
    assert "The finding whose address it is stands, and a Bridge refuses nothing for it." in CONTRACT


def test_an_adapter_fixes_such_an_address_rather_than_committing_an_oracle_that_holds_one():
    assert (
        "The adapter profile refuses an expected findings file holding such an address, so no oracle carries "
        "`bridge:addressNotOneNode`: an adapter whose mapping writes an address its own input does not resolve "
        "to one node fixes the address, and the body is what a Bridge writes on a caller's document."
    ) in CONTRACT
