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
        'bridge:serverBaseUrl "HTTPS://Records.Example.ORG/api/" ;',
        'bridge:serverBaseUrl "HTTPS://Records.Example.ORG/api/", "https://elsewhere.example" ;',
    )
    assert "at most one bridge:serverBaseUrl" in said(package.crate)


def test_reports_a_fact_a_bridge_computes_supplied_with_the_document(package):
    package.edit(
        FACTS,
        "  bridge:sourceFormatVersion",
        '  bridge:sha256 "ni:///sha-256;supplied" ;\n  bridge:sourceFormatVersion',
    )
    assert "bridge:sha256" in said(package.crate)


def test_reports_an_attribution_naming_its_role_by_a_literal(package):
    package.edit(FACTS, "prov:hadRole rec:author", 'prov:hadRole "author"')
    assert "prov:hadRole, by IRI" in said(package.crate)


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
