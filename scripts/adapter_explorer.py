"""Builds an adapter's explorer, one page a reader browses the adapter on:

    python3 scripts/adapter_explorer.py <adapter> --vocabulary <cascade-vocabulary> \\
        --repository <url> --report <url> [--way-back <label> <url>] [--stylesheet <url>]... --out <folder>

<adapter> is a git checkout of an adapter; <cascade-vocabulary> a checkout of the vocabulary that the crate's
bridge:vocabularyFile paths are read in, for the labels of terms; --repository is the adapter's repository on the web,
where the page links each file at the checkout's commit; --report is the adapter's conformance report; --way-back
names the page the explorer was reached from, which the page links in its bar and at its end; each --stylesheet is
linked ahead of the page's own, which reads the site's tokens by name and falls back to the site's values. Writes
index.html, explorer.json (what the page shows, as data) and cases/<n>.json (a test case, read when a reader opens it)
into <folder>.
"""

import argparse
import bisect
import html
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ElementTree
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import url2pathname
from xml.parsers import expat

from rdflib import RDF, RDFS, SKOS, Graph, Literal, Namespace, URIRef, Variable
from rdflib.plugins.sparql.algebra import translateQuery
from rdflib.plugins.sparql.parser import parseQuery
from rdflib.plugins.sparql.parserutils import CompValue
from rdflib.util import guess_format

import path_forms

BRIDGE = Namespace(path_forms.BRIDGE)
SCHEMA = Namespace("http://schema.org/")
MF = Namespace("http://www.w3.org/2001/sw/DataAccess/tests/test-manifest#")
OA = Namespace("http://www.w3.org/ns/oa#")
SPEC = Path(__file__).resolve().parents[1]

