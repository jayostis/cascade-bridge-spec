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
            "version": "0.7.1",
            "bridge:vocabularyFile": ["ontologies/example.ttl"],
            "bridge:envelope": [{"@id": "#envelope-listing"}, {"@id": "#envelope-record"}],
            "bridge:mapping": [{"@id": "in/observation.rq"}, {"@id": "in/absent.rq"}],
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
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
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
[] a bridge:PathEntry ; bridge:sourcePath "/note/text" ; bridge:verdict bridge:carried ;
  bridge:carriedAs [ bridge:inSourceRecordType "Observation" ; bridge:inRecordClass ex:Observation ;
                     bridge:asProperty ex:subject ] ,
                   [ bridge:inSourceRecordType "Observation" ; bridge:inRecordClass ex:Observation ;
                     bridge:asProperty ex:noteText ] .
[] a bridge:PathEntry ; bridge:sourcePath "/contained/subject/reference" ; bridge:verdict bridge:carried ;
  bridge:carriedAs [ bridge:inSourceRecordType "Observation" ; bridge:inRecordClass ex:Observation ;
                     bridge:asProperty ex:subject ] .
[] a bridge:PathEntry ; bridge:sourcePath "/note/display" ; bridge:verdict bridge:redundantWith ;
  bridge:sameFactAs "/contained/subject/reference" .
[] a bridge:PathEntry ; bridge:sourcePath "/_note/extension" ; bridge:verdict bridge:consumed .
[] a bridge:PathEntry ; bridge:sourcePath "/unit/value" ; bridge:verdict bridge:carried ;
  bridge:carriedAs [ bridge:inSourceRecordType "Unit" ; bridge:inRecordClass ex:Unit ;
                     bridge:asProperty ex:unitValue ] .
"""

GAPS = """
exa:gaps a skos:ConceptScheme .
exa:categoryTextNotCarried a skos:Concept ; skos:inScheme exa:gaps ;
  skos:prefLabel "A category's text has no Cascade predicate."@en ;
  skos:broader bridge:noPredicate ;
  rdfs:seeAlso <https://github.com/example/example-adapter/issues/8> .
"""

OBSERVATION_QUERY = """\
PREFIX ex: <https://example.org/vocab#>
CONSTRUCT {
  ?record a ex:Observation ;
    ex:categoryCode ?code ; # a code of the category
    ?subjectProperty ?subject ;
    ex:noteText ?text .
}
WHERE { ?record ex:read ?code . OPTIONAL { ?record ex:read ?subject BIND (ex:subject AS ?subjectProperty) } }
"""

ABSENT_QUERY = """PREFIX ex: <https://example.org/vocab#>
CONSTRUCT { ?absence ex:absentValueProperty ?property . }
WHERE { VALUES ?property { ex:categoryCode ex:subject } ?absence ex:read ?property }
"""

FINDINGS_QUERY = """\
PREFIX oa: <http://www.w3.org/ns/oa#>
PREFIX exa: <https://example.org/adapter#>
CONSTRUCT { ?finding oa:hasBody exa:categoryTextNotCarried . }
WHERE { ?finding oa:hasTarget ?text }
"""

MANIFEST = """
<> a mf:Manifest ; mf:entries ( <#category-coded> <#category-coded-at-length> <#subject-only> <#nothing-to-find> ) .

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

<#nothing-to-find> a bridge:IsomorphicConversionTest ; mf:name "nothing-to-find" ;
  mf:action [ bridge:input <in/nothing-to-find.json> ] ;
  mf:result [ bridge:expectedGraph <expected/nothing-to-find.ttl> ;
              bridge:expectedFindings <findings/nothing-to-find.ttl> ] .
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
    "nothing-to-find": {"unrelated": 1},
}

GRAPHS = {
    "category-coded": '<urn:r> a ex:Observation ; ex:categoryCode "vital-signs" ; ex:subject <urn:p> .',
    "category-coded-at-length": '<urn:r> a ex:Observation ; ex:categoryCode "vital-signs" ; ex:subject <urn:p> .',
    "subject-only": "<urn:r> a ex:Observation ; ex:subject <urn:p> .",
    "nothing-to-find": "",
}

