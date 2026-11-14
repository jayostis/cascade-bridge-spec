"""The page a reader browses an adapter on, built from an adapter checkout and the vocabulary its terms are labelled in."""

import json
import re
import subprocess
from html.parser import HTMLParser

import pytest

import adapter_explorer

REPOSITORY = "https://github.com/example/example-adapter"
REPORT = "https://example.org/conformance/tests/example-adapter/"

CRATE = {
    "@context": [
        "https://w3id.org/ro/crate/1.2/context",
        {"bridge": "https://ns.cascadeprotocol.org/bridge/v1-draft#"},
    ],
    "@graph": [
        {"@id": "ro-crate-metadata.json", "@type": "CreativeWork", "about": {"@id": "./"}},
        {
            "@id": "./",
            "@type": ["Dataset", "bridge:Adapter"],
            "identifier": "example",
            "name": "Example JSON",
            "version": "0.4.1",
            "bridge:vocabularyFile": ["ontologies/example.ttl"],
            "bridge:envelope": [{"@id": "#envelope-listing"}, {"@id": "#envelope-record"}],
            "bridge:mapping": [{"@id": "in/observation.rq"}],
            "bridge:findingsQuery": [{"@id": "in/findings.rq"}],
            "bridge:gapScheme": {"@id": "vocab/gaps.ttl"},
            "bridge:sourceAccounting": {"@id": "vocab/accounting.ttl"},
            "bridge:testManifest": {"@id": "fixtures/manifest.ttl"},
        },
        {
            "@id": "#envelope-listing",
            "@type": "bridge:Envelope",
            "name": "listing",
            "bridge:pathOfContentInRecord": "/item",
        },
        {
            "@id": "#envelope-record",
            "@type": "bridge:Envelope",
            "name": "record",
            "bridge:pathOfContentInRecord": "",
            "bridge:pathOfContainedContentBelowContent": "/contained",
        },
    ],
}

PREFIXES = """\
@prefix bridge: <https://ns.cascadeprotocol.org/bridge/v1-draft#> .
@prefix ex: <https://example.org/vocab#> .
@prefix exa: <https://example.org/adapter#> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix mf: <http://www.w3.org/2001/sw/DataAccess/tests/test-manifest#> .
@prefix oa: <http://www.w3.org/ns/oa#> .
"""

ACCOUNTING = """
[] a bridge:PathEntry ; bridge:sourcePath "/category" ; bridge:verdict bridge:consumed .
[] a bridge:PathEntry ; bridge:sourcePath "/category/coding" ; bridge:verdict bridge:consumed .
[] a bridge:PathEntry ; bridge:sourcePath "/category/coding/code" ; bridge:verdict bridge:carried ;
  bridge:concern bridge:concernCodes ;
  bridge:carriedAs [ bridge:inSourceRecordType "Observation" ; bridge:inRecordClass ex:Observation ;
                     bridge:asProperty ex:categoryCode ] .
[] a bridge:PathEntry ; bridge:sourcePath "/item/category/coding/code" ; bridge:verdict bridge:carried ;
  bridge:concern bridge:concernCodes ;
  bridge:carriedAs [ bridge:inSourceRecordType "Observation" ; bridge:inRecordClass ex:Observation ;
                     bridge:asProperty ex:categoryCode ] .
[] a bridge:PathEntry ; bridge:sourcePath "/category/coding/display" ; bridge:verdict bridge:ignored ;
  bridge:because "A display repeats what its code says." .
[] a bridge:PathEntry ; bridge:sourcePath "/category/text" ; bridge:verdict bridge:noHome ;
  bridge:namesGap exa:categoryTextNotCarried .
[] a bridge:PathEntry ; bridge:sourcePath "/subject/reference" ; bridge:verdict bridge:carried ;
  bridge:carriedAs [ bridge:inSourceRecordType "Observation" ; bridge:inRecordClass ex:Observation ;
                     bridge:asProperty ex:subject ] .
[] a bridge:PathEntry ; bridge:sourcePath "/contained/subject/reference" ; bridge:verdict bridge:carried ;
  bridge:carriedAs [ bridge:inSourceRecordType "Observation" ; bridge:inRecordClass ex:Observation ;
                     bridge:asProperty ex:subject ] .
"""

