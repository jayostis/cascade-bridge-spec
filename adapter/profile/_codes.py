from rdflib import Graph, URIRef
from rdflib.namespace import RDF, SKOS

from _terms import BRIDGE

KINDS_A_GAP_MAY_NAME = (
    BRIDGE.carriedWithLoss,
    BRIDGE.noPredicate,
    BRIDGE.schemaRuleUnnamed,
    BRIDGE.sourceLacksRequired,
    BRIDGE.valueNotMapped,
)

THE_KINDS_A_GAP_MAY_NAME = ", ".join(str(kind).replace(str(BRIDGE), "bridge:") for kind in KINDS_A_GAP_MAY_NAME)

VALIDATION_RULES_OF_XML_SCHEMA_PART_1 = (
    "cos-st-restricts",
    "cvc-assess-attr",
    "cvc-attribute",
    "cvc-complex-type",
    "cvc-elt",
    "cvc-id",
    "cvc-identity-constraint",
    "cvc-simple-type",
    "cvc-type",
    "src-resolve",
)

VALIDATION_RULES_OF_XML_SCHEMA_PART_2 = (
    "cos-applicable-facets",
    "cvc-datatype-valid",
    "cvc-enumeration-valid",
    "cvc-fractionDigits-valid",
    "cvc-length-valid",
    "cvc-maxExclusive-valid",
    "cvc-maxInclusive-valid",
    "cvc-maxLength-valid",
    "cvc-minExclusive-valid",
    "cvc-minInclusive-valid",
    "cvc-minLength-valid",
    "cvc-pattern-valid",
    "cvc-totalDigits-valid",
)

W3C_XML_SCHEMA_RULE_ANCHORS = frozenset(
    URIRef(f"https://www.w3.org/TR/xmlschema-{part}/#{rule}")
    for part, rules in ((1, VALIDATION_RULES_OF_XML_SCHEMA_PART_1), (2, VALIDATION_RULES_OF_XML_SCHEMA_PART_2))
    for rule in rules
)

BODIES_OF_A_SCHEMA_FAILURE = W3C_XML_SCHEMA_RULE_ANCHORS | {BRIDGE.schemaRuleUnnamed}

THE_ANCHORS = ", ".join(sorted(str(anchor) for anchor in W3C_XML_SCHEMA_RULE_ANCHORS))


def accounts_for_its_source(crate):
    return (crate.root, BRIDGE.sourceAccounting, None) in crate.graph


def no_gap_of_the_scheme(crate):
    admitted = "bridge:schemaRuleUnnamed, or bridge:pathNotAccounted"
    if not accounts_for_its_source(crate):
        admitted = "or bridge:schemaRuleUnnamed, the adapter naming no bridge:sourceAccounting"
    return (
        "is not a gap of the adapter's bridge:gapScheme, the anchor of a validation rule "
        f"in a W3C XML Schema Recommendation, {admitted}. "
        f"The anchors a body may take are {THE_ANCHORS}"
    )


def scheme_named_by(crate):
    """The graph of the one gap scheme the adapter names, empty where gap_scheme.py has a fault to report."""
    named = list(crate.graph.objects(crate.root, BRIDGE.gapScheme))
    path = crate.file_at(named[0]) if len(named) == 1 else None
    graph = Graph()
    if path is None:
        return graph
    try:
        graph.parse(path, format="turtle")
    except Exception:
        return Graph()
    return graph


def gaps_of(crate):
    return set(scheme_named_by(crate).subjects(RDF.type, SKOS.Concept))


def bodies_a_finding_may_carry(crate):
    census = {BRIDGE.pathNotAccounted} if accounts_for_its_source(crate) else set()
    return gaps_of(crate) | BODIES_OF_A_SCHEMA_FAILURE | census
