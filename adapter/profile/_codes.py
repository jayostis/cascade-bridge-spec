from rdflib import Graph, URIRef
from rdflib.namespace import RDF, SH, SKOS

from _json_source import syntax_of
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

KEYWORDS_OF_JSON_SCHEMA_DRAFT_06 = (
    "multipleOf",
    "maximum",
    "exclusiveMaximum",
    "minimum",
    "exclusiveMinimum",
    "maxLength",
    "minLength",
    "pattern",
    "items",
    "additionalItems",
    "maxItems",
    "minItems",
    "uniqueItems",
    "contains",
    "maxProperties",
    "minProperties",
    "required",
    "properties",
    "patternProperties",
    "additionalProperties",
    "dependencies",
    "propertyNames",
    "enum",
    "const",
    "type",
    "allOf",
    "anyOf",
    "oneOf",
    "not",
)

JSON_SCHEMA_DRAFT_06_VALIDATION = "https://datatracker.ietf.org/doc/html/draft-wright-json-schema-validation-01"

JSON_SCHEMA_DRAFT_06_KEYWORD_ANCHORS = {
    keyword: URIRef(f"{JSON_SCHEMA_DRAFT_06_VALIDATION}#section-6.{section}")
    for section, keyword in enumerate(KEYWORDS_OF_JSON_SCHEMA_DRAFT_06, start=1)
}

JSON_SCHEMA_RULE_ANCHORS = frozenset(JSON_SCHEMA_DRAFT_06_KEYWORD_ANCHORS.values())

BODIES_OF_A_SCHEMA_FAILURE = W3C_XML_SCHEMA_RULE_ANCHORS | JSON_SCHEMA_RULE_ANCHORS | {BRIDGE.schemaRuleUnnamed}

THE_ANCHORS = ", ".join(sorted(str(anchor) for anchor in W3C_XML_SCHEMA_RULE_ANCHORS))

THE_JSON_SCHEMA_ANCHORS = ", ".join(str(anchor) for anchor in JSON_SCHEMA_DRAFT_06_KEYWORD_ANCHORS.values())


def schema_rule_anchors_of(crate):
    return JSON_SCHEMA_RULE_ANCHORS if syntax_of(crate) == "json" else W3C_XML_SCHEMA_RULE_ANCHORS


CONSTRAINT_COMPONENTS_OF_SHACL = (
    "And",
    "Class",
    "Closed",
    "Datatype",
    "Disjoint",
    "Equals",
    "HasValue",
    "In",
    "LanguageIn",
    "LessThan",
    "LessThanOrEquals",
    "MaxCount",
    "MaxExclusive",
    "MaxInclusive",
    "MaxLength",
    "MinCount",
    "MinExclusive",
    "MinInclusive",
    "MinLength",
    "Node",
    "NodeKind",
    "Not",
    "Or",
    "Pattern",
    "Property",
    "QualifiedMaxCount",
    "QualifiedMinCount",
    "SPARQL",
    "UniqueLang",
    "Xone",
)

SHACL_CONSTRAINT_COMPONENTS = frozenset(SH[f"{name}ConstraintComponent"] for name in CONSTRAINT_COMPONENTS_OF_SHACL)

THE_CONSTRAINT_COMPONENTS = ", ".join(f"sh:{name}ConstraintComponent" for name in CONSTRAINT_COMPONENTS_OF_SHACL)

BODIES_OF_AN_OUTPUT_VALIDATION_FINDING = SHACL_CONSTRAINT_COMPONENTS | {BRIDGE.predicateNotDeclared}


def accounts_for_its_source(crate):
    return (crate.root, BRIDGE.sourceAccounting, None) in crate.graph


def no_gap_of_the_scheme(crate):
    admitted = "bridge:schemaRuleUnnamed, or bridge:pathNotAccounted"
    if not accounts_for_its_source(crate):
        admitted = "or bridge:schemaRuleUnnamed, the adapter naming no bridge:sourceAccounting"
    if syntax_of(crate) == "json":
        rule, anchors = (
            "the anchor of a JSON Schema draft-06 validation keyword",
            THE_JSON_SCHEMA_ANCHORS,
        )
    else:
        rule, anchors = "the anchor of a validation rule in a W3C XML Schema Recommendation", THE_ANCHORS
    return (
        f"is not a gap of the adapter's bridge:gapScheme, {rule}, {admitted}. A finding about the produced graph "
        "takes the SHACL constraint component that failed, or bridge:predicateNotDeclared. "
        f"The anchors a body may take are {anchors}. "
        f"The constraint components it may take are {THE_CONSTRAINT_COMPONENTS}"
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
    schema = schema_rule_anchors_of(crate) | {BRIDGE.schemaRuleUnnamed}
    return gaps_of(crate) | schema | BODIES_OF_AN_OUTPUT_VALIDATION_FINDING | census