VERDICTS = ("carried", "carriedInPart", "redundantWith", "consumed", "noHome", "ignored")
NOT_CARRIED = ("carriedInPart", "noHome", "ignored")
NAMESPACED_STEP = re.compile(r"(@?)\*\[local-name\(\)='([^']*)' and namespace-uri\(\)='[^']*'\]")
PREFIX = re.compile(r"\bPREFIX\s+([A-Za-z][\w.-]*)?:\s*<([^>\s]*)>", re.IGNORECASE)
PREFIXED_NAME = re.compile(r"(?<![\w?$:<])([A-Za-z][\w.-]*)?:([A-Za-z0-9_](?:[\w.-]*[\w-])?)")
AN_IRI = re.compile(r"<([^<>\s]*)>")
TURTLE_PREFIX = re.compile(r"(?:@prefix|PREFIX)\s+([A-Za-z][\w.-]*|):\s*<([^>\s]*)>", re.IGNORECASE)
XPATH_STEP = re.compile(
    r"(@?)(?:\*\[local-name\(\)='([^']*)' and namespace-uri\(\)='([^']*)'\]|([A-Za-z_][\w.-]*))(?:\[(\d+)\])?"
)
JSON_DECODER = json.JSONDecoder()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("adapter", type=Path)
    parser.add_argument("--vocabulary", type=Path, required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--way-back", nargs=2, metavar=("LABEL", "URL"))
    parser.add_argument("--stylesheet", action="append", default=[], metavar="URL")
    parser.add_argument("--out", type=Path, required=True)
    arguments = parser.parse_args(argv)
    data, cases = build(arguments.adapter, arguments.vocabulary, arguments.repository.rstrip("/"), arguments.report)
    write(arguments.out, data, cases, arguments.way_back, arguments.stylesheet)


def path_of(iri):
    return Path(url2pathname(urlparse(str(iri)).path))


def english(graph, subject, predicate):
    values = list(graph.objects(subject, predicate))
    for value in values:
        if isinstance(value, Literal) and value.language in ("en", None):
            return str(value)
    return str(values[0]) if values else None


def in_words(name):
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", name).lower()


def local_name(iri):
    return re.split(r"[#/]", str(iri))[-1]


def steps_of(path):
    """A path's steps: each / outside a step's brackets and quotes begins one."""
    steps, depth, quote, start = [], 0, None, 1
    for at, character in enumerate(path):
        if quote:
            quote = None if character == quote else quote
        elif character in "'\"":
            quote = character
        elif character == "[":
            depth += 1
        elif character == "]":
            depth -= 1
        elif character == "/" and depth == 0 and at > 0:
            steps.append(path[start:at])
            start = at + 1
    steps.append(path[start:])
    return tuple(steps)


def step_label(step):
    """`*[local-name()='code' and namespace-uri()='…']` as `code`, a JSON Pointer token unescaped."""
    namespaced = NAMESPACED_STEP.fullmatch(step)
    if namespaced:
        return namespaced[1] + namespaced[2]
    return step.replace("~1", "/").replace("~0", "~")


def plain_steps(path):
    """A path's steps as the places of an accounting name them: a position (`[2]`, or an array's index in a JSON
    Pointer) is dropped, and a namespaced step is its local name."""
    named = (re.sub(r"\[\d+\]$", "", step) for step in steps_of(path))
    return tuple(step_label(step) for step in named if step and not step.isdigit())


def on_path(selector, place):
    """Whether a selector's steps lie on the place's: one is the other's beginning, and the selector is not the root."""
    if not selector:
        return False
    shorter = min(len(selector), len(place))
    return selector[:shorter] == place[:shorter]


def shown_path(steps):
    return "/" + "/".join(step_label(step) for step in steps)


class Adapter:
    def __init__(self, folder, vocabulary):
        self.folder = folder.resolve()
        crate_file = self.folder / "ro-crate-metadata.json"
        crate = json.loads(crate_file.read_text(encoding="utf-8"))
        context = [part for part in crate["@context"] if isinstance(part, dict)]
        crate["@context"] = [{"@vocab": str(SCHEMA)}, *context]
        self.crate = Graph().parse(data=json.dumps(crate), format="json-ld", base=crate_file.as_uri())
        (self.root,) = self.crate.subjects(RDF.type, BRIDGE.Adapter)
        self.accounting_file = self.file(BRIDGE.sourceAccounting)
        self.accounting = Graph().parse(self.accounting_file, publicID=self.accounting_file.as_uri())
        self.gaps = Graph().parse(self.file(BRIDGE.gapScheme), format="turtle")
        manifest = self.file(BRIDGE.testManifest)
        self.manifest = Graph().parse(manifest, format="turtle", publicID=manifest.as_uri())
        self.manifest_iri = URIRef(manifest.as_uri())
        self.vocabulary = Graph()
        for file in self.crate.objects(self.root, BRIDGE.vocabularyFile):
            self.vocabulary.parse(vocabulary / str(file), format="turtle")
        self.names = Graph(bind_namespaces="none")
        for graph in (self.gaps, self.accounting):
            for prefix, namespace in graph.namespaces():
                self.names.bind(prefix, namespace, override=False)

    def value(self, predicate):
        return self.crate.value(self.root, predicate)

    def file(self, predicate):
        return path_of(self.value(predicate))

    def relative(self, path):
        return path.resolve().relative_to(self.folder).as_posix()

    def term(self, iri):
        try:
            curie = self.names.namespace_manager.curie(str(iri), generate=False)
        except (KeyError, ValueError):
            curie = f"<{iri}>"
        return {"term": curie, "label": english(self.vocabulary, iri, RDFS.label)}

    def kind_label(self, kind):
        if self.value(BRIDGE.sourceRecordTypesAreIdentifiers) != Literal(True):
            return kind
        for concept in self.accounting.subjects(SKOS.notation, Literal(kind)):
            return english(self.accounting, concept, SKOS.prefLabel)
        return kind


def query_terms(text):
    """The IRIs a query names outside its prefix declarations, its strings and its comments: a mapping binds the
    property it writes as often as it writes it in its template."""
    cleaned = without_strings_and_comments(text)
    prefixes = {prefix or "": namespace for prefix, namespace in PREFIX.findall(cleaned)}
    body = PREFIX.sub(" ", cleaned)
    terms = set(AN_IRI.findall(body))
    for prefix, local in PREFIXED_NAME.findall(AN_IRI.sub(" ", body)):
        if (prefix or "") in prefixes:
            terms.add(prefixes[prefix or ""] + local)
    return terms


def properties_written(text):
    """The IRIs a CONSTRUCT query writes as the predicate of a template triple: named there, or bound by BIND or VALUES
    to the variable that sits there. An IRI the query names only as a value, bound to a variable the template writes as
    an object, is not written."""
    query = translateQuery(parseQuery(text)).algebra
    bound = {}

    def children(node):
        if isinstance(node, (CompValue, dict)):
            return list(node.values())
        return list(node) if isinstance(node, (list, tuple, set)) else []

    def collect(node):
        if isinstance(node, CompValue) and node.name == "Extend":
            bound.setdefault(node["var"], set()).update(terms_in(node["expr"]))
        if isinstance(node, CompValue) and node.name == "values":
            for row in node["res"]:
                for variable, value in row.items():
                    bound.setdefault(variable, set()).add(value)
        for child in children(node):
            collect(child)

    def terms_in(node):
        if isinstance(node, (URIRef, Variable)):
            return {node}
        return {term for child in children(node) for term in terms_in(child)}

    def resolved(term, seen=()):
        if isinstance(term, URIRef):
            return {term}
        if term in seen:
            return set()
        return {iri for value in bound.get(term, ()) for iri in resolved(value, (*seen, term))}

    collect(query["p"])
    return {str(iri) for _, predicate, _ in query["template"] for iri in resolved(predicate)}


def without_strings_and_comments(text):
    out, at = [], 0
    while at < len(text):
        character = text[at]
        if character == "<":
            iri = AN_IRI.match(text, at)
            if iri:
                out.append(iri[0])
                at = iri.end()
                continue
        if character == "#":
            end = text.find("\n", at)
            at = len(text) if end == -1 else end
            continue
        if character in "'\"":
            quote = text[at : at + 3] if text[at : at + 3] in ("'''", '"""') else character
            at += len(quote)
            while at < len(text) and not text.startswith(quote, at):
                at += 2 if text[at] == "\\" else 1
            at += len(quote)
            out.append('""')
            continue
        out.append(character)
        at += 1
    return "".join(out)


class Held:
    """The paths a test case's input holds, from any node of it down."""

    def __init__(self, text):
        self.below = {}
        try:
            self.json(json.loads(text))
        except ValueError:
            try:
                self.xml(ElementTree.fromstring(text))
            except ElementTree.ParseError:
                pass

    def reached(self, parent, step):
        node = {}
        self.below.setdefault(step, []).append(node)
        parent.setdefault(step, []).append(node)
        return node

    def json(self, value, parent=None):
        if isinstance(value, list):
            for item in value:
                self.json(item, parent)
        elif isinstance(value, dict):
            for name, member in value.items():
                node = self.reached({} if parent is None else parent, name.replace("~", "~0").replace("/", "~1"))
                self.json(member, node)

    def xml(self, element, parent=None):
        node = self.reached({} if parent is None else parent, self.xml_step(element.tag))
        for name in element.attrib:
            self.reached(node, "@" + self.xml_step(name))
        for child in element:
            if isinstance(child.tag, str):
                self.xml(child, node)

    @staticmethod
    def xml_step(name):
        if name.startswith("{"):
            namespace, local = name[1:].split("}", 1)
            return f"*[local-name()='{local}' and namespace-uri()='{namespace}']"
        return name

    def holds(self, path):
        steps = steps_of(path)
        frontier = self.below.get(steps[0], [])
        for step in steps[1:]:
            frontier = [child for node in frontier for child in node.get(step, [])]
        return bool(frontier)


class Lines:
    """The line each node of a test case's input begins on, by the selector a finding would give it: a JSON Pointer,
    or an XPath of `*[local-name()=… and namespace-uri()=…][n]` and `@name` steps."""

    def __init__(self, text):
        self.text = text
        self.starts = [0] + [at + 1 for at, character in enumerate(text) if character == "\n"]
        self.at = {}
        try:
            self.json_value(self.skip(0), "", 0)
        except (ValueError, IndexError):
            self.at = {}
            self.xml()

    def line(self, offset):
        return bisect.bisect_right(self.starts, offset)

    def skip(self, at):
        while at < len(self.text) and self.text[at] in " \t\r\n":
            at += 1
        return at

    def json_value(self, at, pointer, begins):
        self.at[pointer] = self.line(begins)
        opening = self.text[at]
        if opening not in "{[":
            return JSON_DECODER.raw_decode(self.text, at)[1]
        closing, at, index = "}" if opening == "{" else "]", self.skip(at + 1), 0
        while self.text[at] != closing:
            if opening == "{":
                name, after = json.decoder.scanstring(self.text, at + 1)
                colon = self.skip(after)
                if self.text[colon] != ":":
                    raise ValueError("a member's name is not followed by a colon")
                at = self.json_value(
                    self.skip(colon + 1), f"{pointer}/{name.replace('~', '~0').replace('/', '~1')}", at
                )
            else:
                at = self.json_value(at, f"{pointer}/{index}", at)
                index += 1
            at = self.skip(at)
            if self.text[at] == ",":
                at = self.skip(at + 1)
        return at + 1

    def xml(self):
        parser = expat.ParserCreate(namespace_separator=" ")
        stack = [{"children": []}]

        def start(name, attributes):
            namespace, _, local = name.rpartition(" ")
            node = {"name": (namespace, local), "line": parser.CurrentLineNumber, "children": [], "attributes": {}}
            for attribute in attributes:
                attribute_namespace, _, attribute_local = attribute.rpartition(" ")
                node["attributes"][(attribute_namespace, attribute_local)] = parser.CurrentLineNumber
            stack[-1]["children"].append(node)
            stack.append(node)

        parser.StartElementHandler = start
        parser.EndElementHandler = lambda name: stack.pop()
        try:
            parser.Parse(self.text, True)
        except expat.ExpatError:
            return
        self.document = stack[0]

    def find(self, selector):
        if selector in self.at:
            return self.at[selector]
        node = getattr(self, "document", None)
        for step in [] if node is None else [step for step in steps_of(selector) if step]:
            matched = XPATH_STEP.fullmatch(step)
            if not matched:
                return None
            attribute, local, namespace, plain, position = matched.groups()
            local, namespace = (plain, "") if plain else (local, namespace)
            if attribute:
                return node["attributes"].get((namespace, local))
            same = [child for child in node["children"] if child["name"] == (namespace, local)]
            index = int(position or 1) - 1
            if index >= len(same):
                return None
            node = same[index]
        return None if node is None or "line" not in node else node["line"]


def selectors_of(findings, body):
    """The selector of each finding with the body, its refinements appended: a JSON Pointer or an XPath, refined below
    where its record is."""
    out = []
    for finding in sorted(findings.subjects(OA.hasBody, body)):
        for target in findings.objects(finding, OA.hasTarget):
            selector, path = findings.value(target, OA.hasSelector), ""
            while selector is not None:
                step = str(findings.value(selector, RDF.value) or "")
                path = path + step if step.startswith("/") or not path else f"{path}/{step}"
                selector = findings.value(selector, OA.refinedBy)
            out.append(path)
    return out


def naming(text, iris):
    """A pattern for any of the IRIs as a Turtle text spells it, whole or under a prefix the text declares, and the
    text's lines it matches."""
    spellings = {f"<{iri}>" for iri in iris}
    for prefix, namespace in TURTLE_PREFIX.findall(text):
        spellings |= {f"{prefix}:{iri[len(namespace) :]}" for iri in iris if iri.startswith(namespace)}
    named = re.compile("|".join(rf"(?<![\w:<-]){re.escape(spelling)}(?![\w-])" for spelling in sorted(spellings)))
    return named, [at + 1 for at, line in enumerate(text.split("\n")) if spellings and named.search(line)]


def lines_naming(text, iris):
    """The lines of a Turtle text that name any of the IRIs, whole or under a prefix the text declares."""
    return naming(text, iris)[1]


def selectors_by_line(text, body):
    """The selectors of the finding each line of a Turtle findings text names the body for, by the line: the
    selectors the text loses when that line stops naming it."""
    named, lines = naming(text, [str(body)])
    whole = Counter(selectors_of(Graph().parse(data=text, format="turtle"), body))
    by_line, rows = {}, text.split("\n")
    for line in lines:
        rows_without = rows[: line - 1] + [named.sub("<urn:x-explorer:other>", rows[line - 1])] + rows[line:]
        left = Counter(selectors_of(Graph().parse(data="\n".join(rows_without), format="turtle"), body))
        by_line[line] = sorted((whole - left).elements())
    return by_line


def read_cases(adapter):
    cases = []
    head = adapter.manifest.value(adapter.manifest_iri, MF.entries)
    for test in [] if head is None else adapter.manifest.items(head):
        action, result = adapter.manifest.value(test, MF.action), adapter.manifest.value(test, MF.result)
        expected = adapter.manifest.value(result, BRIDGE.expectedGraph) if result is not None else None
        if expected is None:
            continue
        files = {
            "input": path_of(adapter.manifest.value(action, BRIDGE.input)),
            "expectedGraph": path_of(expected),
            "expectedFindings": path_of(adapter.manifest.value(result, BRIDGE.expectedFindings) or ""),
        }
        if not files["expectedFindings"].is_file():
            del files["expectedFindings"]
        texts = {role: file.read_text(encoding="utf-8") for role, file in files.items()}
        graph = Graph().parse(data=texts["expectedGraph"], format=guess_format(str(files["expectedGraph"])))
        findings = Graph()
        if "expectedFindings" in texts:
            findings.parse(data=texts["expectedFindings"], format=guess_format(str(files["expectedFindings"])))
        cases.append(
            {
                "findingsAreEmpty": len(findings) == 0,
                "name": str(adapter.manifest.value(test, MF.name) or local_name(test)),
                "comment": english(adapter.manifest, test, RDFS.comment),
                "concern": adapter.manifest.value(test, BRIDGE.concern),
                "files": {role: adapter.relative(file) for role, file in files.items()},
                "texts": texts,
                "held": Held(texts["input"]),
                "classes": set(graph.objects(None, RDF.type)),
                "predicates": set(graph.predicates()),
                "bodies": set(findings.objects(None, OA.hasBody)),
                "findings": findings,
            }
        )
    return cases


def read_entries(adapter, forms):
    entries = []
    graph = adapter.accounting
    for entry in graph.subjects(RDF.type, BRIDGE.PathEntry):
        path = str(graph.value(entry, BRIDGE.sourcePath))
        form, place = path_forms.place_of(forms, path)
        carried = sorted(
            (
                str(graph.value(node, BRIDGE.inSourceRecordType) or ""),
                graph.value(node, BRIDGE.inRecordClass),
                graph.value(node, BRIDGE.asProperty),
            )
            for node in graph.objects(entry, BRIDGE.carriedAs)
        )
        entries.append(
            {
                "path": path,
                "form": None if form is None else form_label(adapter, form),
                "contained": form is not None and form.contained,
                "steps": steps_of(place),
                "verdict": local_name(graph.value(entry, BRIDGE.verdict)),
                "because": english(graph, entry, BRIDGE.because),
                "gap": graph.value(entry, BRIDGE.namesGap),
                "lookupIn": graph.value(entry, BRIDGE.lookupIn),
                "lookupGap": graph.value(entry, BRIDGE.lookupNamesGap),
                "sameFactAs": graph.value(entry, BRIDGE.sameFactAs),
                "concern": graph.value(entry, BRIDGE.concern),
                "carried": tuple(carried),
            }
        )
    unknown = {entry["verdict"] for entry in entries} - set(VERDICTS)
    if unknown:
        raise ValueError(f"the accounting names verdicts this explorer does not know: {sorted(unknown)}")
    return entries


def form_label(adapter, form):
    name = adapter.crate.value(form.envelope, SCHEMA.name) or local_name(form.envelope)
    return f"{name}, contained" if form.contained else str(name)


def rough(count):
    if count == 0:
        return "none"
    if count < 10:
        return "a few"
    digits = len(str(count)) - 2 if count >= 100 else 1
    return f"about {round(count, -digits):,}"


def build(folder, vocabulary, repository, report):
    adapter = Adapter(folder, vocabulary)
    commit = subprocess.run(
        ["git", "-C", str(adapter.folder), "rev-parse", "HEAD"], check=True, capture_output=True, text=True
    ).stdout.strip()
    forms = path_forms.read(adapter.crate, adapter.root)
    entries = read_entries(adapter, forms)
    cases = read_cases(adapter)
    queries = {}
    for predicate in (BRIDGE.mapping, BRIDGE.findingsQuery):
        for iri in sorted(adapter.crate.objects(adapter.root, predicate)):
            file = path_of(iri)
            text = file.read_text(encoding="utf-8")
            queries[adapter.relative(file)] = (
                predicate,
                query_terms(text) if predicate == BRIDGE.findingsQuery else properties_written(text),
            )
    blob = f"{repository}/blob/{commit}/"

    def gap(iri):
        if iri is None:
            return None
        return {
            "term": adapter.term(iri)["term"],
            "label": english(adapter.gaps, iri, SKOS.prefLabel) or local_name(iri),
            "issues": sorted(str(issue) for issue in adapter.gaps.objects(iri, RDFS.seeAlso)),
        }

    def writers(kind, term):
        return [name for name, (of, terms) in queries.items() if of == kind and str(term) in terms]

    def case_for(entry, paths):
        """The case that holds the adapter to the entry: its input holds the place, and its expected graph holds
        something the entry becomes, or, for an entry that becomes nothing, its expected findings name the entry's gap;
        of those, the smallest input."""

        def shows(case):
            if not entry["carried"]:
                return entry["gap"] in case["bodies"]
            return any(
                record_class in case["classes"] and property_ in case["predicates"]
                for _, record_class, property_ in entry["carried"]
            )

        candidates = [case for case in cases if shows(case) and any(case["held"].holds(path) for path in paths)]
        return min(candidates, key=lambda case: (len(case["texts"]["input"]), case["name"]), default=None)

    def marks_in(case, entry, paths):
        """The lines of the case's files a reader looks at for the entry: where each finding naming its gap points in
        the input, on one of the entry's own paths, those findings, and each line of the expected graph naming a
        property the entry becomes."""
        marks = {}
        if entry["gap"] is not None and "expectedFindings" in case["texts"]:
            if "lines" not in case:
                case["lines"] = Lines(case["texts"]["input"])
            own = [plain_steps(path) for path in paths]
            if "findings_by_line" not in case:
                case["findings_by_line"] = {}
            if entry["gap"] not in case["findings_by_line"]:
                case["findings_by_line"][entry["gap"]] = selectors_by_line(
                    case["texts"]["expectedFindings"], entry["gap"]
                )
            found, finding_lines = set(), []
            for line, selectors in case["findings_by_line"][entry["gap"]].items():
                on = [selector for selector in selectors if any(on_path(plain_steps(selector), steps) for steps in own)]
                if on:
                    finding_lines.append(line)
                found |= {case["lines"].find(selector) for selector in on}
            marks["input"] = sorted(line for line in found if line is not None)
            marks["expectedFindings"] = finding_lines
        properties = sorted({str(property_) for _, _, property_ in entry["carried"]})
        if properties:
            marks["expectedGraph"] = lines_naming(case["texts"]["expectedGraph"], properties)
        return {role: lines for role, lines in marks.items() if lines}

    tree = {}
    for entry in entries:
        node = {"children": tree}
        for depth in range(1, len(entry["steps"]) + 1):
            node = node["children"].setdefault(
                entry["steps"][:depth], {"steps": entry["steps"][:depth], "children": {}, "entries": []}
            )
        node["entries"].append(entry)

    nodes_by_steps, ordered = {}, []

    def number(level):
        for steps in sorted(
            level, key=lambda steps: (steps[-1].startswith("_"), step_label(steps[-1]).lower(), steps[-1])
        ):
            node = level[steps]
            node["id"] = f"n{len(ordered) + 1}"
            nodes_by_steps[steps] = node
            ordered.append(node)
            number(node["children"])

    number(tree)

    def node_of(path):
        return nodes_by_steps.get(steps_of(path_forms.place_of(forms, path)[1]))

    def plain_form_of(path):
        """The path a fact is read at where it is not contained, when the accounting names its contained form."""
        place = path_forms.place_of(forms, path)[1]
        same_place = [entry for entry in entries if path_forms.place_of(forms, entry["path"])[1] == place]
        return min(((entry["contained"], entry["path"]) for entry in same_place), default=(False, path))[1]

    def mappings_of(node):
        grouped = {}
        for entry in node["entries"]:
            key = tuple(entry[name] for name in ("verdict", "because", "gap", "lookupIn", "lookupGap", "concern"))
            same = entry["sameFactAs"]
            key += (entry["carried"], None if same is None else path_forms.place_of(forms, str(same))[1])
            grouped.setdefault(key, []).append(entry)
        mappings = []
        for group in grouped.values():
            entry = group[0]
            paths = sorted(member["path"] for member in group)
            same = entry["sameFactAs"]
            mappings.append(
                {
                    "forms": [
                        {"path": path, "shown": shown_path(steps_of(path)), "form": form}
                        for _, path, form in sorted(
                            (member["contained"], member["path"], member["form"] or "") for member in group
                        )
                    ],
                    "verdict": entry["verdict"],
                    "because": entry["because"],
                    "gap": gap(entry["gap"]),
                    "lookup": None
                    if entry["lookupIn"] is None
                    else {"table": adapter.relative(path_of(entry["lookupIn"])), "gap": gap(entry["lookupGap"])},
                    "sameFactAs": None
                    if same is None
                    else {"path": plain_form_of(str(same)), "node": (node_of(str(same)) or {}).get("id")},
                    "concern": None if entry["concern"] is None else local_name(entry["concern"]),
                    "becomes": [
                        {
                            "kind": adapter.kind_label(kind),
                            "class": adapter.term(record_class),
                            "property": adapter.term(property_),
                            "queries": writers(BRIDGE.mapping, property_),
                        }
                        for kind, record_class, property_ in entry["carried"]
                    ],
                    "queries": [] if entry["gap"] is None else writers(BRIDGE.findingsQuery, entry["gap"]),
                    "case": None,
                    "marks": {},
                }
            )
            case = case_for(entry, paths)
            if case is not None:
                mappings[-1]["case"], mappings[-1]["marks"] = case["name"], marks_in(case, entry, paths)
        return sorted(mappings, key=lambda mapping: (VERDICTS.index(mapping["verdict"]), str(mapping["forms"])))

    for node in ordered:
        node["mappings"] = mappings_of(node)

    def shaped(level):
        out = []
        for steps in sorted(level, key=lambda steps: int(nodes_by_steps[steps]["id"][1:])):
            node = level[steps]
            children = shaped(node["children"])
            counts = {verdict: 0 for verdict in VERDICTS}
            for mapping in node["mappings"]:
                counts[mapping["verdict"]] += len(mapping["forms"])
            for child in children:
                for verdict, count in child.pop("counts").items():
                    counts[verdict] += count
            verdicts = {verdict for verdict, count in counts.items() if count}
            out.append(
                {
                    "id": node["id"],
                    "place": shown_path(steps),
                    "step": step_label(steps[-1]),
                    "mappings": node["mappings"],
                    "rollUp": [verdict for verdict in VERDICTS if verdict in verdicts],
                    "shares": shares(counts),
                    "counts": counts,
                    "children": children,
                }
            )
        return out

    shaped_tree = shaped(tree)
    for node in shaped_tree:
        node.pop("counts")
    flat = list(walk(shaped_tree))
    places = {node["id"]: node["place"] for node in flat}
    by_place = sorted(flat, key=lambda node: node["place"])

    kinds = {}
    for node in by_place:
        for mapping in node["mappings"]:
            for becomes in mapping["becomes"]:
                target = kinds.setdefault(becomes["kind"], {})
                key = (becomes["class"]["term"], becomes["property"]["term"])
                item = target.setdefault(key, {"class": becomes["class"], "property": becomes["property"], "nodes": []})
                if node["id"] not in item["nodes"]:
                    item["nodes"].append(node["id"])
    kinds_list = [
        {"kind": kind, "becomes": [kinds[kind][key] for key in sorted(kinds[kind])]}
        for kind in sorted(kinds, key=str.lower)
    ]

    concern_labels = scheme_labels(BRIDGE.concerns)
    concerns = {}

    def concern(iri):
        name = local_name(iri)
        return concerns.setdefault(
            name, {"concern": name, "label": concern_labels.get(name, name), "nodes": [], "gaps": [], "cases": []}
        )

    for node in by_place:
        for mapping in node["mappings"]:
            if mapping["concern"] is not None and node["id"] not in concern(mapping["concern"])["nodes"]:
                concern(mapping["concern"])["nodes"].append(node["id"])
    for iri in sorted(adapter.gaps.subjects(BRIDGE.concern, None)):
        for tag in adapter.gaps.objects(iri, BRIDGE.concern):
            concern(tag)["gaps"].append(gap(iri))
    for case in cases:
        if case["concern"] is not None:
            concern(case["concern"])["cases"].append(case["name"])

    reasons = {}
    for node in by_place:
        for mapping in node["mappings"]:
            if mapping["verdict"] not in NOT_CARRIED:
                continue
            reason = mapping["gap"]["label"] if mapping["gap"] else mapping["because"]
            group = reasons.setdefault(
                reason,
                {"reason": reason, "issues": mapping["gap"]["issues"] if mapping["gap"] else [], "verdicts": []},
            )
            group.setdefault("nodes", [])
            if node["id"] not in group["nodes"]:
                group["nodes"].append(node["id"])
            if mapping["verdict"] not in group["verdicts"]:
                group["verdicts"].append(mapping["verdict"])
    not_carried = sorted(reasons.values(), key=lambda group: (-len(group["nodes"]), str(group["reason"])))

    search = []
    for node in flat:
        words = [node["place"]]
        for mapping in node["mappings"]:
            words += [form["path"] for form in mapping["forms"]]
            for becomes in mapping["becomes"]:
                for term in (becomes["class"], becomes["property"]):
                    words += [term["term"], term["label"] or ""]
                words.append(becomes["kind"])
        search.append({"node": node["id"], "place": node["place"], "text": " ".join(words).lower()})

    by_verdict = {verdict: len([entry for entry in entries if entry["verdict"] == verdict]) for verdict in VERDICTS}
    verdict_labels = scheme_labels(BRIDGE.verdicts)
    shown_cases = []
    case_files = {}
    for number_, case in enumerate(cases):
        file = f"cases/{number_ + 1}.json"
        shown_cases.append({"name": case["name"], "file": file, "comment": case["comment"]})
        case_files[file] = {
            "name": case["name"],
            "comment": case["comment"],
            **{
                role: {"file": case["files"][role], "link": blob + case["files"][role], "text": case["texts"][role]}
                | ({"empty": case["findingsAreEmpty"]} if role == "expectedFindings" else {})
                for role in case["files"]
            },
        }

    data = {
        "adapter": {
            "identifier": str(adapter.value(SCHEMA.identifier) or ""),
            "name": str(adapter.value(SCHEMA.name) or ""),
            "version": str(adapter.value(SCHEMA.version) or ""),
            "commit": commit,
            "repository": repository,
            "tree": f"{repository}/tree/{commit}",
            "blob": blob,
            "accounting": blob + adapter.relative(adapter.accounting_file),
            "report": report,
        },
        "figures": {
            "paths": rough(len(entries)),
            "places": rough(len(flat)),
            "cases": rough(len(cases)),
            "verdicts": {verdict: rough(by_verdict[verdict]) for verdict in VERDICTS},
            "shares": shares(by_verdict),
        },
        "verdicts": [
            {"verdict": verdict, "words": in_words(verdict), "label": verdict_labels.get(verdict)}
            for verdict in VERDICTS
        ],
        "tree": shaped_tree,
        "kinds": kinds_list,
        "concerns": [concerns[name] for name in sorted(concerns, key=lambda name: concerns[name]["label"])],
        "notCarried": not_carried,
        "cases": shown_cases,
        "search": search,
        "places": places,
    }
    return data, case_files


def shares(counts):
    """Each verdict's share of the counts, in hundredths, at least one where it has any: what a bar draws, not a figure."""
    total = sum(counts.values())
    return {verdict: max(1, round(100 * count / total)) for verdict, count in counts.items() if count}


def walk(nodes):
    for node in nodes:
        yield node
        yield from walk(node["children"])


def scheme_labels(scheme):
    vocabulary = Graph().parse(SPEC / "vocab" / "bridge.ttl", format="turtle")
    return {
        local_name(concept): english(vocabulary, concept, SKOS.prefLabel)
        for concept in vocabulary.subjects(SKOS.inScheme, scheme)
    }


def write(out, data, cases, way_back=None, stylesheets=()):
    if out.exists() and any(out.iterdir()):
        sys.exit(f"{out} is not empty; the explorer is written into an empty folder")
    (out / "cases").mkdir(parents=True, exist_ok=True)
    (out / "explorer.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    for file, case in cases.items():
        (out / file).write_text(json.dumps(case, ensure_ascii=False), encoding="utf-8")
    (out / "index.html").write_text(page(data, way_back, stylesheets), encoding="utf-8")


def e(text):
    return html.escape(str(text), quote=True)


def link(href, text):
    return f'<a href="{e(href)}">{text}</a>'


FOLDER = (
    '<svg class="ic" width="13" height="11" viewBox="0 0 13 11" aria-hidden="true">'
    '<path d="M.5 1.5h4l1.2 1.4h6.8v7.6H.5z" fill="none" stroke="currentColor"/></svg>'
)
LEAF = (
    '<svg class="ic lf" width="13" height="11" viewBox="0 0 13 11" aria-hidden="true">'
    '<path d="M3 .5h5l2.5 2.5v7.5H3z" fill="none" stroke="currentColor"/></svg>'
)


class Page:
    def __init__(self, data):
        self.data = data
        self.verdicts = {item["verdict"]: item for item in data["verdicts"]}
        self.concerns = {concern["concern"]: concern["label"] for concern in data["concerns"]}
        self.cases = {case["name"]: case for case in data["cases"]}

    def pill(self, verdict, tag="span"):
        item = self.verdicts[verdict]
        kind = ' type="button"' if tag == "button" else ""
        return f'<{tag} class="v v-{e(verdict)}"{kind} title="{e(item["label"] or "")}">{e(item["words"])}</{tag}>'

    def bar(self, shares, css="mb"):
        words = ", ".join(self.verdicts[verdict]["words"] for verdict in shares)
        segments = "".join(f'<i class="s-{e(verdict)}" style="flex:{share}"></i>' for verdict, share in shares.items())
        return f'<span class="{css}" role="img" aria-label="{e(words)}" title="{e(words)}">{segments}</span>'

    def end(self, node):
        if not node["children"] and len(node["rollUp"]) == 1:
            return self.pill(node["rollUp"][0])
        return self.bar(node["shares"])

    def row(self, node, depth, opened):
        own = sorted({mapping["verdict"] for mapping in node["mappings"]}, key=VERDICTS.index)
        concerns = sorted({mapping["concern"] for mapping in node["mappings"] if mapping["concern"]})
        attributes = (
            f'data-node="{e(node["id"])}" data-v="{e(" ".join(own))}" data-c="{e(" ".join(concerns))}"'
            f' style="--d:{depth}"' + (" data-own" if own else "")
        )
        end = f'<span class="end">{self.end(node)}</span>'
        if not node["children"]:
            return (
                f'<li><a class="row" href="#{e(node["id"])}" {attributes}><span class="tw"></span>{LEAF}'
                f'<span class="nm" title="{e(node["place"])}">{e(node["step"])}</span>{end}</a></li>'
            )
        alone = opened and len(node["children"]) == 1
        inner = "".join(self.row(child, depth + 1, alone) for child in node["children"])
        return (
            f'<li><details{" open" if opened else ""}><summary class="row" {attributes}>'
            f'<span class="tw" aria-hidden="true"></span>{FOLDER}<a class="nm" href="#{e(node["id"])}" title="{e(node["place"])}">'
            f"{e(node['step'])}/</a>{end}</summary><ul>{inner}</ul></details></li>"
        )

    def facts(self, pairs):
        if not pairs:
            return ""
        return '<dl class="kv">' + "".join(f"<dt>{name}</dt><dd>{value}</dd>" for name, value in pairs) + "</dl>"

    def mapping(self, mapping, place):
        blob = self.data["adapter"]["blob"]
        verdict = self.verdicts[mapping["verdict"]]
        parts = [f'<p class="gen">{self.pill(mapping["verdict"])} {e(verdict["label"] or "")}</p>']
        if mapping["because"]:
            parts.append(f'<p class="fx">{e(mapping["because"])}</p>')
        if mapping["gap"]:
            parts.append(f'<p class="fx">{a_gap(mapping["gap"])}</p>')
        facts = []
        if mapping["gap"]:
            facts.append(("reported as", f"<code>{e(mapping['gap']['term'])}</code>"))
        if mapping["queries"]:
            facts.append(("written by", a_queries(blob, mapping["queries"])))
        if mapping["lookup"]:
            table, outside = mapping["lookup"]["table"], mapping["lookup"]["gap"]
            facts.append(
                (
                    "looked up in",
                    link(blob + table, f"<code>{e(table)}</code>")
                    + (f"; a value outside it: {a_gap(outside)}" if outside else ""),
                )
            )
        if mapping["concern"]:
            facts.append(("concern", e(self.concerns.get(mapping["concern"], mapping["concern"]))))
        parts.append(self.facts(facts))
        if mapping["sameFactAs"]:
            same = mapping["sameFactAs"]
            shown = f"<code>{e(shown_path(steps_of(same['path'])))}</code>"
            parts.append(f"<p>The same fact as {link('#' + same['node'], shown) if same['node'] else shown}.</p>")
        if mapping["becomes"]:
            rows = "".join(
                f'<tr><td data-label="property">{term(becomes["property"])}</td>'
                f'<td data-label="on the class">{term(becomes["class"])}</td>'
                f'<td data-label="in the kind">{e(becomes["kind"])}</td>'
                f'<td data-label="written by">{a_queries(blob, becomes["queries"])}</td></tr>'
                for becomes in mapping["becomes"]
            )
            parts.append(
                '<h4>Becomes</h4><table class="et stack"><thead><tr><th>property</th><th>on the class</th>'
                f"<th>in the kind</th><th>written by</th></tr></thead><tbody>{rows}</tbody></table>"
            )
        also = [form for form in mapping["forms"] if form["shown"] != place]
        if also:
            parts.append(
                '<details class="also"><summary>Also read at</summary>'
                + self.facts([(e(form["form"]), f"<code>{e(form['shown'])}</code>") for form in also])
                + "</details>"
            )
        if mapping["case"]:
            parts.append(f'<p class="case-link">Test case: {self.case_link(mapping["case"], mapping["marks"])}</p>')
        elif mapping["becomes"] or mapping["gap"]:
            parts.append('<p class="quiet">No test case of the adapter shows this.</p>')
        return f'<section class="mapping">{"".join(parts)}</section>'

    def case_link(self, name, marks=None):
        case = self.cases[name]
        return (
            f'<a href="{e(case["file"])}" data-case="{e(case["file"])}" '
            f'data-marks="{e(json.dumps(marks or {}, separators=(",", ":")))}">{e(name)}</a>'
        )

    def detail(self, node, ancestors):
        crumbs = " / ".join(
            [link("#paths", "source paths")]
            + [link(f"#{ancestor['id']}", e(ancestor["step"])) for ancestor in ancestors]
            + [f"<b>{e(node['step'])}</b>"]
        )
        parts = [
            f'<p class="crumbs">{crumbs}</p><h1 class="path" tabindex="-1">{e(node["place"]).replace("/", "<wbr>/")}</h1>'
        ]
        if not node["mappings"]:
            parts.append('<p class="fx">No entry of the accounting names this place itself.</p>')
        parts += [self.mapping(mapping, node["place"]) for mapping in node["mappings"]]
        if node["children"]:
            rows = "".join(
                f"<tr><td>{link('#' + child['id'], '<code>' + e(child['step']) + folder + '</code>')}"
                f'</td><td class="fig">{self.end(child)}</td></tr>'
                for child in node["children"]
                for folder in ["/" if child["children"] else ""]
            )
            parts.append(f'<h4>Under it</h4><table class="et under"><tbody>{rows}</tbody></table>')
        own = " data-own" if node["mappings"] else ""
        return (
            f'<article class="view detail" id="{e(node["id"])}" data-stop="paths"{own}><h2 class="ph">Selected</h2>'
            f'<div class="insp">{"".join(parts)}</div></article>'
        )

    def details(self, nodes, ancestors=()):
        for node in nodes:
            yield self.detail(node, ancestors)
            yield from self.details(node["children"], (*ancestors, node))

    def verdict_rows(self, figures=True):
        return "".join(
            f'<tr data-verdict="{e(item["verdict"])}"><td>{self.pill(item["verdict"], "button")}</td>'
            f"<td>{e(item['label'] or '')}</td>"
            + (f'<td class="fig">{e(self.data["figures"]["verdicts"][item["verdict"]])}</td>' if figures else "")
            + "</tr>"
            for item in self.data["verdicts"]
        )

    def kinds_table(self):
        most = max(
            (len({item["property"]["term"] for item in kind["becomes"]}) for kind in self.data["kinds"]), default=1
        )
        rows = []
        for number, kind in enumerate(self.data["kinds"], 1):
            classes = {item["class"]["term"]: item["class"] for item in kind["becomes"]}
            properties = len({item["property"]["term"] for item in kind["becomes"]})
            rows.append(
                f'<tr><td class="mono">{link(f"#kind-{number}", e(kind_name(kind)))}</td>'
                f"<td>{''.join(term(classes[key]) for key in sorted(classes))}</td>"
                f'<td><span class="len" style="width:{max(4, round(100 * properties / most))}%"></span></td></tr>'
            )
        return (
            '<table class="et kinds"><thead><tr><th>in the source</th><th>becomes</th><th class="len-h">properties</th>'
            f"</tr></thead><tbody>{''.join(rows)}</tbody></table>"
        )

    def kind(self, number, kind):
        rows = "".join(
            f'<tr><td data-label="property">{term(item["property"])}</td>'
            f'<td data-label="on the class">{term(item["class"])}</td>'
            f'<td data-label="from">{place_links(self.data, item["nodes"])}</td></tr>'
            for item in kind["becomes"]
        )
        return (
            f'<article class="view" id="kind-{number}" data-stop="kinds"><h2 class="ph">Kinds of record</h2>'
            f'<div class="insp"><p class="crumbs">{link("#kinds", "kinds of record")} / <b>{e(kind_name(kind))}</b></p>'
            f'<h1 tabindex="-1">{e(kind_name(kind))}</h1>'
            '<table class="et stack"><thead><tr><th>property</th><th>on the class</th><th>from</th></tr></thead>'
            f"<tbody>{rows}</tbody></table></div></article>"
        )

    def concern(self, concern):
        parts = [f"<h3>{e(concern['label'])}</h3>"]
        if concern["nodes"]:
            parts.append(
                f'<p>{e(rough(len(concern["nodes"])))} places. <button class="chip" type="button" '
                f'data-concern="{e(concern["concern"])}">Narrow the tree to these</button></p>'
            )
        if concern["gaps"]:
            parts.append('<ul class="list">' + "".join(f"<li>{a_gap(gap)}</li>" for gap in concern["gaps"]) + "</ul>")
        if concern["cases"]:
            parts.append("<p>Test cases: " + ", ".join(self.case_link(name) for name in concern["cases"]) + "</p>")
        return f'<section class="concern">{"".join(parts)}</section>'

    def not_carried(self):
        rows = "".join(
            f'<tr><td><button class="narrow" type="button" data-nodes="{e(" ".join(group["nodes"]))}">'
            f"{e(group['reason'] or 'No reason stated.')}</button>"
            + (f" {a_gap({'label': '', 'issues': group['issues']})}" if group["issues"] else "")
            + f"</td><td>{''.join(self.pill(verdict) for verdict in group['verdicts'])}</td>"
            f'<td class="fig">{e(rough(len(group["nodes"])))}</td></tr>'
            for group in self.data["notCarried"]
        )
        return (
            '<table class="et"><thead><tr><th>reason</th><th>verdict</th><th class="fig">places</th></tr></thead>'
            f"<tbody>{rows}</tbody></table>"
        )


def kind_name(kind):
    return kind["kind"] or "A kind of record the accounting does not name"


def term(item):
    code = e(item["term"]).replace(":", ":<wbr>", 1)
    shown = f"<b>{e(item['label'])}</b> <code>{code}</code>" if item["label"] else f"<code>{code}</code>"
    return f'<span class="term">{shown}</span>'


def place_links(data, nodes):
    return ", ".join(link(f"#{node}", f"<code>{e(data['places'][node])}</code>") for node in nodes)


def a_gap(gap):
    issues = "".join(f" {link(issue, e(issue_name(issue)))}" for issue in gap["issues"])
    return f"{e(gap['label'])}{' Tracked in' + issues + '.' if issues else ''}"


def issue_name(url):
    parts = urlparse(url).path.strip("/").split("/")
    return f"{parts[1]}#{parts[3]}" if len(parts) == 4 else url


def a_queries(blob, queries):
    return ", ".join(link(blob + query, f"<code>{e(query)}</code>") for query in queries)


def page(data, way_back=None, stylesheets=()):
    shown = Page(data)
    adapter = data["adapter"]
    figures = data["figures"]
    name = e(adapter["name"])
    legend = "".join(shown.pill(item["verdict"]) for item in data["verdicts"])
    chips = (
        '<div class="chips" role="group" aria-label="Narrow by concern">'
        '<button class="chip on" type="button" data-concern="" aria-pressed="true">every concern</button>'
        + "".join(
            f'<button class="chip" type="button" data-concern="{e(concern["concern"])}" aria-pressed="false">'
            f"{e(concern['label'])}</button>"
            for concern in data["concerns"]
        )
        + "</div>"
        if data["concerns"]
        else ""
    )
    opened = len(data["tree"]) == 1
    tree = "".join(shown.row(node, 0, opened) for node in data["tree"])
    concerns = "".join(shown.concern(concern) for concern in data["concerns"]) or (
        "<p>This adapter tags nothing with a concern yet. An adapter tags an accounting entry, a gap or a test case "
        "with <code>bridge:concern</code>.</p>"
    )
    cases = "".join(
        f'<tr><td class="mono">{shown.case_link(case["name"])}</td><td>{e(case["comment"] or "")}</td></tr>'
        for case in data["cases"]
    )
    views = [
        f"""<article class="view" id="overview" data-stop="overview"><h2 class="ph">Overview</h2><div class="insp">
<h1 tabindex="-1">{name}</h1>
<p class="sub"><code>{e(adapter["identifier"])}</code> {e(adapter["version"])} at {link(adapter["tree"], f"<code>{e(adapter['commit'][:7])}</code>")}</p>
<div class="over"><div>
<p class="gen">It accounts for {e(figures["paths"])} source paths, at {e(figures["places"])} places, and {e(figures["cases"])}
test cases of a conversion hold it to what it makes.</p>
<h3>Where the paths go <span>select a verdict to see its paths</span></h3>
{shown.bar(figures["shares"], "ledger-bar")}
<table class="et verdicts"><tbody>{shown.verdict_rows()}</tbody></table>
</div><div>
<h3>Kinds of record <span>select one to see what it becomes</span></h3>
{shown.kinds_table()}
</div></div></div></article>""",
        f"""<article class="view" id="paths" data-stop="paths"><h2 class="ph">Source paths</h2><div class="insp">
<h1 tabindex="-1">Source paths</h1>
<p>Open a path like a folder. A folded path shows the verdicts of the entries under it. Every path has a verdict:</p>
<table class="et verdicts"><tbody>{shown.verdict_rows(figures=False)}</tbody></table></div></article>""",
        f"""<article class="view" id="kinds" data-stop="kinds"><h2 class="ph">Kinds of record</h2><div class="insp">
<h1 tabindex="-1">Kinds of record</h1>
<p>Each kind of record in the source, and the classes it becomes.</p>
{shown.kinds_table()}</div></article>""",
        *(shown.kind(number, kind) for number, kind in enumerate(data["kinds"], 1)),
        f"""<article class="view" id="concerns" data-stop="concerns"><h2 class="ph">By concern</h2><div class="insp">
<h1 tabindex="-1">By concern</h1>{concerns}</div></article>""",
        f"""<article class="view" id="not-carried" data-stop="not-carried"><h2 class="ph">Not carried</h2><div class="insp">
<h1 tabindex="-1">Not carried</h1>
<p>What the adapter leaves out, wholly or in part, and why. Select a reason to see its paths.</p>
{shown.not_carried()}</div></article>""",
        f"""<article class="view" id="cases" data-stop="cases"><h2 class="ph">Test cases</h2><div class="insp">
<h1 tabindex="-1">Test cases</h1>
<p>{e(figures["cases"]).capitalize()} test cases of a conversion hold the adapter to what it makes. Select one to read it.</p>
<table class="et"><tbody>{cases}</tbody></table></div></article>""",
        *shown.details(data["tree"]),
    ]
    stops = "".join(
        f'<a class="stop" href="#{target}">{label}</a>'
        for target, label in (
            ("overview", "Overview"),
            ("paths", "Source paths"),
            ("kinds", "Kinds of record"),
            ("concerns", "By concern"),
            ("not-carried", "Not carried"),
            ("cases", "Test cases"),
        )
    )
    back = link(way_back[1], e(way_back[0])) if way_back else ""
    steps = [f"← {back}"] if way_back else []
    steps += [
        link(adapter["report"], "Its conformance report"),
        link(adapter["accounting"], "its accounting, in its repository"),
    ]
    index = json.dumps(data["search"], ensure_ascii=False).replace("</", "<\\/")
    linked = "".join(f'<link rel="stylesheet" href="{e(href)}">\n' for href in stylesheets)
    here = Path(__file__).with_suffix("")
    style = here.with_suffix(".css").read_text(encoding="utf-8")
    script = here.with_suffix(".js").read_text(encoding="utf-8")
    footer = f"<footer><p>← {back}</p></footer>\n" if way_back else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{name}: an adapter explorer</title>
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3E%3Crect width='16' height='16' rx='3' fill='%2314202a'/%3E%3C/svg%3E">
{linked}<style>{style}</style>
</head>
<body class="adapter-explorer">
<header class="top">
<span class="brand">Adapter explorer</span>
<span class="who">{name}</span>
<span class="addr"><code>{e(adapter["identifier"])}</code> · {e(adapter["version"])} · {link(adapter["tree"], f"<code>{e(adapter['commit'][:7])}</code>")}</span>
<span class="legend">every path has a verdict: {legend}</span>
</header>
<nav>
<div class="stops">{stops}</div>
<p class="stepline">{" · ".join(steps)}</p>
</nav>
<div id="tabs" class="tabs" role="group" aria-label="Show">
<button type="button" aria-controls="paths-pane">Paths</button>
<button type="button" aria-controls="views-pane" aria-current="true" class="on">Overview</button>
<button type="button" aria-controls="case-pane">Test case</button>
</div>
<main class="panes">
<section class="pane" id="paths-pane" aria-label="Source paths">
<h2>Source paths <span>open a path like a folder</span></h2>
<div class="filter">
<input id="search" type="search" aria-controls="tree" aria-label="Search by path or term" placeholder="Search a path or a term">
{chips}<button id="narrowed" class="chip on" type="button" hidden></button>
<p id="count" class="quiet" aria-live="polite"></p>
</div>
<div class="scroll">
<p class="root-h"><span>{name}</span><small>{e(figures["places"])} places</small></p>
<ul id="tree" class="tree">{tree}</ul>
</div>
</section>
<section class="pane on" id="views-pane" aria-label="Selected">
<div class="scroll" id="views">
{chr(10).join(views)}
</div>
</section>
<section class="pane" id="case-pane" aria-label="Test case">
<h2>Test case <span>the adapter's own</span></h2>
<div class="scroll" id="case"><p class="empty">Select a path to read the test case that holds the adapter to it.</p></div>
</section>
</main>
{footer}<script type="application/json" id="search-index">{index}</script>
<script>{script}</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