GAPS = """
exa:gaps a skos:ConceptScheme .
exa:categoryTextNotCarried a skos:Concept ; skos:inScheme exa:gaps ;
  skos:prefLabel "A category's text has no Cascade predicate."@en ;
  skos:broader bridge:noPredicate ;
  rdfs:seeAlso <https://github.com/example/example-adapter/issues/4> .
"""

OBSERVATION_QUERY = """\
PREFIX ex: <https://example.org/vocab#>
CONSTRUCT {
  ?record a ex:Observation ;
    ex:categoryCode ?code ; # a code of the category
    ?subjectProperty ?subject .
}
WHERE { ?record ex:read ?code . OPTIONAL { ?record ex:read ?subject BIND (ex:subject AS ?subjectProperty) } }
"""

FINDINGS_QUERY = """\
PREFIX oa: <http://www.w3.org/ns/oa#>
PREFIX exa: <https://example.org/adapter#>
CONSTRUCT { ?finding oa:hasBody exa:categoryTextNotCarried . }
WHERE { ?finding oa:hasTarget ?text }
"""

MANIFEST = """
<> a mf:Manifest ; mf:entries ( <#category-coded> <#category-coded-at-length> <#subject-only> ) .

<#category-coded> a bridge:IsomorphicConversionTest ; mf:name "category-coded" ;
  rdfs:comment "An observation's category, coded and in text." ;
  mf:action [ bridge:input <in/category-coded.json> ] ;
  mf:result [ bridge:expectedGraph <expected/category-coded.ttl> ] .

<#category-coded-at-length> a bridge:IsomorphicConversionTest ; mf:name "category-coded-at-length" ;
  mf:action [ bridge:input <in/category-coded-at-length.json> ] ;
  mf:result [ bridge:expectedGraph <expected/category-coded-at-length.ttl> ;
              bridge:expectedFindings <findings/category-coded-at-length.ttl> ] .

<#subject-only> a bridge:IsomorphicConversionTest ; mf:name "subject-only" ;
  mf:action [ bridge:input <in/subject-only.json> ] ;
  mf:result [ bridge:expectedGraph <expected/subject-only.ttl> ] .
"""

INPUTS = {
    "category-coded": {"category": {"coding": [{"code": "vital-signs"}], "text": "Vital signs"}},
    "category-coded-at-length": {
        "category": {"coding": [{"code": "vital-signs", "display": "Vital signs"}], "text": "Vital signs"},
        "subject": {"reference": "Patient/a"},
        "note": "Taken at length, the record a reader should not be shown first.",
    },
    "subject-only": {
        "subject": {"reference": "Patient/a"},
        "note": "A subject alone, written at length, so that the smallest input whose graph has a subject holds none.",
    },
}

GRAPHS = {
    "category-coded": '<urn:r> a ex:Observation ; ex:categoryCode "vital-signs" ; ex:subject <urn:p> .',
    "category-coded-at-length": '<urn:r> a ex:Observation ; ex:categoryCode "vital-signs" ; ex:subject <urn:p> .',
    "subject-only": "<urn:r> a ex:Observation ; ex:subject <urn:p> .",
}

FINDINGS = {
    "category-coded-at-length": "<urn:f> oa:hasBody exa:categoryTextNotCarried .",
}

