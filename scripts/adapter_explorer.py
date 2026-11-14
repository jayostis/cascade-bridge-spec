"""Builds an adapter's explorer, one page a reader browses the adapter on:

    python3 scripts/adapter_explorer.py <adapter> --vocabulary <cascade-vocabulary> \\
        --repository <url> --report <url> --out <folder>

<adapter> is a git checkout of an adapter; <cascade-vocabulary> a checkout of the vocabulary that the crate's
bridge:vocabularyFile paths are read in, for the labels of terms; --repository is the adapter's repository on the web,
where the page links each file at the checkout's commit; --report is the adapter's conformance report. Writes
index.html, explorer.json (what the page shows, as data) and cases/<n>.json (a test case, read when a reader opens it)
into <folder>.
"""

import argparse
import html
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ElementTree
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import url2pathname

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


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("adapter", type=Path)
    parser.add_argument("--vocabulary", type=Path, required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--out", type=Path, required=True)
    arguments = parser.parse_args(argv)
    data, cases = build(arguments.adapter, arguments.vocabulary, arguments.repository.rstrip("/"), arguments.report)
    write(arguments.out, data, cases)


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
                "name": str(adapter.manifest.value(test, MF.name) or local_name(test)),
                "comment": english(adapter.manifest, test, RDFS.comment),
                "concern": adapter.manifest.value(test, BRIDGE.concern),
                "files": {role: adapter.relative(file) for role, file in files.items()},
                "texts": texts,
                "held": Held(texts["input"]),
                "classes": set(graph.objects(None, RDF.type)),
                "predicates": set(graph.predicates()),
                "bodies": set(findings.objects(None, OA.hasBody)),
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
        best = min(candidates, key=lambda case: (len(case["texts"]["input"]), case["name"]), default=None)
        return None if best is None else best["name"]

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
        for steps in sorted(level, key=lambda steps: (step_label(steps[-1]).lower(), steps[-1])):
            node = level[steps]
            node["id"] = f"n{len(ordered) + 1}"
            nodes_by_steps[steps] = node
            ordered.append(node)
            number(node["children"])

    number(tree)

    def node_of(path):
        return nodes_by_steps.get(steps_of(path_forms.place_of(forms, path)[1]))

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
                        for path, form in sorted((member["path"], member["form"] or "") for member in group)
                    ],
                    "verdict": entry["verdict"],
                    "because": entry["because"],
                    "gap": gap(entry["gap"]),
                    "lookup": None
                    if entry["lookupIn"] is None
                    else {"table": adapter.relative(path_of(entry["lookupIn"])), "gap": gap(entry["lookupGap"])},
                    "sameFactAs": None
                    if same is None
                    else {"path": str(same), "node": (node_of(str(same)) or {}).get("id")},
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
                    "case": case_for(entry, paths),
                }
            )
        return sorted(mappings, key=lambda mapping: (VERDICTS.index(mapping["verdict"]), str(mapping["forms"])))

    for node in ordered:
        node["mappings"] = mappings_of(node)

    def shaped(level):
        out = []
        for steps in sorted(level, key=lambda steps: int(nodes_by_steps[steps]["id"][1:])):
            node = level[steps]
            children = shaped(node["children"])
            verdicts = {mapping["verdict"] for mapping in node["mappings"]}
            verdicts |= {verdict for child in children for verdict in child["rollUp"]}
            out.append(
                {
                    "id": node["id"],
                    "place": shown_path(steps),
                    "step": step_label(steps[-1]),
                    "mappings": node["mappings"],
                    "rollUp": [verdict for verdict in VERDICTS if verdict in verdicts],
                    "children": children,
                }
            )
        return out

    shaped_tree = shaped(tree)
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
        "figures": {"paths": rough(len(entries)), "places": rough(len(flat)), "cases": rough(len(cases))},
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


