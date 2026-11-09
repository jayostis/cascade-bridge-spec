import facts

FACTS = "fixtures/facts/example-registry.ttl"


def said(crate):
    return "\n".join(facts.faulty(crate))


def test_reports_nothing_for_the_facts_the_synthetic_adapter_supplies(crate):
    assert not said(crate)


def test_reports_facts_naming_a_file_that_is_not_there(package):
    package.edit("fixtures/manifest.ttl", "<facts/example-registry.ttl>", "<facts/absent.ttl>", times=11)
    assert "absent.ttl, which is not a file in this package" in said(package.crate)


def test_reports_facts_that_are_not_turtle(package):
    package.edit(FACTS, "@prefix rdfs:", "@prefixx rdfs:")
    assert "example-registry.ttl does not parse as Turtle" in said(package.crate)


def test_reports_a_document_supplied_two_server_base_urls(package):
    package.edit(
        FACTS,
        'cascade:serverBaseUrl "HTTPS://Records.Example.ORG/api/" ;',
        'cascade:serverBaseUrl "HTTPS://Records.Example.ORG/api/", "https://elsewhere.example" ;',
    )
    assert "at most one cascade:serverBaseUrl" in said(package.crate)


def test_reports_a_fact_a_bridge_computes_supplied_with_the_document(package):
    package.edit(
        FACTS,
        "  cascade:sourceFormatVersion",
        '  bridge:sha256 "ni:///sha-256;supplied" ;\n  cascade:sourceFormatVersion',
    )
    assert "bridge:sha256" in said(package.crate)


def test_reports_an_association_naming_its_role_by_a_literal(package):
    package.edit(FACTS, "prov:hadRole cascade:AuthorRole", 'prov:hadRole "author"')
    assert "prov:hadRole, by IRI" in said(package.crate)


def test_reports_a_role_stated_on_an_attribution_of_the_document(package):
    package.write(
        FACTS,
        """@prefix rdfs:   <http://www.w3.org/2000/01/rdf-schema#> .
@prefix prov:   <http://www.w3.org/ns/prov#> .
@prefix bridge: <https://ns.cascadeprotocol.org/bridge/v1-draft#> .
@prefix cascade: <https://ns.cascadeprotocol.org/cascade#> .

bridge:thisDocument prov:qualifiedAttribution
  [ prov:agent [ rdfs:label "Example Records Registry" ] ; prov:hadRole cascade:AuthorRole ] .
""",
    )
    assert "never on a prov:qualifiedAttribution" in said(package.crate)


def test_reports_a_document_generated_by_two_acts(package):
    package.edit(FACTS, "prov:wasGeneratedBy _:writing ;", "prov:wasGeneratedBy _:writing, _:rewriting ;")
    assert "at most one prov:wasGeneratedBy" in said(package.crate)


def test_reports_a_generating_act_carrying_more_than_its_associations(package):
    package.edit(
        FACTS, "_:writing prov:qualifiedAssociation", '_:writing rdfs:label "a writing" ;\n  prov:qualifiedAssociation'
    )
    assert "prov:qualifiedAssociation, and nothing else" in said(package.crate)


def test_reports_an_agent_the_document_is_attributed_to_that_carries_no_label(package):
    package.edit(FACTS, "prov:wasAttributedTo _:registry ;", "prov:wasAttributedTo _:registry, _:nameless ;")
    assert "exactly one rdfs:label" in said(package.crate)


def test_reports_an_import_time_that_is_no_datetime(package):
    package.edit(FACTS, 'prov:startedAtTime "2026-09-01T10:00:00Z"^^xsd:dateTime', 'prov:startedAtTime "yesterday"')
    assert "prov:startedAtTime, an xsd:dateTime" in said(package.crate)


def test_reports_a_fact_stated_of_a_misspelled_document(package):
    package.edit(FACTS, "bridge:thisDocument\n", "bridge:thisDocumnet\n")
    assert "v1-draft#thisDocumnet is none of them" in said(package.crate)


def test_reports_a_fact_stated_of_a_subject_that_is_neither_the_document_the_import_nor_what_they_name(package):
    package.edit(
        FACTS, "bridge:thisImport\n", '<https://example.org/elsewhere> rdfs:label "a stray" .\n\nbridge:thisImport\n'
    )
    assert "https://example.org/elsewhere is none of them" in said(package.crate)


def test_reports_a_document_attributed_to_an_agent_that_is_only_a_transmitter(package):
    package.edit(FACTS, "prov:wasAttributedTo _:registry ;", "prov:wasAttributedTo _:registry, _:fetcher ;")
    assert "is no author or custodian" in said(package.crate)


def test_reports_an_author_the_document_is_not_attributed_to(package):
    package.edit(FACTS, "  prov:wasAttributedTo _:registry ;\n", "")
    assert "is not attributed" in said(package.crate)


def test_reports_a_document_attributed_to_an_agent_no_association_names(package):
    package.edit(
        FACTS, "prov:wasAttributedTo _:registry ;", 'prov:wasAttributedTo _:registry, [ rdfs:label "Stray" ] ;'
    )
    assert "is no author or custodian" in said(package.crate)


def test_reports_a_generating_act_with_no_association(package):
    package.write(
        FACTS,
        """@prefix bridge: <https://ns.cascadeprotocol.org/bridge/v1-draft#> .
@prefix prov:   <http://www.w3.org/ns/prov#> .

bridge:thisDocument prov:wasGeneratedBy [] .
""",
    )
    assert "at least one prov:qualifiedAssociation" in said(package.crate)