VOCABULARY = """
ex:Observation rdfs:label "Observation"@en .
ex:categoryCode rdfs:label "Category code"@en .
ex:subject rdfs:label "Subject"@en .
"""


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def an_adapter(folder):
    write(folder / "ro-crate-metadata.json", json.dumps(CRATE, indent=2))
    write(folder / "vocab" / "accounting.ttl", PREFIXES + ACCOUNTING)
    write(folder / "vocab" / "gaps.ttl", PREFIXES + GAPS)
    write(folder / "in" / "observation.rq", OBSERVATION_QUERY)
    write(folder / "in" / "findings.rq", FINDINGS_QUERY)
    write(folder / "fixtures" / "manifest.ttl", PREFIXES + MANIFEST)
    for name, record in INPUTS.items():
        write(folder / "fixtures" / "in" / f"{name}.json", json.dumps(record, indent=2))
        write(folder / "fixtures" / "expected" / f"{name}.ttl", PREFIXES + GRAPHS[name])
    for name, findings in FINDINGS.items():
        write(folder / "fixtures" / "findings" / f"{name}.ttl", PREFIXES + findings)
    git = [
        "git",
        "-C",
        str(folder),
        "-c",
        "user.name=t",
        "-c",
        "user.email=t@example.org",
        "-c",
        "commit.gpgsign=false",
    ]
    subprocess.run([*git, "init", "-q"], check=True)
    subprocess.run([*git, "add", "-A"], check=True)
    subprocess.run([*git, "commit", "-q", "-m", "an adapter"], check=True)
    return subprocess.run([*git, "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()


class ShownText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hidden = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        self.hidden += tag in ("script", "style")

    def handle_endtag(self, tag):
        self.hidden -= tag in ("script", "style")

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


class Explorer:
    def __init__(self, out, commit):
        self.out = out
        self.commit = commit
        self.data = json.loads((out / "explorer.json").read_text(encoding="utf-8"))
        self.page = (out / "index.html").read_text(encoding="utf-8")

    def node(self, place):
        found = [node for node in self.nodes(self.data["tree"]) if node["place"] == place]
        assert len(found) == 1, place
        return found[0]

    def nodes(self, nodes):
        for node in nodes:
            yield node
            yield from self.nodes(node["children"])

    def mapping(self, place):
        (mapping,) = self.node(place)["mappings"]
        return mapping

    def case(self, name):
        (case,) = [case for case in self.data["cases"] if case["name"] == name]
        return json.loads((self.out / case["file"]).read_text(encoding="utf-8"))

    def shown_text(self):
        parser = ShownText()
        parser.feed(self.page)
        return " ".join(parser.parts)


@pytest.fixture(scope="module")
def explorer(tmp_path_factory):
    adapter = tmp_path_factory.mktemp("adapter")
    commit = an_adapter(adapter)
    vocabulary = tmp_path_factory.mktemp("vocabulary")
    write(vocabulary / "ontologies" / "example.ttl", PREFIXES + VOCABULARY)
    out = tmp_path_factory.mktemp("explorer")
    adapter_explorer.main(
        [
            str(adapter),
            "--vocabulary",
            str(vocabulary),
            "--repository",
            REPOSITORY,
            "--report",
            REPORT,
            "--out",
            str(out),
        ]
    )
    return Explorer(out, commit)


class TestAnAdaptersExplorer:
    """An adapter's explorer · scripts/adapter_explorer.py

    One page per adapter, for a reader asking how the adapter handles a kind of record, a code, a date or a reference.
    """

    class TestGivenAnAdapterCheckout:
        def test_nests_its_source_paths_by_place_with_each_form_of_a_place_on_one_node(self, explorer):
            """nests its source paths by place, with each form of a place on one node"""
            category = explorer.node("/category")
            coding = explorer.node("/category/coding")
            assert [child["place"] for child in category["children"]] == ["/category/coding", "/category/text"]
            assert "/category/coding/code" in [child["place"] for child in coding["children"]]
            (code,) = explorer.node("/category/coding/code")["mappings"]
            assert sorted(form["path"] for form in code["forms"]) == [
                "/category/coding/code",
                "/item/category/coding/code",
            ]

        def test_rolls_a_folded_node_up_from_the_explicit_entries_under_it_only(self, explorer):
            """rolls a folded node up from the explicit entries under it only

            How one entry covers the paths below it is not yet specified, so a node no entry names has a roll-up from
            the entries below it and no verdict of its own.
            """
            assert explorer.node("/category")["rollUp"] == ["carried", "consumed", "noHome", "ignored"]
            assert explorer.node("/category/coding")["rollUp"] == ["carried", "consumed", "ignored"]
            subject = explorer.node("/subject")
            assert subject["mappings"] == []
            assert subject["rollUp"] == ["carried"]

        def test_finds_a_deep_node_by_its_path_or_by_a_term(self, explorer):
            """finds a deep node by its path or by a term"""
            by_path = [item["node"] for item in explorer.data["search"] if "coding/code" in item["text"]]
            by_term = [item["node"] for item in explorer.data["search"] if "category code" in item["text"]]
            deep = explorer.node("/category/coding/code")["id"]
            assert by_path == [deep]
            assert by_term == [deep]
            assert f'id="{deep}"' in explorer.page

        def test_shows_a_carried_mapping_with_what_it_becomes_the_query_that_writes_it_and_its_test_case(
            self, explorer
        ):
            """shows a carried mapping with what it becomes, the query that writes it and its test case

            The test case is the smallest whose input holds the place and whose expected graph holds the property on
            the class.
            """
            mapping = explorer.mapping("/category/coding/code")
            assert mapping["verdict"] == "carried"
            assert mapping["becomes"] == [
                {
                    "kind": "Observation",
                    "class": {"term": "ex:Observation", "label": "Observation"},
                    "property": {"term": "ex:categoryCode", "label": "Category code"},
                }
            ]
            assert mapping["queries"] == ["in/observation.rq"]
            assert mapping["case"] == "category-coded"
            subject = explorer.mapping("/subject/reference")
            assert (subject["queries"], subject["case"]) == (["in/observation.rq"], "subject-only")
            case = explorer.case("category-coded")
            assert '"vital-signs"' in case["input"]["text"]
            assert "ex:categoryCode" in case["expectedGraph"]["text"]
            assert "expectedFindings" not in case

        def test_shows_a_path_not_carried_with_its_reason_and_a_gap_with_the_case_that_reports_it(self, explorer):
            """shows a path not carried with its reason, and a gap with the case that reports it

            A path that becomes nothing and opens no gap is held to nothing a case can show.
            """
            ignored = explorer.mapping("/category/coding/display")
            assert (ignored["verdict"], ignored["because"]) == ("ignored", "A display repeats what its code says.")
            assert ignored["case"] is None
            gap = explorer.mapping("/category/text")
            assert gap["verdict"] == "noHome"
            assert gap["gap"]["label"] == "A category's text has no Cascade predicate."
            assert gap["gap"]["issues"] == ["https://github.com/example/example-adapter/issues/4"]
            assert gap["queries"] == ["in/findings.rq"]
            assert gap["case"] == "category-coded-at-length"
            assert "exa:categoryTextNotCarried" in explorer.case(gap["case"])["expectedFindings"]["text"]

        def test_lists_its_kinds_of_record_its_concerns_and_what_it_does_not_carry(self, explorer):
            """lists its kinds of record, its concerns and what it does not carry"""
            code = explorer.node("/category/coding/code")["id"]
            (kind,) = explorer.data["kinds"]
            assert kind["kind"] == "Observation"
            assert {
                "class": {"term": "ex:Observation", "label": "Observation"},
                "property": {"term": "ex:categoryCode", "label": "Category code"},
                "nodes": [code],
            } in kind["becomes"]
            (codes,) = explorer.data["concerns"]
            assert (codes["concern"], codes["nodes"]) == ("concernCodes", [code])
            reasons = {reason["reason"]: reason["nodes"] for reason in explorer.data["notCarried"]}
            assert reasons == {
                "A category's text has no Cascade predicate.": [explorer.node("/category/text")["id"]],
                "A display repeats what its code says.": [explorer.node("/category/coding/display")["id"]],
            }

        def test_names_its_version_and_commit_in_the_header(self, explorer):
            """names its version and commit in the header"""
            header = explorer.page.split("</header>")[0]
            assert "0.4.1" in header
            assert f"{REPOSITORY}/tree/{explorer.commit}" in header
            assert explorer.commit[:7] in header

        def test_gives_rough_figures_and_links_never_an_exact_count(self, explorer):
            """gives rough figures and links, never an exact count"""
            shown = explorer.shown_text()
            entries = [
                form for node in explorer.nodes(explorer.data["tree"]) for m in node["mappings"] for form in m["forms"]
            ]
            exact = {len(INPUTS), len(entries)}
            assert exact == {3, 8}
            assert not [count for count in exact if re.search(rf"\b{count}\b", shown)], shown
            assert f'href="{REPORT}"' in explorer.page
            assert f'href="{REPOSITORY}/blob/{explorer.commit}/vocab/accounting.ttl"' in explorer.page