FINDINGS = {
    "category-coded-at-length": """<urn:f> oa:hasBody exa:categoryTextNotCarried ;
  oa:hasTarget [ oa:hasSelector [ a oa:FragmentSelector ; rdf:value "" ;
    oa:refinedBy [ a oa:FragmentSelector ; rdf:value "/category/text" ] ] ] .""",
    "nothing-to-find": "",
}

VOCABULARY = """
ex:Observation rdfs:label "Observation"@en .
ex:Unit rdfs:label "Unit"@en .
ex:unitValue rdfs:label "Unit value"@en .
ex:categoryCode rdfs:label "Category code"@en .
ex:subject rdfs:label "Subject"@en .
ex:noteText rdfs:label "Note text"@en .
"""


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def an_adapter(folder):
    write(folder / "ro-crate-metadata.json", json.dumps(CRATE, indent=2))
    write(folder / "vocab" / "accounting.ttl", PREFIXES + ACCOUNTING)
    write(folder / "vocab" / "gaps.ttl", PREFIXES + GAPS)
    write(folder / "in" / "observation.rq", OBSERVATION_QUERY)
    write(folder / "in" / "absent.rq", ABSENT_QUERY)
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


VOID = {"meta", "link", "input", "br", "img", "wbr", "hr", "source"}


class Element:
    def __init__(self, tag, attrs, parent=None):
        self.tag, self.attrs, self.parent, self.children = tag, dict(attrs), parent, []

    @property
    def classes(self):
        return (self.attrs.get("class") or "").split()

    def text(self):
        if self.tag in ("script", "style"):
            return ""
        return " ".join(" ".join(c.split()) if isinstance(c, str) else c.text() for c in self.children).strip()

    def all(self, test=lambda element: True):
        for child in self.children:
            if isinstance(child, Element):
                if test(child):
                    yield child
                yield from child.all(test)

    def having(self, name, value=None):
        return [
            element
            for element in self.all()
            if name in element.attrs and (value is None or element.attrs[name] == value)
        ]

    def by_class(self, name):
        return [element for element in self.all() if name in element.classes]

    def rows(self):
        return [
            [cell.text() for cell in row.all(lambda c: c.tag in ("td", "th"))]
            for row in self.all(lambda r: r.tag == "tr")
        ]


class Tree(HTMLParser):
    def __init__(self, page):
        super().__init__()
        self.root = self.at = Element("document", {})
        self.feed(page)

    def handle_starttag(self, tag, attrs):
        element = Element(tag, attrs, self.at)
        self.at.children.append(element)
        if tag not in VOID:
            self.at = element

    def handle_startendtag(self, tag, attrs):
        self.at.children.append(Element(tag, attrs, self.at))

    def handle_endtag(self, tag):
        at = self.at
        while at is not self.root and at.tag != tag:
            at = at.parent
        if at is not self.root:
            self.at = at.parent

    def handle_data(self, data):
        self.at.children.append(data)


class Explorer:
    def __init__(self, out, commit):
        self.out = out
        self.commit = commit
        self.data = json.loads((out / "explorer.json").read_text(encoding="utf-8"))
        self.page = (out / "index.html").read_text(encoding="utf-8")
        self.dom = Tree(self.page).root

    def by_id(self, id_):
        (element,) = self.dom.having("id", id_)
        return element

    def style(self):
        return self.page.split("<style>")[1].split("</style>")[0]

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
def checkout(tmp_path_factory):
    adapter = tmp_path_factory.mktemp("adapter")
    commit = an_adapter(adapter)
    vocabulary = tmp_path_factory.mktemp("vocabulary")
    write(vocabulary / "ontologies" / "example.ttl", PREFIXES + VOCABULARY)
    return adapter, vocabulary, commit


def explore(tmp_path_factory, checkout, *more):
    adapter, vocabulary, commit = checkout
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
            *more,
        ]
    )
    return Explorer(out, commit)


@pytest.fixture(scope="module")
def explorer(tmp_path_factory, checkout):
    return explore(tmp_path_factory, checkout)


