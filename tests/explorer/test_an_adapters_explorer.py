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
            "bridge:pathOfRecordKindBelowContent": "/resourceType",
        },
        {
            "@id": "#envelope-record",
            "@type": "bridge:Envelope",
            "name": "record",
            "bridge:pathOfContentInRecord": "",
            "bridge:pathOfContainedContentBelowContent": "/contained",
            "bridge:pathOfRecordKindBelowContent": "/resourceType",
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
    "category-coded": {
        "resourceType": "Observation",
        "category": {"coding": [{"code": "vital-signs"}], "text": "Vital signs"},
    },
    "category-coded-at-length": {
        "resourceType": "Observation",
        "category": {"coding": [{"code": "vital-signs", "display": "Vital signs"}], "text": "Vital signs"},
        "subject": {"reference": "Patient/a"},
        "note": "Taken at length, the record a reader should not be shown first.",
    },
    "subject-only": {
        "resourceType": "Observation",
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
ex:Document rdfs:label "Document"@en .
ex:Finding rdfs:label "Finding"@en .
ex:Other rdfs:label "Other"@en .
"""


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


SHARED_ACCOUNTING = """
[] a bridge:PathEntry ; bridge:sourcePath "/shared/first" ; bridge:verdict bridge:noHome ;
  bridge:namesGap exa:categoryTextNotCarried .
[] a bridge:PathEntry ; bridge:sourcePath "/shared/second" ; bridge:verdict bridge:noHome ;
  bridge:namesGap exa:categoryTextNotCarried .
"""

SHARED_MANIFEST = """
<> a mf:Manifest ; mf:entries ( <#two-places> ) .

<#two-places> a bridge:IsomorphicConversionTest ; mf:name "two-places" ;
  mf:action [ bridge:input <in/two-places.json> ] ;
  mf:result [ bridge:expectedGraph <expected/two-places.ttl> ;
              bridge:expectedFindings <findings/two-places.ttl> ] .
"""

SHARED_FINDINGS = """<urn:f1> oa:hasBody exa:categoryTextNotCarried ;
  oa:hasTarget [ oa:hasSelector [ a oa:FragmentSelector ; rdf:value "/shared/first" ] ] .
<urn:f2> oa:hasBody exa:categoryTextNotCarried ;
  oa:hasTarget [ oa:hasSelector [ a oa:FragmentSelector ; rdf:value "/shared/second" ] ] ."""

CARRIED_TOGETHER_ACCOUNTING = """
[] a bridge:PathEntry ; bridge:sourcePath "/shared/first" ; bridge:verdict bridge:carried ;
  bridge:carriedAs [ bridge:inSourceRecordType "Observation" ; bridge:inRecordClass ex:Observation ;
                     bridge:asProperty ex:subject ] .
[] a bridge:PathEntry ; bridge:sourcePath "/contained/shared/first" ; bridge:verdict bridge:carried ;
  bridge:carriedAs [ bridge:inSourceRecordType "Observation" ; bridge:inRecordClass ex:Observation ;
                     bridge:asProperty ex:subject ] .
[] a bridge:PathEntry ; bridge:sourcePath "/shared/second" ; bridge:verdict bridge:carried ;
  bridge:carriedAs [ bridge:inSourceRecordType "Observation" ; bridge:inRecordClass ex:Observation ;
                     bridge:asProperty ex:noteText ] ,
                   [ bridge:inSourceRecordType "Unit" ; bridge:inRecordClass ex:Unit ;
                     bridge:asProperty ex:unitValue ] .
"""

CARRIED_TOGETHER_MANIFEST = """
<> a mf:Manifest ; mf:entries ( <#two-places> ) .

<#two-places> a bridge:IsomorphicConversionTest ; mf:name "two-places" ;
  mf:action [ bridge:input <in/two-places.json> ] ;
  mf:result [ bridge:expectedGraph <expected/two-places.ttl> ] .
"""

CARRIED_TOGETHER_INPUT = {
    "resourceType": "Observation",
    "shared": {"first": "a", "second": "b"},
    "contained": [{"resourceType": "Unit", "shared": {"first": "c"}}],
}

XML_CRATE = {
    "@context": CRATE["@context"],
    "@graph": [
        CRATE["@graph"][0],
        {
            "@id": "./",
            "@type": ["Dataset", "bridge:Adapter"],
            "identifier": "example-xml",
            "name": "Example XML",
            "version": "0.2.0",
            "bridge:vocabularyFile": ["ontologies/example.ttl"],
            "bridge:envelope": [{"@id": "#envelope-document"}],
            "bridge:elementNameOfEachRecord": "doc",
            "bridge:sourceRecordTypesAreIdentifiers": True,
            "bridge:mapping": [{"@id": "in/document.rq"}],
            "bridge:gapScheme": {"@id": "vocab/gaps.ttl"},
            "bridge:sourceAccounting": {"@id": "vocab/accounting.ttl"},
            "bridge:testManifest": {"@id": "fixtures/manifest.ttl"},
        },
        {
            "@id": "#envelope-document",
            "@type": "bridge:Envelope",
            "name": "document",
            "bridge:docRootElementName": "doc",
        },
    ],
}


def xpath(*steps):
    return "".join(
        f"/@{step[1:]}" if step.startswith("@") else f"/*[local-name()='{step}' and namespace-uri()='urn:x']"
        for step in steps
    )


OBSERVATION = ("doc", "section", "entry", "observation")
XML_ACCOUNTING = f"""
[] a skos:Concept ; skos:notation "1.1" ; skos:prefLabel "Header"@en .
[] a skos:Concept ; skos:notation "2.1" ; skos:prefLabel "First Section"@en .
[] a skos:Concept ; skos:notation "2.2" ; skos:prefLabel "Second Section"@en .
[] a skos:Concept ; skos:notation "4.1" ; skos:prefLabel "Finding Observation"@en .
[] a skos:Concept ; skos:notation "4.2" ; skos:prefLabel "Other Observation"@en .
[] a bridge:PathEntry ; bridge:sourcePath "{xpath("doc", "title")}" ; bridge:verdict bridge:carried ;
  bridge:carriedAs [ bridge:inSourceRecordType "1.1" ; bridge:inRecordClass ex:Document ; bridge:asProperty ex:title ] .
[] a bridge:PathEntry ; bridge:sourcePath "{xpath(*OBSERVATION, "value", "@value")}" ; bridge:verdict bridge:carried ;
  bridge:carriedAs [ bridge:inSourceRecordType "4.1" ; bridge:inRecordClass ex:Finding ;
                     bridge:asProperty ex:findingValue ] .
[] a bridge:PathEntry ; bridge:sourcePath "{xpath(*OBSERVATION, "value", "@value")}" ; bridge:verdict bridge:carried ;
  bridge:carriedAs [ bridge:inSourceRecordType "4.2" ; bridge:inRecordClass ex:Other ; bridge:asProperty ex:otherValue ] .
[] a bridge:PathEntry ; bridge:sourcePath "{xpath(*OBSERVATION, "code", "@code")}" ; bridge:verdict bridge:carried ;
  bridge:carriedAs [ bridge:inSourceRecordType "4.1" ; bridge:inRecordClass ex:Finding ;
                     bridge:asProperty ex:findingCode ] .
[] a bridge:PathEntry ; bridge:sourcePath "{xpath("doc", "section", "code", "@code")}" ; bridge:verdict bridge:carried ;
  bridge:carriedAs [ bridge:inSourceRecordType "4.1" ; bridge:inRecordClass ex:Finding ;
                     bridge:asProperty ex:findingSection ] .
[] a bridge:PathEntry ; bridge:sourcePath "{xpath("doc", "id", "@root")}" ; bridge:verdict bridge:carried ;
  bridge:carriedAs [ bridge:inRecordClass ex:Document ; bridge:asProperty ex:documentId ] .
"""

XML_QUERY = """\
PREFIX ex: <https://example.org/vocab#>
CONSTRUCT {
  ?document a ex:Document ; ex:title ?title ; ex:documentId ?id .
  ?finding a ex:Finding ; ex:findingValue ?value ; ex:findingCode ?code ; ex:findingSection ?section .
  ?other a ex:Other ; ex:otherValue ?otherValue .
}
WHERE { ?document ex:read ?title }
"""

XML_MANIFEST = """
<> a mf:Manifest ; mf:entries ( <#two-sections> ) .

<#two-sections> a bridge:IsomorphicConversionTest ; mf:name "two-sections" ;
  mf:action [ bridge:input <in/two-sections.xml> ] ;
  mf:result [ bridge:expectedGraph <expected/two-sections.ttl> ] .
"""

XML_INPUT = """\
<doc xmlns="urn:x">
  <templateId root="1.1"/>
  <id root="d1"/>
  <title>A document</title>
  <section>
    <templateId root="2.1"/>
    <code code="s1"/>
    <entry>
      <observation>
        <templateId root="4.1"/>
        <statusCode code=""/>
        <code code="a"/>
        <value value="1"/>
      </observation>
    </entry>
    <entry>
      <observation>
        <code code="z"/>
        <value value="9"/>
      </observation>
    </entry>
  </section>
  <section>
    <templateId root="2.2"/>
    <code code="s2"/>
    <entry>
      <observation>
        <templateId root="4.2"/>
        <code code="b"/>
        <value value="2"/>
      </observation>
    </entry>
  </section>
</doc>
"""

XML_GRAPH = """<urn:d> a ex:Document ; ex:title "A document" ; ex:documentId "d1" .
<urn:f> a ex:Finding ; ex:findingValue "1" ; ex:findingCode "a" ; ex:findingSection "s1" .
<urn:o> a ex:Other ; ex:otherValue "2" .
"""


def an_adapter(
    folder, accounting=ACCOUNTING, manifest=MANIFEST, inputs=INPUTS, graphs=GRAPHS, findings=FINDINGS, crate=CRATE
):
    write(folder / "ro-crate-metadata.json", json.dumps(crate, indent=2))
    write(folder / "vocab" / "accounting.ttl", PREFIXES + accounting)
    write(folder / "vocab" / "gaps.ttl", PREFIXES + GAPS)
    write(folder / "in" / "observation.rq", OBSERVATION_QUERY)
    write(folder / "in" / "absent.rq", ABSENT_QUERY)
    write(folder / "in" / "findings.rq", FINDINGS_QUERY)
    write(folder / "fixtures" / "manifest.ttl", PREFIXES + manifest)
    for name, record in inputs.items():
        write(folder / "fixtures" / "in" / f"{name}.json", json.dumps(record, indent=2))
        write(folder / "fixtures" / "expected" / f"{name}.ttl", PREFIXES + graphs[name])
    for name, text in findings.items():
        write(folder / "fixtures" / "findings" / f"{name}.ttl", PREFIXES + text)
    return committed(folder)


def an_xml_adapter(folder):
    write(folder / "ro-crate-metadata.json", json.dumps(XML_CRATE, indent=2))
    write(folder / "vocab" / "accounting.ttl", PREFIXES + XML_ACCOUNTING)
    write(folder / "vocab" / "gaps.ttl", PREFIXES + GAPS)
    write(folder / "in" / "document.rq", XML_QUERY)
    write(folder / "fixtures" / "manifest.ttl", PREFIXES + XML_MANIFEST)
    write(folder / "fixtures" / "in" / "two-sections.xml", XML_INPUT)
    write(folder / "fixtures" / "expected" / "two-sections.ttl", PREFIXES + XML_GRAPH)
    return committed(folder)


def committed(folder):
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
        return " ".join(
            "".join(c if isinstance(c, str) else f" {c.text()} " * (c.tag != "wbr") for c in self.children).split()
        )

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

    def fragment(self, place):
        """What a reader's script fetches when it opens the place: the sections of its mappings."""
        file = self.by_id(self.node(place)["id"]).attrs["data-file"]
        return Tree((self.out / file).read_text(encoding="utf-8")).root

    def fragments(self):
        return sorted((self.out / "nodes").glob("*.html"))

    def everything(self):
        return self.page + "".join(file.read_text(encoding="utf-8") for file in self.fragments())

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


@pytest.fixture(scope="module")
def explorer_with_two_places_sharing_a_gap(tmp_path_factory):
    adapter = tmp_path_factory.mktemp("adapter")
    commit = an_adapter(
        adapter,
        accounting=SHARED_ACCOUNTING,
        manifest=SHARED_MANIFEST,
        inputs={"two-places": {"shared": {"first": "a", "second": "b"}}},
        graphs={"two-places": ""},
        findings={"two-places": SHARED_FINDINGS},
    )
    vocabulary = tmp_path_factory.mktemp("vocabulary")
    write(vocabulary / "ontologies" / "example.ttl", PREFIXES + VOCABULARY)
    return explore(tmp_path_factory, (adapter, vocabulary, commit))


@pytest.fixture(scope="module")
def explorer_with_two_places_carried_from_one_case(tmp_path_factory):
    adapter = tmp_path_factory.mktemp("adapter")
    commit = an_adapter(
        adapter,
        accounting=CARRIED_TOGETHER_ACCOUNTING,
        manifest=CARRIED_TOGETHER_MANIFEST,
        inputs={"two-places": CARRIED_TOGETHER_INPUT},
        graphs={"two-places": '<urn:r> a ex:Observation ; ex:subject <urn:p> ; ex:noteText "b" .'},
        findings={},
    )
    vocabulary = tmp_path_factory.mktemp("vocabulary")
    write(vocabulary / "ontologies" / "example.ttl", PREFIXES + VOCABULARY)
    return explore(tmp_path_factory, (adapter, vocabulary, commit))


@pytest.fixture(scope="module")
def xml_explorer(tmp_path_factory):
    adapter = tmp_path_factory.mktemp("adapter")
    commit = an_xml_adapter(adapter)
    vocabulary = tmp_path_factory.mktemp("vocabulary")
    write(vocabulary / "ontologies" / "example.ttl", PREFIXES + VOCABULARY)
    return explore(tmp_path_factory, (adapter, vocabulary, commit))


def drawings(explorer):
    """The overview's drawings, the wide one first."""
    return sorted(
        explorer.by_id("overview").all(lambda element: element.tag == "svg"),
        key=lambda svg: "narrow" in svg.classes,
    )


def input_marks(explorer, place, case="two-places"):
    """Each mapping's marked lines of the case's input at a place, stripped, by what the mapping becomes."""
    lines = explorer.case(case)["input"]["text"].split("\n")
    out = {}
    sections = explorer.fragment(place).by_class("mapping")
    for mapping, section in zip(explorer.node(place)["mappings"], sections, strict=True):
        (link,) = section.having("data-case")
        marks = json.loads(link.attrs["data-marks"])
        out[mapping["becomes"][0]["property"]["term"]] = [lines[at - 1].strip() for at in marks.get("input", [])]
    return out


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

        def test_keeps_a_kinds_name_whole_in_what_a_path_becomes(self, explorer):
            """keeps a kind's name whole in what a path becomes"""
            assert re.search(r'td\[data-label="in the kind"\][^{}]*\{[^}]*overflow-wrap: *normal', explorer.style())

        def test_stacks_the_trace_until_its_three_boxes_fit_across(self, explorer):
            """stacks the trace until its three boxes fit across"""
            across = re.search(
                r"@container \(min-width: *(\d+)px\) \{[^@]*\.trace \{[^}]*grid-template-columns", explorer.style()
            )
            assert across and int(across[1]) >= 800

        def test_keeps_a_kinds_name_whole_and_wraps_what_it_becomes_instead(self, explorer):
            """keeps a kind's name whole, and wraps what it becomes instead"""
            style = explorer.style()
            assert re.search(r"table\.et\.kinds td\.mono[^{}]*\{[^}]*overflow-wrap: *normal", style)
            assert re.search(r"table\.et\.kinds [^{}]*\.term[^{}]*\{[^}]*overflow-wrap: *anywhere", style)

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

        def test_holds_no_mapping_in_the_page_itself(self, explorer):
            """holds no mapping in the page itself

            A page that held every place's mappings was 2.4 MB for a real adapter; a place's mappings are read when a
            reader opens the place.
            """
            assert not explorer.dom.by_class("mapping")
            assert 'class="mapping"' not in explorer.page

        def test_writes_for_every_place_with_mappings_a_fragment_holding_exactly_its_mappings(self, explorer):
            """writes for every place with mappings a fragment holding exactly its mappings"""
            nodes = list(explorer.nodes(explorer.data["tree"]))
            own = [node for node in nodes if node["mappings"]]
            assert len(own) > 1
            for node in own:
                file = explorer.by_id(node["id"]).attrs["data-file"]
                sections = Tree((explorer.out / file).read_text(encoding="utf-8")).root.by_class("mapping")
                assert len(sections) == len(node["mappings"]), node["place"]
            for node in nodes:
                if not node["mappings"]:
                    assert "data-file" not in explorer.by_id(node["id"]).attrs, node["place"]
            assert len(explorer.fragments()) == len(own)
            assert len({explorer.by_id(node["id"]).attrs["data-file"] for node in own}) == len(own)

        def test_fetches_a_places_fragment_when_the_place_is_selected(self, explorer):
            """fetches a place's fragment when the place is selected

            Selecting runs on a hash on arrival too, so a link to a place opens with its mappings.
            """
            script = explorer.page.split("<script>")[-1]
            assert "fetch(view.dataset.file)" in script
            select = script.split("function select(")[1].split("\nfunction ")[0]
            assert "openPlace(view)" in select

        def test_shows_what_a_path_becomes_as_a_table(self, explorer):
            """shows what a path becomes as a table"""
            detail = explorer.fragment("/category/coding/code")
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
            rows = {
                place: explorer.fragment(place).all(lambda element: element.tag == "table")
                for place in ("/unit/value", "/note/text")
            }
            assert [row[1:3] for row in next(rows["/unit/value"]).rows()[1:]] == [["Unit ex:Unit", "Unit"]]
            assert [row[1:3] for row in next(rows["/note/text"]).rows()[1:]] == [
                ["Observation ex:Observation", "Observation"]
            ] * 2
            assert not re.search(r"\b(on|in) an? (<span|<code|[A-Z])", explorer.everything())

        def test_marks_where_a_finding_points_in_the_input_and_the_term_a_mapping_names_in_the_graph(self, explorer):
            """marks where a finding points in the input, and the term a mapping names in the graph

            A finding's selector is a JSON Pointer, refined from the record's own; the input's line is where the pointer
            lands. The graph's lines are each that names the property the path becomes.
            """

            def marks(place):
                (link,) = explorer.fragment(place).having("data-case")
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

        def test_marks_where_a_path_that_raises_no_finding_lands_in_the_input(self, explorer):
            """marks where a path that raises no finding lands in the input

            The path is read from each record of the input the adapter's envelopes find, below where the record's
            content begins, in a record of a kind the path's mapping names.
            """
            assert input_marks(explorer, "/category/coding/code", "category-coded") == {
                "ex:categoryCode": ['"code": "vital-signs"']
            }
            (link,) = explorer.fragment("/category/coding/code").having("data-case")
            assert json.loads(link.attrs["data-marks"])["inputFrom"] == "path"
            (link,) = explorer.fragment("/category/text").having("data-case")
            assert "inputFrom" not in json.loads(link.attrs["data-marks"])
            script = explorer.page.split("<script>")[-1]
            assert "where this path lands in the input" in script

        def test_draws_each_kind_of_record_flowing_into_the_classes_it_becomes(self, explorer):
            """draws each kind of record flowing into the classes it becomes

            A line's weight is the number of properties the kind becomes on the class. The page draws a wide drawing
            and a narrow one for a phone, from the same data.
            """
            flow = explorer.data["flow"]
            assert flow == {
                "sources": [
                    {"label": "Observation", "kinds": ["Observation"]},
                    {"label": "Unit", "kinds": ["Unit"]},
                ],
                "classes": [
                    {"term": "ex:Observation", "label": "Observation"},
                    {"term": "ex:Unit", "label": "Unit"},
                ],
                "links": [
                    {"source": 0, "class": 0, "properties": 3},
                    {"source": 1, "class": 1, "properties": 1},
                ],
            }
            wide, narrow = drawings(explorer)
            assert "narrow" not in wide.classes and "narrow" in narrow.classes
            captions = [text.text() for text in wide.all(lambda element: element.tag == "text")][:2]
            assert captions == ["A kind of record in the source", "What it becomes in the pod"]
            for drawing in (wide, narrow):
                texts = [text.text() for text in drawing.all(lambda element: element.tag == "text")]
                for name in ("Observation", "Unit", "ex:Observation", "ex:Unit"):
                    assert name in texts, (name, texts)
                assert drawing.attrs["role"] == "img" and drawing.attrs["aria-label"]
                lines = list(drawing.all(lambda element: element.tag == "path"))
                assert len(lines) == len(flow["links"])
                widths = [float(line.attrs["stroke-width"]) for line in lines]
                assert widths[0] > widths[1]
                assert not re.search(r"\b[13]\b", " ".join(texts))

        def test_draws_in_colours_that_need_no_stylesheet(self, explorer):
            """draws in colours that need no stylesheet

            Each line and each word of a drawing carries its colour as an attribute, so a reader who opens the page
            without its styles sees no black shapes.
            """
            assert len(drawings(explorer)) == 2
            for drawing in drawings(explorer):
                for line in drawing.all(lambda element: element.tag == "path"):
                    assert line.attrs.get("fill") == "none" and line.attrs.get("stroke", "").startswith("#")
                for text in drawing.all(lambda element: element.tag == "text"):
                    assert text.attrs.get("fill", "").startswith("#"), text.text()

        def test_traces_a_carried_path_from_the_source_through_the_adapter_to_the_pod(self, explorer):
            """traces a carried path from the source, through the adapter, to the pod

            The source names the kind and the case's input, the adapter the path and its verdict, the pod the class;
            the script fills each end with the case's lines around its mark.
            """
            detail = explorer.fragment("/category/coding/code")
            (trace,) = detail.by_class("trace")
            assert trace.attrs["data-trace"] == explorer.data["cases"][0]["file"]
            source, adapter, pod = [part.text() for part in trace.all(lambda element: element.tag == "section")]
            assert source.startswith("The source Observation") and "fixtures/in/category-coded.json" in source
            assert adapter.startswith("The adapter /category/coding/code carried")
            assert "in/observation.rq" in adapter
            assert pod.startswith("The pod Observation ex:Observation")
            assert [pre.attrs["data-role"] for pre in trace.all(lambda element: element.tag == "pre")] == [
                "input",
                "expectedGraph",
            ]

        def test_traces_a_path_not_carried_to_the_finding_it_raises(self, explorer):
            """traces a path not carried to the finding it raises"""
            (trace,) = explorer.fragment("/category/text").by_class("trace")
            *_, findings = [part.text() for part in trace.all(lambda element: element.tag == "section")]
            assert findings.startswith("The findings A category's text has no Cascade predicate.")
            assert "exa:categoryTextNotCarried" in findings
            assert [pre.attrs["data-role"] for pre in trace.all(lambda element: element.tag == "pre")] == [
                "input",
                "expectedFindings",
            ]
            assert not explorer.fragment("/category/coding/display").by_class("trace")

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
            fragment = (
                explorer.out / explorer.by_id(explorer.node("/note/display")["id"]).attrs["data-file"]
            ).read_text(encoding="utf-8")
            assert f'The same fact as <a href="#{same["node"]}"><code>/subject/reference</code></a>.' in fragment

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

        def test_folds_its_panes_to_buttons_on_a_narrow_screen_with_rows_a_thumb_can_hit(self, explorer):
            """folds its panes to buttons on a narrow screen, with rows a thumb can hit

            The buttons are not tabs: they carry no tab roles, and the pane shown is the button with aria-current.
            """
            buttons = list(explorer.by_id("tabs").all(lambda e: e.tag == "button"))
            assert [button.attrs["aria-controls"] for button in buttons] == ["paths-pane", "views-pane", "case-pane"]
            assert [button.attrs.get("aria-current") for button in buttons] == [None, "true", None]
            assert not explorer.dom.having("role", "tab") and not explorer.dom.having("role", "tablist")
            assert not explorer.dom.having("aria-selected")
            narrow = explorer.style().split("@media (max-width: 760px)")[1]
            assert re.search(r"\.tabs[^{}]*\{[^}]*display: *grid", narrow)
            assert re.search(r"\.row[^{}]*\{[^}]*min-height: *32px", narrow)

        def test_moves_focus_to_the_heading_of_the_place_selected_and_marks_its_row_as_current(self, explorer):
            """moves focus to the heading of the place selected, and marks its row as current"""
            for view in explorer.dom.by_class("view"):
                (heading,) = view.all(lambda element: element.tag == "h1")
                assert heading.attrs.get("tabindex") == "-1", view.attrs["id"]
            script = explorer.page.split("<script>")[-1]
            assert re.search(r'setAttribute\("aria-current", "true"\)', script)
            assert "heading.focus(" in script

        def test_shows_every_pane_stacked_when_the_script_is_off(self, explorer):
            """shows every pane stacked when the script is off

            Under 760 px the panes are folded to one at a time only where the script has set a class on the page's root
            to say it can unfold them.
            """
            narrow = explorer.style().split("@media (max-width: 760px)")[1]
            hiding = [
                selectors
                for selectors, body in re.findall(r"([^{}]+)\{([^{}]*)\}", narrow)
                if re.search(r"display: *none", body) and ".pane" in selectors
            ]
            assert hiding
            for selectors in hiding:
                assert all(selector.strip().startswith(".js ") for selector in selectors.split(",")), selectors
            assert re.search(r'documentElement\.classList\.add\("js"\)', explorer.page.split("<script>")[-1])
            assert re.search(r"\.js \.tabs[^{}]*\{[^}]*display: *grid", narrow)

        def test_falls_back_to_the_values_the_sites_stylesheet_gives_its_tokens(self, explorer):
            """falls back to the values the site's stylesheet gives its tokens

            A change to a fallback here is a pair with cascade-runtime-js: its check of the stylesheet, which fails every
            docs-site build where a fallback is not the value `site.css` declares, has to change with it.
            """
            fallbacks = {
                name: value.strip()
                for name, value in re.findall(r"var\((--[\w-]+), *([^()]*(?:\([^()]*\))?[^()]*)\)", explorer.style())
            }
            assert fallbacks == {
                "--amber": "#8a5a0d",
                "--bar": "0px",
                "--d": "0",
                "--ink": "#14202a",
                "--ink-2": "#3a4853",
                "--link": "#0b6a8a",
                "--link-hover": "#084f68",
                "--mono": "'IBM Plex Mono', ui-monospace, 'SFMono-Regular', Menlo, monospace",
                "--muted": "#5a6873",
                "--paper": "#f6f7f8",
                "--pencil": "#b4410c",
                "--rule": "#c9d1d6",
                "--rule-soft": "#e3e8eb",
                "--sans": "'IBM Plex Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
                "--serif": "'Newsreader', Georgia, 'Times New Roman', serif",
            }

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

    class TestGivenTwoPlacesThatShareAGap:
        def test_marks_only_what_a_finding_points_at_on_the_places_own_path(
            self, explorer_with_two_places_sharing_a_gap
        ):
            """marks only what a finding points at on the place's own path

            Two places name one gap and each has one finding. A place is marked at its own finding, in the input and in
            the expected findings, never at the other's.
            """
            explorer = explorer_with_two_places_sharing_a_gap
            case = explorer.case("two-places")
            for place, line, finding in (
                ("/shared/first", '"first": "a",', "<urn:f1>"),
                ("/shared/second", '"second": "b"', "<urn:f2>"),
            ):
                (link,) = explorer.fragment(place).having("data-case")
                marks = json.loads(link.attrs["data-marks"])
                lines = case["input"]["text"].split("\n")
                assert [lines[at - 1].strip() for at in marks["input"]] == [line], place
                findings = case["expectedFindings"]["text"].split("\n")
                assert [findings[at - 1].split()[0] for at in marks["expectedFindings"]] == [finding], place

    class TestGivenTwoPlacesCarriedFromOneCase:
        def test_marks_each_place_where_its_own_path_lands_in_a_record_of_its_own_kind(
            self, explorer_with_two_places_carried_from_one_case
        ):
            """marks each place where its own path lands, in a record of its own kind

            Neither raises a finding. A place is marked at its own path, never at the other's, and its contained form
            is not marked in a contained record of a kind its mapping does not name.
            """
            explorer = explorer_with_two_places_carried_from_one_case
            assert input_marks(explorer, "/shared/first") == {"ex:subject": ['"first": "a",']}
            assert input_marks(explorer, "/shared/second") == {"ex:noteText": ['"second": "b"']}

        def test_traces_only_the_kind_the_path_landed_in_and_the_class_the_case_shows(
            self, explorer_with_two_places_carried_from_one_case
        ):
            """traces only the kind the path landed in, and the class the case shows

            The mapping of /shared/second names two kinds and two classes; the case's record is an Observation and its
            graph holds no Unit, so the source and the pod name the Observation alone.
            """
            explorer = explorer_with_two_places_carried_from_one_case
            (trace,) = explorer.fragment("/shared/second").by_class("trace")
            source, _, pod = [part.text() for part in trace.all(lambda element: element.tag == "section")]
            assert source.startswith("The source Observation fixtures/in/two-places.json")
            assert pod == "The pod Observation ex:Observation"

    class TestGivenTwoEnvelopesNamingOneMemberOfTheRoot:
        def test_finds_the_records_of_the_envelope_naming_the_members_value_before_the_one_naming_the_member_alone(
            self, tmp_path
        ):
            """finds the records of the envelope naming the member's value before the one naming the member alone"""
            by_value, by_member = {"@id": "#envelope-by-value"}, {"@id": "#envelope-by-member"}
            crate = json.loads(json.dumps(CRATE))
            crate["@graph"][1]["bridge:envelope"] = [by_value, by_member]
            crate["@graph"] = [
                *crate["@graph"][:2],
                {
                    **by_value,
                    "@type": "bridge:Envelope",
                    "name": "by value",
                    "bridge:docRootMemberName": "kind",
                    "bridge:docRootMemberValue": "x",
                    "bridge:jsonPathOfEachRecord": "$.first[*]",
                },
                {
                    **by_member,
                    "@type": "bridge:Envelope",
                    "name": "by member",
                    "bridge:docRootMemberName": "kind",
                    "bridge:jsonPathOfEachRecord": "$.second[*]",
                },
            ]
            an_adapter(tmp_path / "adapter", crate=crate)
            vocabulary = tmp_path / "vocabulary"
            write(vocabulary / "ontologies" / "example.ttl", PREFIXES + VOCABULARY)
            adapter = adapter_explorer.Adapter(tmp_path / "adapter", vocabulary)

            def found(document):
                return {
                    str(envelope).rsplit("#", 1)[1]: [pointer for pointer, _ in nodes]
                    for envelope, nodes in adapter.records(document).items()
                }

            both = {"first": [{"n": 1}], "second": [{"n": 2}]}
            assert found({"kind": "x", **both}) == {"envelope-by-value": ["/first/0"]}
            assert found({"kind": "y", **both}) == {"envelope-by-member": ["/second/0"]}

    class TestGivenAnXmlSource:
        def test_draws_each_section_flowing_into_the_classes_its_records_become(self, xml_explorer):
            """draws each section flowing into the classes its records become

            Where the kinds of record are identifiers, a kind is drawn under the outermost element below the document
            element that bears another identifier of the accounting, in a test case's input; a kind the document
            element itself bears, and a path carried with no kind named, is drawn on its own, however empty a value
            an element of the input carries.
            """
            flow = xml_explorer.data["flow"]
            unnamed = "A kind of record the accounting does not name"
            assert flow["sources"] == [
                {"label": unnamed, "kinds": [unnamed]},
                {"label": "First Section", "kinds": ["Finding Observation"]},
                {"label": "Header", "kinds": ["Header"]},
                {"label": "Second Section", "kinds": ["Other Observation"]},
            ]
            assert [item["term"] for item in flow["classes"]] == ["ex:Document", "ex:Finding", "ex:Other"]
            assert flow["links"] == [
                {"source": 0, "class": 0, "properties": 1},
                {"source": 1, "class": 1, "properties": 3},
                {"source": 2, "class": 0, "properties": 1},
                {"source": 3, "class": 2, "properties": 1},
            ]
            wide, _ = drawings(xml_explorer)
            texts = [text.text() for text in wide.all(lambda element: element.tag == "text")]
            assert texts[0] == "Where in the source"
            assert {"First Section", "Header", "Second Section"} <= set(texts)

        def test_marks_where_a_path_lands_only_in_an_element_bearing_its_kind(self, xml_explorer):
            """marks where a path lands only in an element bearing its kind

            Two kinds share a place and one case: each mapping is marked inside the element that bears its own kind,
            and a second place of the same case only at its own path.
            """
            observation = "/doc/section/entry/observation"
            assert input_marks(xml_explorer, f"{observation}/value/@value", "two-sections") == {
                "ex:findingValue": ['<value value="1"/>'],
                "ex:otherValue": ['<value value="2"/>'],
            }
            assert input_marks(xml_explorer, f"{observation}/code/@code", "two-sections") == {
                "ex:findingCode": ['<code code="a"/>']
            }
            assert input_marks(xml_explorer, "/doc/title", "two-sections") == {
                "ex:title": ["<title>A document</title>"]
            }

        def test_marks_nothing_in_an_element_with_no_identifier_standing_where_the_records_of_its_kind_stand(
            self, xml_explorer
        ):
            """marks nothing in an element with no identifier that stands where the records of its kind stand

            The first section holds, beside the entry of its Finding Observation, an entry whose observation bears no
            identifier: no record reads it, so neither its code nor its value is marked, though the section holds a
            record of the kind.
            """
            observation = "/doc/section/entry/observation"
            for place in (f"{observation}/code/@code", f"{observation}/value/@value"):
                marked = [line for lines in input_marks(xml_explorer, place, "two-sections").values() for line in lines]
                assert not [line for line in marked if '"z"' in line or '"9"' in line], place

        def test_marks_a_place_above_a_record_only_where_it_holds_a_record_of_its_kind(self, xml_explorer):
            """marks a place above a record only where it holds a record of its kind

            A section's code is read for the records the section holds, so it is marked in the section holding a
            record of the mapping's kind, never in another section.
            """
            assert input_marks(xml_explorer, "/doc/section/code/@code", "two-sections") == {
                "ex:findingSection": ['<code code="s1"/>']
            }

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