def write(out, data, cases):
    if out.exists() and any(out.iterdir()):
        sys.exit(f"{out} is not empty; the explorer is written into an empty folder")
    (out / "cases").mkdir(parents=True, exist_ok=True)
    (out / "explorer.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    for file, case in cases.items():
        (out / file).write_text(json.dumps(case, ensure_ascii=False), encoding="utf-8")
    (out / "index.html").write_text(page(data), encoding="utf-8")


def e(text):
    return html.escape(str(text), quote=True)


def link(href, text):
    return f'<a href="{e(href)}">{text}</a>'


def badge(data, verdict):
    words = {item["verdict"]: item for item in data["verdicts"]}[verdict]
    return f'<span class="verdict v-{e(verdict)}" title="{e(words["label"] or "")}">{e(words["words"])}</span>'


def term(item):
    shown = (
        f"<b>{e(item['label'])}</b> <code>{e(item['term'])}</code>"
        if item["label"]
        else f"<code>{e(item['term'])}</code>"
    )
    return f'<span class="term">{shown}</span>'


def place_links(data, nodes):
    return ", ".join(link(f"#{node}", f"<code>{e(data['places'][node])}</code>") for node in nodes)


def a_gap(gap):
    issues = "".join(f" {link(issue, e(issue_name(issue)))}" for issue in gap["issues"])
    return f"{e(gap['label'])}{' Tracked in' + issues + '.' if issues else ''}"


def issue_name(url):
    parts = urlparse(url).path.strip("/").split("/")
    return f"{parts[1]}#{parts[3]}" if len(parts) == 4 else url


def a_mapping(data, mapping):
    blob = data["adapter"]["blob"]
    forms = "".join(
        f"<li><code>{e(form['shown'])}</code>"
        + (f' <span class="form">{e(form["form"])}</span>' if form["form"] else "")
        + "</li>"
        for form in mapping["forms"]
    )
    parts = [f'<ul class="forms">{forms}</ul>', f"<p>{badge(data, mapping['verdict'])}</p>"]
    if mapping["because"]:
        parts.append(f'<p class="why">{e(mapping["because"])}</p>')
    if mapping["gap"]:
        parts.append(f'<p class="why">{a_gap(mapping["gap"])}</p>')
    if mapping["lookup"]:
        table = mapping["lookup"]["table"]
        outside = mapping["lookup"]["gap"]
        parts.append(
            f"<p>Looked up in {link(blob + table, f'<code>{e(table)}</code>')}"
            + (f"; a value outside it: {a_gap(outside)}" if outside else ".")
            + "</p>"
        )
    if mapping["sameFactAs"]:
        same = mapping["sameFactAs"]
        shown = f"<code>{e(shown_path(steps_of(same['path'])))}</code>"
        parts.append(f"<p>The same fact as {link('#' + same['node'], shown) if same['node'] else shown}.</p>")
    for becomes in mapping["becomes"]:
        kind = f", in a {e(becomes['kind'])}" if becomes["kind"] else ""
        written = f" Written by {a_queries(blob, becomes['queries'])}." if becomes["queries"] else ""
        parts.append(f"<p>Becomes {term(becomes['property'])} on a {term(becomes['class'])}{kind}.{written}</p>")
    if mapping["queries"]:
        parts.append(f"<p>Written by {a_queries(blob, mapping['queries'])}.</p>")
    if mapping["case"]:
        (case,) = [case for case in data["cases"] if case["name"] == mapping["case"]]
        parts.append(
            f'<details class="case" data-file="{e(case["file"])}"><summary>Test case: {e(case["name"])}</summary>'
            '<div class="case-body"></div></details>'
        )
    elif mapping["becomes"] or mapping["gap"]:
        parts.append('<p class="quiet">No test case of the adapter shows this.</p>')
    return f'<div class="mapping">{"".join(parts)}</div>'


def a_queries(blob, queries):
    return ", ".join(link(blob + query, f"<code>{e(query)}</code>") for query in queries)


def a_node(data, node):
    badges = "".join(badge(data, verdict) for verdict in node["rollUp"])
    label = node["step"]
    inner = "".join(a_mapping(data, mapping) for mapping in node["mappings"])
    inner += "".join(a_node(data, child) for child in node["children"])
    return (
        f'<details class="node" id="{e(node["id"])}"><summary><code>{e(label)}</code> {badges}</summary>'
        f'<div class="below">{inner}</div></details>'
    )


def page(data):
    adapter = data["adapter"]
    figures = data["figures"]
    legend = "".join(f"<li>{badge(data, item['verdict'])} {e(item['label'] or '')}</li>" for item in data["verdicts"])
    kinds = "".join(
        f"<h3>{e(kind['kind'] or 'A kind of record the accounting does not name')}</h3><ul class='becomes'>"
        + "".join(
            f"<li>{term(item['property'])} on a {term(item['class'])}, from {place_links(data, item['nodes'])}</li>"
            for item in kind["becomes"]
        )
        + "</ul>"
        for kind in data["kinds"]
    )
    concerns = "".join(
        f"<h3>{e(concern['label'])}</h3>"
        + (f"<p>{place_links(data, concern['nodes'])}</p>" if concern["nodes"] else "")
        + "".join(f'<p class="why">{a_gap(gap)}</p>' for gap in concern["gaps"])
        + (f"<p>Test cases: {e(', '.join(concern['cases']))}</p>" if concern["cases"] else "")
        for concern in data["concerns"]
    ) or (
        "<p>This adapter tags nothing with a concern yet. An adapter tags an accounting entry, a gap or a test case "
        "with <code>bridge:concern</code>.</p>"
    )
    not_carried = "".join(
        f"<details class='reason'><summary>{e(group['reason'] or 'No reason stated.')} "
        f"{''.join(badge(data, verdict) for verdict in group['verdicts'])}</summary>"
        + (f"<p>{a_gap({'label': '', 'issues': group['issues']})}</p>" if group["issues"] else "")
        + f"<p>{place_links(data, group['nodes'])}</p></details>"
        for group in data["notCarried"]
    )
    index = json.dumps(data["search"], ensure_ascii=False).replace("</", "<\\/")
    here = Path(__file__).with_suffix("")
    style = here.with_suffix(".css").read_text(encoding="utf-8")
    script = here.with_suffix(".js").read_text(encoding="utf-8")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(adapter["name"])}: an adapter explorer</title>