@pytest.fixture(scope="module")
def explorer_with_a_way_back(tmp_path_factory, checkout):
    return explore(tmp_path_factory, checkout, "--way-back", "Adapters", "../index.html")


@pytest.fixture(scope="module")
def explorer_with_stylesheets(tmp_path_factory, checkout):
    return explore(
        tmp_path_factory, checkout, "--stylesheet", "https://fonts.example/faces.css", "--stylesheet", "../../site.css"
    )


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
                    "queries": ["in/observation.rq"],
                }
            ]
            assert mapping["case"] == "category-coded"
            subject = explorer.mapping("/subject/reference")
            assert ([becomes["queries"] for becomes in subject["becomes"]], subject["case"]) == (
                [["in/observation.rq"]],
                "subject-only",
            )
            case = explorer.case("category-coded")
            assert '"vital-signs"' in case["input"]["text"]
            assert "ex:categoryCode" in case["expectedGraph"]["text"]
            assert "expectedFindings" not in case

        def test_names_a_query_as_writing_a_property_only_where_the_property_is_in_a_template_predicate(self, explorer):
            """names a query as writing a property only where the property is in a template predicate

            A query that names the property as a value only, bound to a variable the template writes as an object,
            does not write it, and a query lists once however many of the mapping's properties it writes.
            """
            code = explorer.mapping("/category/coding/code")
            assert code["becomes"][0]["queries"] == ["in/observation.rq"]
            note = explorer.mapping("/note/text")
            assert {becomes["property"]["term"]: becomes["queries"] for becomes in note["becomes"]} == {
                "ex:subject": ["in/observation.rq"],
                "ex:noteText": ["in/observation.rq"],
            }

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
            assert gap["gap"]["issues"] == ["https://github.com/example/example-adapter/issues/8"]
            assert gap["queries"] == ["in/findings.rq"]
            assert gap["case"] == "category-coded-at-length"
            assert "exa:categoryTextNotCarried" in explorer.case(gap["case"])["expectedFindings"]["text"]

        def test_lists_its_kinds_of_record_its_concerns_and_what_it_does_not_carry(self, explorer):
            """lists its kinds of record, its concerns and what it does not carry"""
            code = explorer.node("/category/coding/code")["id"]
            (kind,) = [kind for kind in explorer.data["kinds"] if kind["kind"] == "Observation"]
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
            assert "0.7.1" in header
            assert f"{REPOSITORY}/tree/{explorer.commit}" in header
            assert explorer.commit[:7] in header

        def test_gives_rough_figures_and_links_never_an_exact_count(self, explorer):
            """gives rough figures and links, never an exact count"""
            nodes = list(explorer.nodes(explorer.data["tree"]))
            entries = [form for node in nodes for m in node["mappings"] for form in m["forms"]]
            counts = (len(entries), len(nodes), len(INPUTS))
            assert counts[0] == 12 and counts[2] == 4
            figures = explorer.page.split("It accounts for ")[1].split("</p>")[0]
            assert figures.startswith(
                f"{adapter_explorer.rough(counts[0])} source paths, at {adapter_explorer.rough(counts[1])} places, "
                f"and {adapter_explorer.rough(counts[2])}\ntest cases"
            ), figures
            assert not [count for count in counts if re.search(rf"\b{count}\b", figures)], figures
            by_verdict = {
                item["verdict"]: len(
                    [
                        f
                        for node in nodes
                        for m in node["mappings"]
                        if m["verdict"] == item["verdict"]
                        for f in m["forms"]
                    ]
                )
                for item in explorer.data["verdicts"]
            }
            assert by_verdict["carried"] == 6 and by_verdict["consumed"] == 3 and by_verdict["carriedInPart"] == 0
            overview = explorer.by_id("overview")
            shown = {
                row[0]: row[-1]
                for row in overview.rows()
                if row and row[0] in {v["words"] for v in explorer.data["verdicts"]}
            }
            assert shown == {
                item["words"]: adapter_explorer.rough(by_verdict[item["verdict"]]) for item in explorer.data["verdicts"]
            }
            exact = {count for count in (*counts, *by_verdict.values()) if count > 1}
            assert not [count for count in exact if re.search(rf"\b{count}\b", overview.text())], overview.text()
            assert f'href="{REPORT}"' in explorer.page
            assert f'href="{REPOSITORY}/blob/{explorer.commit}/vocab/accounting.ttl"' in explorer.page

        def test_opens_on_an_overview_of_where_its_entries_go_and_its_kinds_of_record_as_a_table(self, explorer):
            """opens on an overview of where its entries go and its kinds of record, as a table

            With no place selected the overview is what the middle pane shows: a bar of the verdicts' shares, a row per
            verdict and a row per kind of record in the source, with the classes it becomes.
            """
            overview = explorer.by_id("overview")
            assert "view" in overview.classes
            assert re.search(
                r":not\(:has\(\.view:target\)\)[^{}]*#overview[^{}]*\{[^}]*display: *block", explorer.style()
            )
            (bar,) = overview.by_class("ledger-bar")
            assert [segment.classes for segment in bar.all()] == [
                ["s-carried"],
                ["s-redundantWith"],
                ["s-consumed"],
                ["s-noHome"],
                ["s-ignored"],
            ]
            kinds = {row[0]: row[1] for row in overview.rows() if row and row[0] in ("Observation", "Unit")}
            assert kinds == {"Observation": "Observation ex:Observation", "Unit": "Unit ex:Unit"}

        def test_stops_at_its_overview_paths_kinds_concerns_what_it_does_not_carry_and_its_test_cases(self, explorer):
            """stops at its overview, paths, kinds, concerns, what it does not carry and its test cases"""
            (bar,) = explorer.dom.all(lambda element: element.tag == "nav")
            stops = [(stop.attrs["href"], stop.text()) for stop in bar.by_class("stop")]
            assert stops == [
                ("#overview", "Overview"),
                ("#paths", "Source paths"),
                ("#kinds", "Kinds of record"),
                ("#concerns", "By concern"),
                ("#not-carried", "Not carried"),
                ("#cases", "Test cases"),
            ]
            for href, _ in stops:
                assert "view" in explorer.by_id(href[1:]).classes

        def test_lists_each_place_as_a_row_of_its_tree_with_a_pill_for_one_verdict_and_a_bar_for_several(
            self, explorer
        ):
            """lists each place as a row of its tree, with a pill for one verdict and a bar for several

            Underscore paths, which FHIR uses for what extends a value, come after the rest.
            """
            tree = explorer.by_id("tree")
            rows = {row.attrs["data-node"]: row for row in tree.having("data-node")}
            assert sorted(rows) == sorted(node["id"] for node in explorer.nodes(explorer.data["tree"]))
            display = rows[explorer.node("/category/coding/display")["id"]]
            assert [pill.text() for pill in display.by_class("v")] == ["ignored"]
            assert "v-ignored" in display.by_class("v")[0].classes
            (bar,) = rows[explorer.node("/category")["id"]].by_class("mb")
            assert [segment.classes for segment in bar.all()] == [
                ["s-carried"],
                ["s-consumed"],
                ["s-noHome"],
                ["s-ignored"],
            ]
            assert [node["step"] for node in explorer.data["tree"]] == ["category", "note", "subject", "unit", "_note"]

        def test_shows_each_places_detail_once_by_its_target(self, explorer):
            """shows each place's detail once, by its target"""
            for node in explorer.nodes(explorer.data["tree"]):
                (detail,) = explorer.dom.having("id", node["id"])
                assert detail.tag == "article" and "view" in detail.classes, node["place"]
                assert detail.parent.attrs.get("id") == "views"
            assert re.search(r"\.view:target[^{}]*\{[^}]*display: *block", explorer.style())

        def test_shows_what_a_path_becomes_as_a_table(self, explorer):
            """shows what a path becomes as a table"""
            detail = explorer.by_id(explorer.node("/category/coding/code")["id"])
            (table,) = detail.all(lambda element: element.tag == "table")
            assert table.rows() == [
                ["property", "on the class", "in the kind", "written by"],
                ["Category code ex:categoryCode", "Observation ex:Observation", "Observation", "in/observation.rq"],
            ]

        def test_puts_no_article_before_a_class_or_a_kind_in_what_a_path_becomes(self, explorer):
            """puts no article before a class or a kind in what a path becomes

            English a and an follow how a word is said, which no spelling rule covers, so the page names the class and the kind
            without one.
            """
            assert not hasattr(adapter_explorer, "an")
            assert not re.search(r"\b(on|in) an? (<span|<code|[A-Z])", explorer.page)

        def test_marks_where_a_finding_points_in_the_input_and_the_term_a_mapping_names_in_the_graph(self, explorer):
            """marks where a finding points in the input, and the term a mapping names in the graph

            A finding's selector is a JSON Pointer, refined from the record's own; the input's line is where the pointer
            lands. The graph's lines are each that names the property the path becomes.
            """

            def marks(place):
                (link,) = explorer.by_id(explorer.node(place)["id"]).having("data-case")
                return link.attrs["data-case"], json.loads(link.attrs["data-marks"])

            file, marked = marks("/category/text")
            case = json.loads((explorer.out / file).read_text(encoding="utf-8"))
            lines = case["input"]["text"].split("\n")
            assert [lines[at - 1].strip() for at in marked["input"]] == ['"text": "Vital signs"']
            findings = case["expectedFindings"]["text"].split("\n")
            assert [findings[at - 1].split()[-2] for at in marked["expectedFindings"]] == ["exa:categoryTextNotCarried"]
            file, marked = marks("/category/coding/code")
            graph = json.loads((explorer.out / file).read_text(encoding="utf-8"))["expectedGraph"]["text"].split("\n")
            assert [graph[at - 1] for at in marked["expectedGraph"]] == [GRAPHS["category-coded"]]
            assert "input" not in marked

        def test_lists_the_plain_form_of_a_place_before_its_contained_form(self, explorer):
            """lists the plain form of a place before its contained form"""
            subject = explorer.mapping("/subject/reference")
            assert [form["path"] for form in subject["forms"]] == ["/subject/reference", "/contained/subject/reference"]

        def test_names_the_plain_form_in_the_same_fact_as(self, explorer):
            """names the plain form in "The same fact as"

            The accounting names the contained form; the page names the plain form of the same place.
            """
            same = explorer.mapping("/note/display")["sameFactAs"]
            assert same["path"] == "/subject/reference"
            assert same["node"] == explorer.node("/subject/reference")["id"]
            assert f'The same fact as <a href="#{same["node"]}"><code>/subject/reference</code></a>.' in explorer.page

        def test_says_in_words_that_a_case_with_an_empty_findings_file_expects_no_findings(self, explorer):
            """says in words that a case with an empty findings file expects no findings"""
            empty = explorer.case("nothing-to-find")["expectedFindings"]
            assert empty["empty"] is True
            assert explorer.case("category-coded-at-length")["expectedFindings"]["empty"] is False
            assert "This case expects no findings" in explorer.page

        def test_declares_no_dark_colour_scheme(self, explorer):
            """declares no dark colour scheme"""
            assert "prefers-color-scheme" not in explorer.page
            assert "dark" not in explorer.page.split("</style>")[0]

        def test_leaves_room_above_a_section_a_link_scrolls_to(self, explorer):
            """leaves room above a section a link scrolls to

            The bar is 9 rem tall at 320 px and 7.4 rem at 400 px, so the room is the bar's own height, which the page sets.
            """
            style = explorer.style()
            assert re.search(r"\.view[^{}]*\{[^}]*scroll-margin-top: *calc\(var\(--bar,", style)
            assert re.search(r"\.row[^{}]*\{[^}]*scroll-margin-top: *calc\(var\(--bar,", style)
            assert 'setProperty("--bar"' in explorer.page.split("<script>")[-1]

        def test_declares_an_icon_so_a_browser_asks_for_no_favicon(self, explorer):
            """declares an icon so a browser asks for no favicon"""
            assert re.search(r'<link rel="icon" href="data:', explorer.page.split("</head>")[0])

        def test_narrows_its_tree_in_place_and_announces_how_many_places_match(self, explorer):
            """narrows its tree in place, and announces how many places match"""
            pane = explorer.by_id("paths-pane")
            (box,) = [element for element in pane.all() if element.tag == "input"]
            assert (box.attrs["type"], box.attrs["aria-controls"]) == ("search", "tree")
            assert pane.having("id", "count")[0].attrs["aria-live"] == "polite"
            assert not explorer.dom.having("id", "results")

        def test_narrows_its_tree_by_a_concern_a_verdict_or_a_reason_not_carried(self, explorer):
            """narrows its tree by a concern, a verdict or a reason not carried"""
            pane = explorer.by_id("paths-pane")
            assert [chip.attrs["data-concern"] for chip in pane.having("data-concern")] == ["", "concernCodes"]
            code = explorer.node("/category/coding/code")["id"]
            (row,) = explorer.by_id("tree").having("data-node", code)
            assert row.attrs["data-c"] == "concernCodes"
            verdicts = [element.attrs["data-verdict"] for element in explorer.by_id("overview").having("data-verdict")]
            assert verdicts == [item["verdict"] for item in explorer.data["verdicts"]]
            reasons = {
                element.text(): element.attrs["data-nodes"].split()
                for element in explorer.by_id("not-carried").having("data-nodes")
            }
            assert reasons == {
                "A category's text has no Cascade predicate.": [explorer.node("/category/text")["id"]],
                "A display repeats what its code says.": [explorer.node("/category/coding/display")["id"]],
            }

        def test_folds_its_panes_to_tabs_on_a_narrow_screen_with_rows_a_thumb_can_hit(self, explorer):
            """folds its panes to tabs on a narrow screen, with rows a thumb can hit"""
            tabs = [tab.attrs["aria-controls"] for tab in explorer.by_id("tabs").all(lambda e: e.tag == "button")]
            assert tabs == ["paths-pane", "views-pane", "case-pane"]
            narrow = explorer.style().split("@media (max-width: 760px)")[1]
            assert re.search(r"\.tabs[^{}]*\{[^}]*display: *grid", narrow)
            assert re.search(r"\.row[^{}]*\{[^}]*min-height: *32px", narrow)

        def test_names_the_sites_tokens_each_with_one_fallback(self, explorer):
            """names the site's tokens, each with one fallback

            The page reads the site's tokens by name, so a stylesheet linked ahead of it restyles it, and falls back to the
            site's values when none is.
            """
            fallbacks = {}
            for name, value in re.findall(r"var\((--[\w-]+), *([^()]*(?:\([^()]*\))?[^()]*)\)", explorer.style()):
                fallbacks.setdefault(name, set()).add(value.strip())
            assert {
                "--ink",
                "--paper",
                "--rule",
                "--link",
                "--pencil",
                "--muted",
                "--serif",
                "--sans",
                "--mono",
            } <= set(fallbacks)
            assert {name: values for name, values in fallbacks.items() if len(values) > 1} == {}
            assert not re.search(r"var\(--(?!bar\b)[\w-]+\)", explorer.style())
            assert not re.search(r"(^|\n)\s*:root\s*\{", explorer.style())

    class TestGivenAStylesheet:
        def test_links_each_stylesheet_ahead_of_its_own_in_the_order_given(self, explorer_with_stylesheets):
            """links each stylesheet ahead of its own, in the order given"""
            head = explorer_with_stylesheets.page.split("</head>")[0]
            links = re.findall(r'<link rel="stylesheet" href="([^"]*)">', head)
            assert links == ["https://fonts.example/faces.css", "../../site.css"]
            assert head.index("../../site.css") < head.index("<style>")

        def test_links_none_without_one(self, explorer):
            """links none without one"""
            assert 'rel="stylesheet"' not in explorer.page

    class TestGivenAWayBack:
        def test_links_back_from_the_bar_and_from_the_end_of_the_page(self, explorer_with_a_way_back):
            """links back from the bar and from the end of the page"""
            page = explorer_with_a_way_back.page
            link = '<a href="../index.html">Adapters</a>'
            assert link in page.split("<nav>")[1].split("</nav>")[0]
            assert link in page.split("</main>")[1]

        def test_links_nowhere_back_without_one(self, explorer):
            """links nowhere back without one"""
            assert "../index.html" not in explorer.page
            assert "<footer" not in explorer.page
