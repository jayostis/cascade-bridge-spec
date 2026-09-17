from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import url2pathname

from rdflib import Graph, URIRef
from rdflib.namespace import RDF

from _terms import BRIDGE, MF


@dataclass(frozen=True)
class Crate:
    adapter: Path
    graph: Graph
    root: URIRef
    manifest_iri: URIRef
    manifest_file: Path

    def path_in_package(self, iri):
        prefix = self.adapter.resolve().as_uri().rstrip("/") + "/"
        if not str(iri).startswith(prefix):
            return None
        return Path(url2pathname(urlparse(str(iri)).path))

    def file_at(self, iri):
        path = self.path_in_package(iri)
        return path if path is not None and path.is_file() else None

    @property
    def entries(self):
        head = self.graph.value(self.manifest_iri, MF.entries)
        found = []
        while head is not None and head != RDF.nil:
            member = self.graph.value(head, RDF.first)
            if member is not None:
                found.append(member)
            head = self.graph.value(head, RDF.rest)
        return found

    def name_of(self, test):
        return str(self.graph.value(test, MF.name) or test)


def file_name_of(iri):
    return Path(url2pathname(urlparse(str(iri)).path)).name or str(iri)


def load(adapter):
    crate_file = adapter / "ro-crate-metadata.json"
    graph = Graph()
    graph.parse(crate_file, format="json-ld", base=crate_file.resolve().as_uri())

    roots = list(graph.subjects(RDF.type, BRIDGE.Adapter))
    if len(roots) != 1:
        raise ValueError(
            f"the crate declares {len(roots)} bridge:Adapter entities; "
            "exactly one, the root entity, is expected"
        )
    root = roots[0]

    manifests = list(graph.objects(root, BRIDGE.testManifest))
    if len(manifests) != 1:
        raise ValueError(
            f"the adapter names {len(manifests)} bridge:testManifest "
            "values; exactly one is expected"
        )
    manifest_iri = manifests[0]
    manifest_file = Path(url2pathname(urlparse(str(manifest_iri)).path))
    if not manifest_file.is_file():
        raise ValueError(
            f"the adapter's bridge:testManifest names {manifest_file}, "
            "which does not exist"
        )
    try:
        graph.parse(manifest_file, format="turtle", publicID=str(manifest_iri))
    except Exception as error:
        raise ValueError(f"{manifest_file.name} does not parse as Turtle: {error}") from error

    return Crate(adapter, graph, root, manifest_iri, manifest_file)


_parsed_crates: dict[Path, Crate] = {}


def from_context(context):
    uri = context.settings.rocrate_uri
    for candidate in (getattr(uri, "path", None), str(uri)):
        if not candidate:
            continue
        text = str(candidate)
        if text.startswith("file://"):
            text = url2pathname(urlparse(text).path)
        path = Path(text)
        if path.is_dir():
            path = path.resolve()
            if path not in _parsed_crates:
                _parsed_crates[path] = load(path)
            return _parsed_crates[path]
    raise FileNotFoundError(f"cannot read {uri} as a directory")