<style>{style}</style>
</head>
<body>
<header>
<p class="eyebrow">Cascade Bridge adapter explorer</p>
<h1>{e(adapter["name"])}</h1>
<p>The adapter <code>{e(adapter["identifier"])}</code>, version {e(adapter["version"])}, at commit
{link(adapter["tree"], f"<code>{e(adapter['commit'][:7])}</code>")}.</p>
<p>It accounts for {e(figures["paths"])} source paths, at {e(figures["places"])} places, and {e(figures["cases"])}
test cases of a conversion hold it to what it makes.
{link(adapter["report"], "Its conformance report")} ·
{link(adapter["accounting"], "its accounting, in its repository")}</p>
</header>
<nav>
<a href="#paths">Source paths</a> <a href="#kinds">Kinds of record</a> <a href="#concerns">By concern</a>
<a href="#not-carried">Not carried</a>
<input id="search" type="search" aria-label="Search by path or term" placeholder="Search a path or a term">
</nav>
<section id="results" hidden></section>
<main>
<section id="paths">
<h2>Source paths</h2>
<p>Open a path like a folder. A folded path shows the verdicts of the entries under it.</p>
<ul class="legend">{legend}</ul>
{"".join(a_node(data, node) for node in data["tree"])}
</section>
<section id="kinds"><h2>Kinds of record</h2>{kinds}</section>
<section id="concerns"><h2>By concern</h2>{concerns}</section>
<section id="not-carried"><h2>Not carried</h2>
<p>What the adapter leaves out, wholly or in part, and why.</p>{not_carried}</section>
</main>
<script type="application/json" id="search-index">{index}</script>
<script>{script}</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
